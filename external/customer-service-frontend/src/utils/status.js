/**
 * 订单状态 → 展示样式映射。
 * 保留旧的三套 class（status-warning / status-info / ...）以兼容历史样式，
 * 同时提供 AppBadge 用的 variant 映射（success/warning/info/danger/muted）。
 */

export const ORDER_STATUS_CLASS = {
  '待发货': 'status-warning',
  '待揽收': 'status-warning',
  '运输中': 'status-info',
  '派送中': 'status-info',
  '已完成': 'status-success',
  '已签收': 'status-success',
  '已取消': 'status-muted',
  '退款中': 'status-danger',
  '已退款': 'status-muted',
}

const ORDER_STATUS_VARIANT = {
  '待发货': 'warning',
  '待揽收': 'warning',
  '运输中': 'info',
  '派送中': 'info',
  '已完成': 'success',
  '已签收': 'success',
  '已取消': 'muted',
  '退款中': 'danger',
  '已退款': 'muted',
}

export function getStatusClass(status) {
  return ORDER_STATUS_CLASS[status] || 'status-muted'
}

export function getStatusVariant(status) {
  return ORDER_STATUS_VARIANT[status] || 'muted'
}
