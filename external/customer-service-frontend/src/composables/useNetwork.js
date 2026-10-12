import { onMounted, onUnmounted, ref } from 'vue'

/**
 * 网络在线/离线状态（顶栏离线 pill 用）。
 */
export function useNetwork() {
  const online = ref(typeof navigator !== 'undefined' ? navigator.onLine : true)

  const update = () => { online.value = navigator.onLine }

  onMounted(() => {
    window.addEventListener('online', update)
    window.addEventListener('offline', update)
  })
  onUnmounted(() => {
    window.removeEventListener('online', update)
    window.removeEventListener('offline', update)
  })

  return { online }
}
