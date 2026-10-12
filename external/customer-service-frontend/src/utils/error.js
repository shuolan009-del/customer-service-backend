/**
 * 把底层异常翻译成用户可读的中文提示。
 *
 * 背景：后端未启动、网络中断或响应非 JSON 时，fetch/Response.json() 抛出的都是
 * 英文 TypeError（如 "Failed to execute 'json' on 'Response': Unexpected end of JSON input"），
 * 直接把 error.message 渲染到界面上对用户毫无意义。这里统一兜底。
 *
 * 规则：后端主动返回的中文 detail 原样沿用；其余按类型给出可操作提示。
 */

const FALLBACK = '操作失败，请稍后重试。'

export function toFriendlyMessage(error, fallback = FALLBACK) {
  if (!error) return fallback

  const raw = error instanceof Error ? error.message : String(error)
  const text = (raw || '').trim()
  if (!text) return fallback

  const lower = text.toLowerCase()

  // 连接层错误：后端没起、端口不通、被代理拦截
  if (
    lower.includes('failed to fetch') ||
    lower.includes('networkerror') ||
    lower.includes('load failed') ||
    lower.includes('network request failed')
  ) {
    return '无法连接后台服务，请确认后端已启动（对话服务 18082 / 电商服务 18081）。'
  }

  // 拿到了响应但不是合法 JSON：多为服务未就绪或中途断开
  if (lower.includes('json')) {
    return '后台返回内容异常（服务可能未启动或已中断），请稍后重试。'
  }

  if (lower.includes('timeout') || text.includes('超时')) {
    return '请求超时，请检查网络后重试。'
  }

  // 后端返回的中文 detail：原样展示（例如「加载订单列表失败。」）
  if (/[\u4e00-\u9fa5]/.test(text)) return text

  return fallback
}
