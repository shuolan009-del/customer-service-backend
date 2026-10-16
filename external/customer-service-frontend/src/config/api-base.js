/**
 * 部署前缀适配（单一事实源）。
 *
 * 背景：服务器部署（方案A）时，前端挂在同源 /cs/ 前缀下（由 Caddy 分流），
 * 而 /api、/commerce、/ws 等后端请求路径必须随之带上 /cs 前缀，
 * 否则会落到同源根路径上的其他服务（嘉禾控制台），造成 404 / 串服务。
 *
 * - 本机开发：vite base 为 '/' → API_PREFIX 为空串 → withPrefix 原样返回，
 *   全部请求仍走 vite dev 代理（与改动前行为完全一致）
 * - 服务器构建：vite base 为 '/cs/' → API_PREFIX 为 '/cs'
 *
 * 路由对照（Caddy，见服务器 Caddyfile）：
 *   /cs/api/...      → 127.0.0.1:18082（客服后端，前缀剥离后即 /api/...）
 *   /cs/commerce/... → 127.0.0.1:18081（电商后端，剥离 /cs/commerce 后即 /users/...）
 *   /cs/ws/...       → 127.0.0.1:18082（WebSocket 聊天通道）
 */
export const API_PREFIX = String(import.meta.env.BASE_URL || '/').replace(/\/+$/, '')

/** 给以 / 开头的后端请求路径加部署前缀（本机开发时原样返回） */
export function withPrefix(path) {
  return API_PREFIX + path
}

/** 门户地址：本机开发指向 5174；服务器构建指向同源 /portal/ */
export const PORTAL_URL = import.meta.env.DEV ? 'http://127.0.0.1:5174/' : '/portal/'
