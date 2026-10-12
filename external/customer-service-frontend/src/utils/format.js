/**
 * 展示格式化工具：金额、对象卡片字段、时间。
 * 一律对 message（{ objectType, payload }）或原始对象做空值兜底，避免模板报错。
 */

export function formatAmount(amount) {
  const numericAmount = Number(amount)
  if (Number.isNaN(numericAmount)) {
    return '￥0.00'
  }
  return `￥${numericAmount.toFixed(2)}`
}

export function formatOrderSummary(order) {
  const payload = order?.payload ?? order ?? {}
  const status = payload.status ?? payload.attributes?.status
  return status ? `订单状态：${status}` : '订单'
}

export function formatProductSummary(product) {
  const payload = product?.payload ?? product ?? {}
  if (payload.description) {
    return payload.description
  }
  if (payload.attributes?.price) {
    return `商品价格：${formatAmount(payload.attributes.price)}`
  }
  return '商品信息'
}

export function getObjectTitle(message) {
  const payload = message?.payload ?? {}
  if (payload.title) {
    return payload.title
  }
  return message?.objectType === 'order' ? '订单对象' : '商品对象'
}

export function getObjectIdentifier(message) {
  const payload = message?.payload ?? {}
  const id = payload.order_id ?? payload.product_id ?? payload.id
  const label = message?.objectType === 'order' ? '订单号' : '商品号'
  return id ? `${label}：${id}` : label
}

export function getObjectSummary(message) {
  const payload = message?.payload ?? {}
  if (message?.objectType === 'order') {
    const status = payload.status ?? payload.attributes?.status
    return status ? `订单状态：${status}` : '订单'
  }
  return formatProductSummary(payload)
}

export function getObjectAmount(message) {
  const payload = message?.payload ?? {}
  const amount = message?.objectType === 'order'
    ? payload.amount ?? payload.attributes?.amount
    : payload.price ?? payload.attributes?.price
  return formatAmount(amount)
}

export function formatDateTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

// ── 日期时间轴（配合 utils/timeline.js 使用）──────────────────────────────

/** 无时间戳的消息统一归到这一组（历史接口不返回时间，见 timeline.js 注释） */
export const EARLIER_KEY = 'earlier'
export const EARLIER_LABEL = '更早的记录'

const WEEKDAYS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

function pad2(value) {
  return String(value).padStart(2, '0')
}

/** 本地自然日键：yyyy-MM-dd；无时间戳返回 EARLIER_KEY */
export function dayKeyOf(timestamp) {
  if (!Number.isFinite(timestamp)) return EARLIER_KEY
  const date = new Date(timestamp)
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`
}

/** 日期分隔标签：今天 / 昨天 / 10月9日 周四 / 2025年10月9日 / 更早的记录 */
export function formatDayLabel(timestamp) {
  if (!Number.isFinite(timestamp)) return EARLIER_LABEL
  const date = new Date(timestamp)
  const now = new Date()
  const key = dayKeyOf(timestamp)
  if (key === dayKeyOf(now.getTime())) return '今天'
  if (key === dayKeyOf(now.getTime() - 24 * 60 * 60 * 1000)) return '昨天'

  const monthDay = `${date.getMonth() + 1}月${date.getDate()}日`
  if (date.getFullYear() === now.getFullYear()) {
    return `${monthDay} ${WEEKDAYS[date.getDay()]}`
  }
  return `${date.getFullYear()}年${monthDay}`
}

/** 消息组首条的时分标签：14:32；无时间戳返回空串 */
export function formatClock(timestamp) {
  if (!Number.isFinite(timestamp)) return ''
  const date = new Date(timestamp)
  return `${pad2(date.getHours())}:${pad2(date.getMinutes())}`
}
