import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
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
})
