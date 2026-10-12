import { readonly, reactive } from 'vue'

/**
 * 极简零依赖 hash 路由（~40 行）。
 * - 监听 hashchange + popstate，reactive 一个 { path }
 * - 未知路径由调用方（routes.js 的 resolveView）回落 `#/`
 * - 不引入 vue-router；无需 Vite history 回落配置
 */

const DEFAULT_PATH = '/'

function normalize(rawHash) {
  let path = String(rawHash || '').replace(/^#/, '')
  const queryIndex = path.indexOf('?')
  if (queryIndex >= 0) path = path.slice(0, queryIndex)
  if (!path) return DEFAULT_PATH
  if (!path.startsWith('/')) path = `/${path}`
  // 去掉尾部多余斜杠（保留根 '/'）
  const trimmed = path.replace(/\/+$/, '')
  return trimmed || DEFAULT_PATH
}

const state = reactive({ path: normalize(typeof window !== 'undefined' ? window.location.hash : '') })

function syncFromLocation() {
  state.path = normalize(window.location.hash)
}

if (typeof window !== 'undefined') {
  window.addEventListener('hashchange', syncFromLocation)
  window.addEventListener('popstate', syncFromLocation)
  // 初次进入且无 hash 时补一个默认 hash，保证地址栏可读、可分享
  if (!window.location.hash) {
    window.location.replace(`${window.location.pathname}${window.location.search}#/`)
  }
}

/** 编程式导航 */
export function navigate(path) {
  const next = String(path || DEFAULT_PATH)
  const target = `#${next}`
  if (window.location.hash === target) {
    syncFromLocation()
    return
  }
  window.location.hash = next
}

export function useRoute() {
  return readonly(state)
}
