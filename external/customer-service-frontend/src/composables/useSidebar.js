import { ref } from 'vue'
import { withPrefix } from '../config/api-base'

/**
 * 右侧「业务对象」栏数据（订单 / 商品列表）。
 * 模块级单例：切换 sender_id 后由 WorkbenchView 触发 fetch。
 */

const orders = ref([])
const products = ref([])
const isLoading = ref(false)
const error = ref('')
const activeTab = ref('orders')

export function useSidebar() {
  /**
   * 请求序号：快速切换 sender_id 时，先发的请求可能后返回。
   * 过期响应直接丢弃，避免旧身份的订单/商品写进当前列表。
   */
  let loadSeq = 0

  async function load(senderId) {
    const sid = String(senderId ?? '').trim()
    orders.value = []
    products.value = []
    error.value = ''
    if (!sid) return

    const seq = ++loadSeq
    isLoading.value = true
    try {
      const [ordersResponse, productsResponse] = await Promise.all([
        fetch(withPrefix(`/commerce/users/${encodeURIComponent(sid)}/orders`)),
        fetch(withPrefix(`/commerce/users/${encodeURIComponent(sid)}/products`)),
      ])

      const [ordersPayload, productsPayload] = await Promise.all([
        ordersResponse.json(),
        productsResponse.json(),
      ])

      if (seq !== loadSeq) return

      if (!ordersResponse.ok) {
        throw new Error(ordersPayload.detail || '加载订单列表失败。')
      }
      if (!productsResponse.ok) {
        throw new Error(productsPayload.detail || '加载商品列表失败。')
      }

      orders.value = Array.isArray(ordersPayload?.data?.orders) ? ordersPayload.data.orders : []
      products.value = Array.isArray(productsPayload?.data?.products) ? productsPayload.data.products : []
    } catch (err) {
      if (seq !== loadSeq) return
      error.value = err instanceof Error ? err.message : '加载右侧列表失败。'
    } finally {
      if (seq === loadSeq) isLoading.value = false
    }
  }

  return { orders, products, isLoading, error, activeTab, load }
}
