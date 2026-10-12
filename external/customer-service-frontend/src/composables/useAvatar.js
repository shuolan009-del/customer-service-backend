import { computed, reactive, ref } from 'vue'
import { useAvatarWs } from './useAvatarWs'
import { useToast } from './useToast'
import { safeUuid } from '../utils/id'

/**
 * 数字人（魔珐星云）能力单例。
 * - 连接 / 销毁 SDK、资源加载进度、WS 聊天通道、TTS 播报（改为驱动数字人朗读）
 * - 通过 setHooks() 注入「收到 bot 文本」「取 sender_id」「错误提示」等外部行为，避免与 useChat 循环依赖
 */

const XMOV_SDK_URL = 'https://media.xingyun3d.com/xingyun3d/general/litesdk/xmovAvatar@latest.js'

// ── 状态 ────────────────────────────────────────────────────────────
const humanReady = ref(false)
const humanConnecting = ref(false)
const humanProgress = ref(0)
const humanError = ref('')
const ttsState = reactive({})

// ── 内部 ────────────────────────────────────────────────────────────
let humanSdk = null
let humanSpeechBuffer = []
let humanTurnFinish = null
let humanInitReject = null
let hooks = { onBotMessage: null, getSenderId: () => '', onError: null, onTurnStart: null }

const avatarWs = useAvatarWs()
const toast = useToast()

// ── SDK 加载 ────────────────────────────────────────────────────────
function supportsWebgl2() {
  try {
    const canvas = document.createElement('canvas')
    return Boolean(canvas.getContext('webgl2'))
  } catch (error) {
    return false
  }
}

function loadXmovSdk() {
  return new Promise((resolve, reject) => {
    if (window.XmovAvatar) { resolve(); return }
    const existing = document.querySelector('script[data-xmov-sdk]')
    if (existing) {
      existing.addEventListener('load', () => resolve())
      existing.addEventListener('error', () => reject(new Error('数字人 SDK 加载失败。')))
      return
    }
    const script = document.createElement('script')
    script.src = XMOV_SDK_URL
    script.async = true
    script.dataset.xmovSdk = '1'
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('数字人 SDK 脚本加载失败，请检查网络。'))
    document.head.appendChild(script)
  })
}

// ── 播报 ────────────────────────────────────────────────────────────
function speakWithAvatar(text) {
  const content = (text || '').trim()
  if (!content || !humanSdk || !humanReady.value) return
  try {
    // 官方建议：两次 speak 之间先切一次 interactiveidle，否则口型对不上
    humanSdk.interactiveidle?.()
    setTimeout(() => {
      try { humanSdk?.speak(content, true, true) } catch (error) { console.error('[数字人] speak 失败:', error) }
    }, 260)
  } catch (error) {
    console.error('[数字人] speak 失败:', error)
  }
}

function stopSpeech() {
  try { humanSdk?.interactiveidle?.() } catch (error) { /* 忽略 */ }
  for (const key of Object.keys(ttsState)) {
    if (ttsState[key] === 'playing') ttsState[key] = 'idle'
  }
}

function resetSpeech() {
  for (const key of Object.keys(ttsState)) {
    ttsState[key] = 'idle'
  }
}

async function playTts(botMsg) {
  const msgId = botMsg?.id
  const text = (botMsg?.text || '').trim()
  if (!msgId || !text) return

  // 正在播报时再点一次 = 停止
  if (ttsState[msgId] === 'playing') {
    stopSpeech()
    return
  }
  if (!humanReady.value) {
    toast.info('数字人尚未连接，请先点击左侧「连接数字人」。')
    return
  }
  for (const key of Object.keys(ttsState)) {
    if (ttsState[key] === 'playing') ttsState[key] = 'idle'
  }
  ttsState[msgId] = 'playing'
  speakWithAvatar(text)
}

// ── WS ──────────────────────────────────────────────────────────────
function handleWsMessage(event) {
  let msg = null
  try { msg = JSON.parse(event.data) } catch (error) { return }
  if (!msg) return

  switch (msg.type) {
    case 'bot_text':
      hooks.onBotMessage?.({ text: msg.text, object: msg.object })
      if (msg.text) humanSpeechBuffer.push(msg.text)
      break
    case 'turn_end':
      if (typeof humanTurnFinish === 'function') humanTurnFinish()
      break
    case 'interrupt':
      stopSpeech()
      humanSpeechBuffer = []
      break
    case 'error':
      hooks.onError?.(msg.message || '数字人通道返回错误。')
      if (typeof humanTurnFinish === 'function') humanTurnFinish()
      break
    default:
      break
  }
}

avatarWs.configure({
  onMessage: handleWsMessage,
  onStatus: (status) => {
    if (status === 'closed') console.info('[数字人] 聊天通道已关闭')
  },
})

/** 数字人已就绪 + WS 打开时才走 WS 链路 */
function canUseWs() {
  return humanReady.value && avatarWs.isOpen()
}

function sendViaWs(text) {
  return new Promise((resolve) => {
    if (!canUseWs()) { resolve(false); return }

    humanSpeechBuffer = []
    let timer = null

    const finish = (sent = true) => {
      if (humanTurnFinish !== finish) return
      humanTurnFinish = null
      if (timer) clearTimeout(timer)
      // 本轮结束统一播报一次，避免连续 speak 撞上官方限制
      const speech = humanSpeechBuffer.join(' ').trim()
      humanSpeechBuffer = []
      if (speech) speakWithAvatar(speech)
      // sent=false 表示消息根本没发出去（socket 已断开），调用方需回退 HTTP；
      // 超时与 error 回调仍然 resolve(true)——消息已送达服务端，回退会造成重复回复
      resolve(sent)
    }

    timer = setTimeout(() => {
      hooks.onError?.('数字人通道响应超时。')
      finish()
    }, 60000)

    humanTurnFinish = finish
    const sent = avatarWs.send({
      type: 'user_text',
      sender_id: hooks.getSenderId?.() || '',
      text,
      message_id: safeUuid(),
    })
    if (!sent) finish(sent)
  })
}

// ── 生命周期 ────────────────────────────────────────────────────────
async function init() {
  // 防重入：连接进行中（humanConnecting=true 但 humanSdk 仍为 null）时重复调用，
  // 会创建两个 SDK 实例争抢同一个 #digital-human-sdk 容器
  if (humanConnecting.value) return

  humanError.value = ''
  humanConnecting.value = true
  humanProgress.value = 0

  try {
    if (!supportsWebgl2()) {
      throw new Error('当前浏览器不支持 WebGL 2.0，无法渲染 3D 数字人。请使用较新版本的 Chrome / Edge 打开。')
    }

    // 1. 凭证从后端取（App Secret 只存在后端 .env，前端不硬编码）
    const response = await fetch('/api/avatar/session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    })
    const credentials = await response.json()
    if (!response.ok) {
      throw new Error(credentials.detail || '获取数字人凭证失败。')
    }
    if (!credentials.app_secret) {
      throw new Error(credentials.notice || '后端未下发 App Secret：请在 .env 设置 XMOV_ALLOW_SECRET_TO_CLIENT=true 后重启服务（仅限本地演示）。')
    }

    // 2. 加载官方 SDK
    await loadXmovSdk()

    // 3. 创建实例
    humanSdk = new window.XmovAvatar({
      containerId: '#digital-human-sdk',
      appId: credentials.app_id,
      appSecret: credentials.app_secret,
      gatewayServer: credentials.gateway_server,
      hardwareAcceleration: 'default',
      enableLogger: false,
      onMessage(message) {
        const networkStatusCodes = [50001, 50002, 50003, 50004]
        if (message && message.code && !networkStatusCodes.includes(message.code)) {
          humanError.value = `数字人 SDK 错误 ${message.code}：${message.message || ''}`
          if (typeof humanInitReject === 'function') {
            humanInitReject(new Error(humanError.value))
          }
        }
      },
      onVoiceStateChange(status) {
        if (status === 'end' || status === 'voice_end') {
          for (const key of Object.keys(ttsState)) {
            if (ttsState[key] === 'playing') ttsState[key] = 'idle'
          }
        }
      },
      onStartSessionWarning(warning) {
        console.warn('[数字人] 会话配置警告:', warning)
      },
    })

    // 4. 连接房间 + 下载资源，进度到 100% 才真正可说话
    await new Promise((resolve, reject) => {
      humanInitReject = reject
      const timer = setTimeout(
        () => reject(new Error('数字人资源下载超时（90 秒内未完成），请检查网络后重试。')),
        90000,
      )
      try {
        humanSdk.init({
          initModel: 'normal',
          onDownloadProgress(progress) {
            humanProgress.value = progress
            if (progress >= 100) {
              clearTimeout(timer)
              resolve()
            }
          },
        })
      } catch (error) {
        clearTimeout(timer)
        reject(error)
      }
    })

    humanReady.value = true
    humanProgress.value = 100
    avatarWs.connect()
  } catch (error) {
    humanError.value = error instanceof Error ? error.message : String(error)
    destroy()
  } finally {
    humanInitReject = null
    humanConnecting.value = false
  }
}

function destroy() {
  avatarWs.close()
  try { humanSdk?.destroy?.() } catch (error) { /* 实例可能已不存在 */ }
  humanSdk = null
  humanReady.value = false
  humanProgress.value = 0
  humanTurnFinish = null
  humanInitReject = null
  humanSpeechBuffer = []
  resetSpeech()
}

function toggle() {
  if (humanSdk || humanReady.value) {
    destroy()
  } else {
    init()
  }
}

/** 页面卸载 / 关闭前释放房间连接，避免并发限制（错误码 10005） */
function dispose() {
  try { humanSdk?.destroy?.() } catch (error) { /* 忽略 */ }
  destroy()
}

const buttonText = computed(() => {
  if (humanConnecting.value) return `加载中 ${humanProgress.value}%`
  if (humanReady.value) return '销毁数字人'
  return '连接数字人'
})

const statusText = computed(() => {
  if (humanReady.value) return '已连接'
  if (humanConnecting.value) return '连接中'
  return '未连接'
})

const statusClass = computed(() => {
  if (humanReady.value) return 'is-ready'
  if (humanConnecting.value) return 'is-loading'
  return 'is-idle'
})

const wsStatusText = computed(() => {
  const map = { open: '通道已连接', connecting: '通道连接中', reconnecting: '通道重连中', closed: '通道已断开', idle: '通道未连接' }
  return map[avatarWs.wsState.status] || '通道未连接'
})

export function useAvatar() {
  function setHooks(next) {
    hooks = { ...hooks, ...next }
  }

  return {
    // state
    humanReady,
    humanConnecting,
    humanProgress,
    humanError,
    ttsState,
    wsState: avatarWs.wsState,
    // computed
    buttonText,
    statusText,
    statusClass,
    wsStatusText,
    // actions
    setHooks,
    init,
    destroy,
    dispose,
    toggle,
    playTts,
    stopSpeech,
    resetSpeech,
    speakWithAvatar,
    canUseWs,
    sendViaWs,
  }
}
