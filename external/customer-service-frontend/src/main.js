import { createApp } from 'vue'
import App from './App.vue'
import './styles/design-tokens.css'
import './styles/base.css'
/* 「02 · Stripe」主题层 —— 2026-10-16 试上线后按用户要求改回品牌绿，暂停启用。
   如需再启用：取消下一行注释即可（别名修复不受影响）。 */
// import './styles/theme-stripe.css'
import { readPrefs } from './utils/prefs'

/**
 * 「系统设置」保存的本地偏好（键见 utils/prefs.js）。
 * 启动时应用一次 —— 其中「减弱动效」必须在挂载前落到 <html> 上，
 * 否则首屏动画会先按系统设置跑一遍再被关掉。
 */
const prefs = readPrefs()
if (prefs.reduceMotion) {
  document.documentElement.dataset.reduceMotion = 'on'
}

createApp(App).mount('#app')
