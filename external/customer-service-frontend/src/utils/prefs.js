/**
 * 本机偏好（localStorage，键 cs-prefs）的唯一读写入口。
 * 「系统设置」页写入，启动时（main.js）与工作台（applyPrefs）读取。
 */

const PREF_KEY = 'cs-prefs'

/** 读取偏好；本地存储不可用或数据损坏时返回空对象，绝不抛错 */
export function readPrefs() {
  try {
    return JSON.parse(localStorage.getItem(PREF_KEY) || '{}') || {}
  } catch (error) {
    return {}
  }
}

/** 写入偏好；调用方负责 try/catch（存储配额满等场景） */
export function writePrefs(prefs) {
  localStorage.setItem(PREF_KEY, JSON.stringify(prefs))
}
