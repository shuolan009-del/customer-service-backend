import { reactive } from 'vue'

/**
 * 全局 Toast（顶部居中堆叠，自动消失）。
 * 模块级单例：任意组件 import 后调用 push/success/error，由 <ToastHost> 统一渲染。
 */

let seq = 0
const state = reactive({ items: [] })

export function useToast() {
  function dismiss(id) {
    const index = state.items.findIndex((item) => item.id === id)
    if (index >= 0) state.items.splice(index, 1)
  }

  function push(message, variant = 'info', timeout = 3000) {
    const text = String(message ?? '').trim()
    if (!text) return null
    const id = ++seq
    state.items.push({ id, message: text, variant })
    if (timeout > 0) {
      setTimeout(() => dismiss(id), timeout)
    }
    return id
  }

  return {
    items: state.items,
    push,
    dismiss,
    success: (message, timeout) => push(message, 'success', timeout),
    error: (message, timeout) => push(message, 'error', timeout),
    warning: (message, timeout) => push(message, 'warning', timeout),
    info: (message, timeout) => push(message, 'info', timeout),
  }
}
