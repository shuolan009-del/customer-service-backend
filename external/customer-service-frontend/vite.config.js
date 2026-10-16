import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

/**
 * - 本机开发：base 为 '/'，dev 代理不变（5173 → 18082 / 18081）
 * - 服务器部署（方案A，2026-10-14）：构建产物挂在同源 /cs/ 前缀下，
 *   故 build 时 base 取 '/cs'；配合 src/config/api-base.js 的请求前缀适配。
 */
export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/cs/' : '/',
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:18082',
        changeOrigin: true,
      },
      '/commerce': {
        target: 'http://127.0.0.1:18081',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/commerce/, ''),
      },
      '/health': {
        target: 'http://127.0.0.1:18082',
        changeOrigin: true,
      },
      // 数字人聊天通道（/ws/avatar/chat），必须开 ws: true 才能转发 WebSocket
      '/ws': {
        target: 'ws://127.0.0.1:18082',
        ws: true,
        changeOrigin: true,
      },
    },
  },
}))
