import { createApp } from 'vue'
import App from './App.vue'
import './styles/design-tokens.css'
import './styles/base.css'
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
