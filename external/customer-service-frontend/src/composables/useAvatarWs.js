import { reactive } from 'vue'

/**
 * 数字人聊天通道（WS /ws/avatar/chat）引擎。
 * - 指数退避重连：1s / 2s / 4s / 8s / 16s / 30s（上限 30s）
 * - 状态：idle | connecting | open | reconnecting | closed
 * - 仅负责连接与收发；业务侧通过 configure() 注入 onMessage / onStatus 回调
 */

const BACKOFF_STEPS = [1000, 2000, 4000, 8000, 16000, 30000]

const wsState = reactive({ status: 'idle' })

let socket = null
let handlers = {}
let attempt = 0
let retryTimer = null
let manualClose = false

function buildUrl() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/ws/avatar/chat`
}

export function useAvatarWs() {
  function configure(next) {
    handlers = { ...handlers, ...next }
  }

  function clearRetry() {
    if (retryTimer) {
      clearTimeout(retryTimer)
      retryTimer = null
    }
  }

  function scheduleRetry() {
    if (manualClose) return
    const delay = BACKOFF_STEPS[Math.min(attempt, BACKOFF_STEPS.length - 1)]
    attempt += 1
    wsState.status = 'reconnecting'
    clearRetry()
    retryTimer = setTimeout(connect, delay)
  }

  function connect() {
    manualClose = false
    clearRetry()
    if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
      return
    }
    wsState.status = attempt > 0 ? 'reconnecting' : 'connecting'
    try {
      socket = new WebSocket(buildUrl())
    } catch (error) {
      wsState.status = 'closed'
      scheduleRetry()
      return
    }
    socket.onopen = () => {
      attempt = 0
      wsState.status = 'open'
      handlers.onStatus?.('open')
    }
    socket.onmessage = (event) => handlers.onMessage?.(event)
    socket.onerror = () => {
      handlers.onStatus?.('error')
    }
    socket.onclose = () => {
      wsState.status = 'closed'
      handlers.onStatus?.('closed')
      scheduleRetry()
    }
  }

  function isOpen() {
    return socket?.readyState === WebSocket.OPEN
  }

  function send(payload) {
    if (!isOpen()) return false
    try {
      socket.send(JSON.stringify(payload))
      return true
    } catch (error) {
      return false
    }
  }

  function close() {
    manualClose = true
    clearRetry()
    attempt = 0
    if (socket) {
      try {
        socket.onopen = null
        socket.onmessage = null
        socket.onerror = null
        socket.onclose = null
        socket.close()
      } catch (error) {
        /* 忽略 */
      }
    }
    socket = null
    wsState.status = 'idle'
  }

  return { wsState, configure, connect, send, close, isOpen }
}
