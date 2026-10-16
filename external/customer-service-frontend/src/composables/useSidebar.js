import { ref } from 'vue'
import { withPrefix } from '../config/api-base'

/**
 * 右侧「业务对象」栏数据（订单 / 商品列表）。
 * 模块级单例：切换 sender_id 后由 WorkbenchView 触发 fetch。
 *
 * 演示兜底（2026-10-16）：接口为空或失败时回退到内置虚拟数据，
 * 并置 isMock=true 供侧栏展示「演示数据」标识——保证任意 sender_id 下
 * 侧栏都有可展示的内容（演示/截图友好）。字段形状与真实接口一致。
 */

const MOCK_ORDERS = [
  { order_id: 'A20260410001', title: 'iPhone 15 Pro 256G 远峰蓝', amount: 8999, status: '待发货' },
  { order_id: 'A20260407004', title: 'Apple Watch Series 9 GPS 45mm', amount: 2999, status: '待揽收' },
  { order_id: 'A20260408002', title: '小米恒温电热水壶 3', amount: 149, status: '运输中' },
]

const MOCK_PRODUCTS = [
  { product_id: 'SKU10001', title: 'iPhone 15 Pro 256G 远峰蓝', price: 8999, description: '6.1 英寸超视网膜 XDR 显示屏，A17 Pro 芯片，支持 5 倍光学变焦。' },
  { product_id: 'SKU10006', title: '罗技 MX Master 3S 鼠标', price: 699, description: '静音微动，支持多设备切换，适合办公与设计。' },
  { product_id: 'SKU10005', title: '美的空气炸锅 5L', price: 399, description: '大容量可视窗设计，支持多菜单模式。' },
]

const orders = ref([])
const products = ref([])
const isLoading = ref(false)
const error = ref('')
const isMock = ref(false)
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
    isMock.value = false
    if (!sid) {
      /* 未填 sender_id：直接给演示数据，侧栏不空 */
      orders.value = MOCK_ORDERS
      products.value = MOCK_PRODUCTS
      isMock.value = true
      return
    }

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

      const nextOrders = Array.isArray(ordersPayload?.data?.orders) ? ordersPayload.data.orders : []
      const nextProducts = Array.isArray(productsPayload?.data?.products) ? productsPayload.data.products : []

      if (nextOrders.length === 0 && nextProducts.length === 0) {
        /* 真实数据为空 → 演示兜底 */
        orders.value = MOCK_ORDERS
        products.value = MOCK_PRODUCTS
        isMock.value = true
      } else {
        /* 单边为空时用演示数据补齐该边，保证两个 tab 都有内容 */
        orders.value = nextOrders.length ? nextOrders : MOCK_ORDERS
        products.value = nextProducts.length ? nextProducts : MOCK_PRODUCTS
        isMock.value = !nextOrders.length || !nextProducts.length
      }
    } catch (err) {
      if (seq !== loadSeq) return
      /* 接口失败 → 演示兜底（不再向用户抛错误横幅） */
      console.warn('[sidebar] 业务对象接口失败，回退演示数据：', err)
      orders.value = MOCK_ORDERS
      products.value = MOCK_PRODUCTS
      isMock.value = true
    } finally {
      if (seq === loadSeq) isLoading.value = false
    }
  }

  return { orders, products, isLoading, error, isMock, activeTab, load }
}
