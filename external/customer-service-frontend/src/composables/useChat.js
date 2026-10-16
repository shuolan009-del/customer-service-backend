import { computed, nextTick, ref, watch } from 'vue'
import { useAvatar } from './useAvatar'
import { safeUuid } from '../utils/id'
import { toFriendlyMessage } from '../utils/error'
import * as timeline from '../utils/timeline'
import { EARLIER_KEY, dayKeyOf, formatClock, formatDayLabel } from '../utils/format'
import { DEFAULT_SENDER_ID } from '../config/service'
import { withPrefix } from '../config/api-base'

/**
 * 对话核心：消息列表（按自然日分组）、发送、历史加载、滚动与未读。
 *
 * 分组维度是「日期时间轴」而不是「Turn 轮次」：
 *   - 用户要求「对话不要分成一块一块的，要连成一个整体」→ 不再按 Turn 塞进卡片
 *   - 用户要求「按每天的时间进行对话管理」→ 用自然日为分隔
 * 时间来源见 utils/timeline.js（后端接口不返回任何时间字段）。
 *
 * 模块级单例，供 WorkbenchView / SessionsView 共用同一份会话状态。
 */

const senderId = ref(DEFAULT_SENDER_ID)
const draftMessage = ref('')
const isSending = ref(false)
const errorMessage = ref('')
const historyLoading = ref(false)
const messages = ref([])

// 滚动相关
const scrolledToBottom = ref(true)
const unreadCount = ref(0)
let containerEl = null
let lastPayload = null

const avatar = useAvatar()

// 数字人（WS）回调注入：bot 文本落库、取 sender_id、错误兜底
avatar.setHooks({
  onBotMessage: (message) => appendMessage('bot', message),
  getSenderId: () => senderId.value.trim(),
  onError: (message) => {
    errorMessage.value = message
    isSending.value = false
  },
})

const historyEndpoint = computed(
  () => withPrefix(`/api/chat/history?sender_id=${encodeURIComponent(senderId.value.trim())}`),
)

// ── 消息构造 ────────────────────────────────────────────────────────
function createBaseMessage(role) {
  return { id: safeUuid(), role, at: null }
}

/** 记录最后一条消息的时间（本浏览器产生的消息才有准确时间） */
function stampLastMessage() {
  const index = messages.value.length - 1
  const message = messages.value[index]
  if (!message) return
  const at = Date.now()
  message.at = at
  timeline.stamp(senderId.value, timeline.fingerprintAt(messages.value, index), at)
}

function appendUserText(text) {
  messages.value.push({ ...createBaseMessage('user'), type: 'text', text })
  stampLastMessage()
}

function appendUserObject(objectType, payload) {
  messages.value.push({ ...createBaseMessage('user'), type: 'object', objectType, payload })
  stampLastMessage()
}

/**
 * 追加一条消息。
 * @param {boolean} stampNow 是否打上「现在」的时间戳。
 *        bot 由 WS 回调注入时也走这里（是本轮真实产生的消息，需要打戳）；
 *        历史消息回填时必须传 false，否则会把旧消息记成「今天」。
 */
function appendMessage(role, message, stampNow = true) {
  if (message.object) {
    messages.value.push({
      ...createBaseMessage(role),
      type: 'object',
      objectType: message.object.type,
      payload: message.object,
    })
  } else {
    messages.value.push({
      ...createBaseMessage(role),
      type: 'text',
      text: message.text ?? '',
      suggestions: message.suggestions ?? null,
    })
  }
  if (stampNow) stampLastMessage()
}

function appendBotMessages(botMessages) {
  for (const message of botMessages) {
    appendMessage('bot', message)
  }
}

function setHistoryMessages(historyMessages) {
  messages.value = []
  for (const message of historyMessages) {
    const role = message.role === 'user' ? 'user' : 'bot'
    appendMessage(role, message, false)
  }

  // 回填历史消息的时间：命中了本地时间轴就用真实时间，否则留空 → 归入「更早的记录」
  messages.value.forEach((message, index) => {
    const at = timeline.getTime(
      senderId.value,
      timeline.fingerprintAt(messages.value, index),
    )
    if (at) message.at = at
  })
}

// ── 演示兜底（2026-10-16）───────────────────────────────────────────
/**
 * 虚拟对话：真实历史为空或历史接口失败时展示，保证任意 sender_id 下
 * 聊天区都有内容可看（与右侧「演示数据」同策略）。字段形状与历史接口一致。
 * 时间戳只在内存中设置（今天、按分钟回退），不写入本地时间轴，刷新后重新生成。
 */
const MOCK_CHAT = [
  { role: 'bot', text: '您好，我是小禾，您的专属电商客服。查订单、问商品、退换货，都可以直接找我。' },
  { role: 'user', text: '我昨天下的单什么时候能发货？' },
  { role: 'bot', text: '帮您查到订单 A20260410001 已进入打包流程，预计今天 18:00 前发出，发出后会第一时间短信通知您。', suggestions: ['帮我催发货', '修改收货地址'] },
  { role: 'user', object: { type: 'order', order_id: 'A20260410001', title: 'iPhone 15 Pro 256G 远峰蓝', amount: 8999, status: '待发货' } },
  { role: 'bot', text: '收到，已为您备注优先发货，请放心。还有其他需要帮忙的吗？' },
]

function seedMockConversation() {
  const now = Date.now()
  messages.value = MOCK_CHAT.map((m, index) => {
    const base = { id: safeUuid(), at: now - (MOCK_CHAT.length - index) * 60000 }
    if (m.object) {
      return { ...base, role: m.role, type: 'object', objectType: m.object.type, payload: m.object }
    }
    return { ...base, role: m.role, type: 'text', text: m.text, suggestions: m.suggestions ?? null }
  })
}

// ── 日期分组 ────────────────────────────────────────────────────────
/**
 * 输出结构：
 * [
 *   { type: 'day', key: '2026-10-11', label: '今天', items: [
 *       { message, position: 'single'|'head'|'middle'|'tail', timeLabel: '14:32' }
 *   ]}
 * ]
 * position 用来做「同一发送者连续消息」的视觉成组：只有 head/single 显示头像与时间。
 */
const messageGroups = computed(() => {
  const list = messages.value
  const groups = []
  let current = null
  let lastKey = null

  list.forEach((message, index) => {
    const key = message.at ? dayKeyOf(message.at) : EARLIER_KEY
    if (key !== lastKey) {
      current = { type: 'day', key, label: formatDayLabel(message.at), items: [] }
      groups.push(current)
      lastKey = key
    }

    const prev = list[index - 1]
    const next = list[index + 1]
    const samePrev = Boolean(prev) && prev.role === message.role && current.items.length > 0
    const sameNext = Boolean(next) && next.role === message.role && (next.at ? dayKeyOf(next.at) : EARLIER_KEY) === key
    const position = samePrev
      ? (sameNext ? 'middle' : 'tail')
      : (sameNext ? 'head' : 'single')

    current.items.push({
      message,
      position,
      timeLabel: position === 'head' || position === 'single' ? formatClock(message.at) : '',
    })
  })

  return groups
})

const isEmpty = computed(() => messages.value.length === 0)
const canRetry = computed(() => Boolean(errorMessage.value && lastPayload))

// ── 滚动 ────────────────────────────────────────────────────────────
function setContainer(el) {
  containerEl = el
}

async function scrollToBottom(smooth = false) {
  await nextTick()
  if (!containerEl) return
  if (smooth && typeof containerEl.scrollTo === 'function') {
    containerEl.scrollTo({ top: containerEl.scrollHeight, behavior: 'smooth' })
  } else {
    containerEl.scrollTop = containerEl.scrollHeight
  }
  scrolledToBottom.value = true
  unreadCount.value = 0
}

function onScroll() {
  if (!containerEl) return
  const distance = containerEl.scrollHeight - containerEl.scrollTop - containerEl.clientHeight
  scrolledToBottom.value = distance < 40
  if (scrolledToBottom.value) unreadCount.value = 0
}

watch(
  () => messages.value.length,
  async (next, prev) => {
    const last = messages.value[messages.value.length - 1]
    if (!scrolledToBottom.value && last && last.role === 'bot' && next > prev) {
      unreadCount.value += 1
    }
    if (scrolledToBottom.value) {
      await scrollToBottom()
    }
  },
)

// ── 请求 ────────────────────────────────────────────────────────────
/** 历史请求序号：快速切换 sender_id 时丢弃过期响应，避免骨架屏被旧请求提前解除 */
let historySeq = 0

async function fetchHistory() {
  const sid = senderId.value.trim()
  if (!sid) {
    messages.value = []
    return
  }
  const seq = ++historySeq
  historyLoading.value = true
  errorMessage.value = ''
  try {
    const response = await fetch(historyEndpoint.value)
    const data = await response.json()
    if (!response.ok) {
      throw new Error(data.detail || '加载历史消息失败。')
    }
    if (seq === historySeq && sid === senderId.value.trim()) {
      setHistoryMessages(Array.isArray(data?.messages) ? data.messages : [])
      /* 演示兜底：真实历史为空 → 展示虚拟对话 */
      if (messages.value.length === 0) seedMockConversation()
    }
  } catch (error) {
    if (seq === historySeq) {
      /* 演示兜底：历史接口失败 → 虚拟对话（不向用户抛错误横幅） */
      console.warn('[chat] 历史接口失败，回退演示对话：', error)
      seedMockConversation()
    }
  } finally {
    if (seq === historySeq) {
      historyLoading.value = false
      await scrollToBottom()
    }
  }
}

function reset() {
  messages.value = []
  errorMessage.value = ''
  lastPayload = null
  unreadCount.value = 0
  scrolledToBottom.value = true
  avatar.resetSpeech()
  /* 新对话后同样回到虚拟对话演示态，页面不留空白 */
  seedMockConversation()
}

async function sendPayload(payload) {
  if (isSending.value) return

  errorMessage.value = ''
  isSending.value = true
  lastPayload = payload

  // 数字人已就绪 + 纯文本输入 → 走 WebSocket（支持插话打断播报）
  // 未连接数字人时行为与改动前完全一致，仍走 HTTP
  if (avatar.canUseWs() && typeof payload.text === 'string' && payload.text.trim()) {
    let sent = false
    try {
      sent = await avatar.sendViaWs(payload.text)
    } catch (error) {
      sent = false
    }
    if (sent) {
      isSending.value = false
      return
    }
    // WS 实际未发出（canUseWs 检查与 send 之间连接已断开）→ 回退 HTTP 重发。
    // 用户气泡已在列表中，HTTP 分支只会追加 bot 回复，不会重复追加用户消息；
    // isSending 保持 true，按钮与「正在输入」在重发期间持续禁用。
  }

  try {
    const response = await fetch(withPrefix('/api/chat'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sender_id: senderId.value.trim(), ...payload }),
    })

    const data = await response.json()
    if (!response.ok) {
      throw new Error(data.detail || '请求失败。')
    }

    appendBotMessages(data.messages ?? [])

    // 数字人已连接时，走 HTTP 的回复（如对象类消息）也交给数字人朗读
    if (avatar.humanReady.value) {
      const speech = (data.messages ?? [])
        .map((message) => message.text)
        .filter(Boolean)
        .join(' ')
        .trim()
      if (speech) avatar.speakWithAvatar(speech)
    }
  } catch (error) {
    errorMessage.value = toFriendlyMessage(error, '发送失败，请稍后重试。')
  } finally {
    isSending.value = false
  }
}

/** 内联错误「重试」：重发上一条 payload */
async function retryLast() {
  if (!lastPayload) return
  await sendPayload(lastPayload)
}

async function sendSuggestion(text) {
  appendUserText(text)
  await sendPayload({ text })
}

async function sendQuickText(text) {
  draftMessage.value = text
  await sendTextMessage()
}

async function sendTextMessage() {
  const text = draftMessage.value.trim()
  const sid = senderId.value.trim()

  if (!sid) {
    errorMessage.value = '请先输入 sender_id。'
    return
  }
  if (!text) return

  draftMessage.value = ''
  appendUserText(text)
  await sendPayload({ text })
}

async function sendOrder(order) {
  const sid = senderId.value.trim()
  if (!sid) {
    errorMessage.value = '请先输入 sender_id。'
    return
  }
  appendUserObject('order', { ...order })
  await sendPayload({
    object: {
      type: 'order',
      id: order.order_id,
      title: order.title,
      attributes: {
        status: order.status,
        amount: order.amount,
        created_at: order.created_at,
        cover_url: order.cover_url,
      },
    },
  })
}

async function sendProduct(product) {
  const sid = senderId.value.trim()
  if (!sid) {
    errorMessage.value = '请先输入 sender_id。'
    return
  }
  appendUserObject('product', { ...product })
  await sendPayload({
    object: {
      type: 'product',
      id: product.product_id,
      title: product.title,
      attributes: {
        price: product.price,
        cover_url: product.cover_url,
        description: product.description,
      },
    },
  })
}

export function useChat() {
  return {
    // state
    senderId,
    draftMessage,
    isSending,
    errorMessage,
    historyLoading,
    scrolledToBottom,
    unreadCount,
    // derived
    messageGroups,
    isEmpty,
    canRetry,
    // actions
    setContainer,
    scrollToBottom,
    onScroll,
    fetchHistory,
    reset,
    retryLast,
    sendSuggestion,
    sendQuickText,
    sendTextMessage,
    sendOrder,
    sendProduct,
  }
}
