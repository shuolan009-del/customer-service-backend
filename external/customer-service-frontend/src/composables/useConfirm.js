import { reactive } from 'vue'

/**
 * 全局确认弹窗（Promise 化）。
 * const ok = await confirm({ title, description, danger: true })
 * 由 <ConfirmDialog> 统一渲染并回填。
 */

const state = reactive({
  open: false,
  title: '',
  description: '',
  confirmText: '确认',
  cancelText: '取消',
  danger: false,
  _resolve: null,
})

export function useConfirm() {
  function confirm(options = {}) {
    return new Promise((resolve) => {
      state.title = options.title ?? '请确认'
      state.description = options.description ?? ''
      state.confirmText = options.confirmText ?? '确认'
      state.cancelText = options.cancelText ?? '取消'
      state.danger = Boolean(options.danger)
      state._resolve = resolve
      state.open = true
    })
  }

  function settle(value) {
    const resolve = state._resolve
    state._resolve = null
    state.open = false
    if (typeof resolve === 'function') resolve(value)
  }

  return { confirmState: state, confirm, settle }
}
