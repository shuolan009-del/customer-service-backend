/**
 * 本地消息时间轴 —— 「按天管理对话」的时间来源。
 *
 * 为什么需要它（后端零改动前提下的硬约束）：
 *   GET /api/chat/history 返回的 HistoryMessage 只有 session_id / role / text / object，
 *   没有任何时间字段；后端的时间戳只存在于 Session 级（domain/state.py 的
 *   started_at / last_activity_at / closed_at），且 session_id 是 str(uuid4())，
 *   无法反推日期。所以「这条消息是哪天说的」只能由前端自己记。
 *
 * 策略：
 *   - 本浏览器发出 / 收到的消息 → 打上 Date.now()，可精确分到「今天 / 昨天 / 具体日期」
 *   - 历史接口返回、本机没记录过的旧消息 → 无时间 → 归入「更早的记录」
 *
 * 指纹：HistoryMessage 没有 message_id，无法与本地记录一一对应，故用
 *   「角色 + 类型 + 对象 id + 文本 + 同内容第几次出现」生成稳定键。
 *   后端按 session/turn 顺序稳定展开历史，所以刷新后同一条消息能重新命中。
 *   已知取舍：同一发送者跨天说过「完全相同的第 N 次同样的话」时会命中后一条的时间，
 *   而分组只用到「天」，影响仅限于该条被归到较新的那天。
 */

const PREFIX = 'cs-ts:v1:'
const RETAIN_DAYS = 30
const MAX_ENTRIES = 1000

// 按 sender_id 缓存已解析的时间表，避免分组时对每条消息重复 JSON.parse
let cache = { senderId: null, map: {} }

function normalize(senderId) {
  return String(senderId ?? '').trim()
}

function storageKey(senderId) {
  const sid = normalize(senderId)
  return `${PREFIX}${sid || 'default'}`
}

function readFromStorage(senderId) {
  try {
    const raw = localStorage.getItem(storageKey(senderId))
    if (!raw) return {}
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch (error) {
    // 隐私模式 / 配额满 / 数据损坏 —— 一律降级为「无时间轴」
    return {}
  }
}

function mapFor(senderId) {
  const sid = normalize(senderId)
  if (cache.senderId !== sid) {
    cache = { senderId: sid, map: readFromStorage(sid) }
  }
  return cache.map
}

function persist(senderId) {
  const map = mapFor(senderId)
  const cutoff = Date.now() - RETAIN_DAYS * 24 * 60 * 60 * 1000

  const entries = Object.entries(map).filter(([, at]) => Number.isFinite(at) && at >= cutoff)
  if (entries.length > MAX_ENTRIES) {
    entries.sort((a, b) => b[1] - a[1])
    entries.length = MAX_ENTRIES
  }

  const next = Object.fromEntries(entries)
  cache.map = next
  try {
    localStorage.setItem(storageKey(senderId), JSON.stringify(next))
  } catch (error) {
    /* 写不进去就当只读，内存里仍然可用 */
  }
  return next
}

/** 不含「第几次出现」的基础指纹 */
function baseFingerprint(message) {
  const payload = message?.payload ?? {}
  const objectId = payload.id ?? payload.order_id ?? payload.product_id ?? ''
  const text = typeof message?.text === 'string' ? message.text : ''
  return `${message?.role ?? ''}|${message?.type ?? ''}|${message?.objectType ?? ''}|${objectId}|${text}`
}

/**
 * 第 index 条消息的完整指纹（含同内容出现序号）。
 * 序号是「按当前消息列表顺序数下来」确定的，刷新后顺序一致 → 结果一致。
 */
export function fingerprintAt(messages, index) {
  const target = messages[index]
  if (!target) return ''
  const base = baseFingerprint(target)
  let occurrence = 0
  for (let i = 0; i < index; i += 1) {
    if (baseFingerprint(messages[i]) === base) occurrence += 1
  }
  return `${base}|${occurrence}`
}

/** 读取某条消息记录过的时间戳（毫秒），没有则返回 null */
export function getTime(senderId, fingerprint) {
  if (!fingerprint) return null
  const at = mapFor(senderId)[fingerprint]
  return Number.isFinite(at) ? at : null
}

/** 记录一条消息的时间戳 */
export function stamp(senderId, fingerprint, at) {
  if (!fingerprint) return null
  const ts = Number.isFinite(at) ? at : Date.now()
  mapFor(senderId)[fingerprint] = ts
  persist(senderId)
  return ts
}
