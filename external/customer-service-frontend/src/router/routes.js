import WorkbenchView from '../views/WorkbenchView.vue'
import SessionsView from '../views/SessionsView.vue'
import DashboardView from '../views/DashboardView.vue'
import SettingsView from '../views/SettingsView.vue'

/** path → 视图组件 */
export const routes = {
  '/': WorkbenchView,
  '/sessions': SessionsView,
  '/dashboard': DashboardView,
  '/settings': SettingsView,
}

/** 顶栏一级导航 */
export const NAV_ITEMS = [
  { path: '/', label: '工作台', icon: 'grid' },
  { path: '/sessions', label: '会话记录', icon: 'list' },
  { path: '/dashboard', label: '数据看板', icon: 'chart' },
  { path: '/settings', label: '系统设置', icon: 'settings' },
]

/** 未知路径回落工作台 */
export function resolveView(path) {
  return routes[path] || routes['/']
}
