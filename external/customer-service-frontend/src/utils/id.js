/**
 * 生成一个 UUID；优先使用 crypto.randomUUID，老浏览器回落。
 * 用于消息 id、WS message_id 等。
 */
export function safeUuid() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    try {
      return crypto.randomUUID()
    } catch (error) {
      /* 某些非安全上下文下会抛错，走回落 */
    }
  }
  return `id-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}
