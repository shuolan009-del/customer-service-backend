<script setup>
import { computed } from 'vue'
import AppButton from '../ui/AppButton.vue'
import EmptyState from '../ui/EmptyState.vue'
import InlineAlert from '../ui/InlineAlert.vue'
import SegmentedControl from '../ui/SegmentedControl.vue'
import Skeleton from '../ui/Skeleton.vue'
import Icon from '../ui/Icon.vue'
import ObjectCard from './ObjectCard.vue'
import { useChat } from '../../composables/useChat'
import { useSidebar } from '../../composables/useSidebar'

/**
 * 右侧「业务对象」栏：把订单 / 商品作为对象消息发给客服。
 * 卡片复用 MessageStream 同款 ObjectCard，保证流内流外观感一致。
 *
 * 可收起模式（2026-10-16）：collapsed=true 时整栏收为一条竖向轨道，
 * 默认收起；点击轨道展开，展开态右上角按钮收回。
 */

const props = defineProps({
  /** true = 收起为竖向轨道 */
  collapsed: { type: Boolean, default: false },
})
const emit = defineEmits(['toggle'])

const { senderId, isSending, sendOrder, sendProduct } = useChat()
const { orders, products, isLoading, error, isMock, activeTab, load } = useSidebar()

const TABS = [
  { value: 'orders', label: '订单' },
  { value: 'products', label: '商品' },
]

const list = computed(() => (activeTab.value === 'orders' ? orders.value : products.value))
const isOrderTab = computed(() => activeTab.value === 'orders')
const isEmptyList = computed(() => !isLoading.value && list.value.length === 0)

/** 把列表原始数据包装成 ObjectCard 期望的消息结构 */
function toCardMessage(item) {
  return isOrderTab.value
    ? { objectType: 'order', payload: item }
    : { objectType: 'product', payload: item }
}

function itemKey(item) {
  return isOrderTab.value ? item.order_id : item.product_id
}

function send(item) {
  if (isOrderTab.value) sendOrder(item)
  else sendProduct(item)
}
</script>

<template>
  <!-- 收起态：竖向轨道，点击展开 -->
  <aside v-if="collapsed" class="sidebar sidebar--rail">
    <button
      type="button"
      class="rail-btn"
      title="展开业务对象"
      aria-label="展开业务对象栏"
      @click="emit('toggle')"
    >
      <Icon name="chevron-left" :size="16" />
      <span class="rail-btn__label">业务对象</span>
      <span class="rail-btn__count">{{ list.length }}</span>
    </button>
  </aside>

  <!-- 展开态 -->
  <aside v-else class="sidebar">
    <header class="sidebar__header">
      <h2 class="sidebar__title">
        <Icon name="list" :size="16" />
        <span>业务对象</span>
        <span v-if="isMock" class="sidebar__mock" title="接口无数据或不可用时展示的内置演示数据">演示数据</span>
      </h2>
      <div class="sidebar__actions">
        <AppButton
          variant="ghost"
          size="sm"
          :loading="isLoading"
          title="重新加载该 sender_id 的订单与商品"
          aria-label="刷新业务对象列表"
          @click="load(senderId)"
        >
          <template #icon><Icon name="refresh" :size="15" /></template>
        </AppButton>
        <button
          type="button"
          class="iconbtn"
          title="收起业务对象栏"
          aria-label="收起业务对象栏"
          @click="emit('toggle')"
        >
          <Icon name="chevron-right" :size="15" />
        </button>
      </div>
    </header>

    <SegmentedControl v-model="activeTab" :options="TABS" aria-label="业务对象类型" />

    <p class="sidebar__hint">
      发送给「{{ senderId || '未填写' }}」· 共 {{ list.length }} 条
    </p>

    <InlineAlert v-if="error" variant="danger" :message="error" retryable @retry="load(senderId)" />

    <div class="sidebar__list">
      <Skeleton v-if="isLoading" variant="list-item" :rows="3" />

      <EmptyState
        v-else-if="isEmptyList"
        :icon="isOrderTab ? 'package' : 'bag'"
        :title="isOrderTab ? '暂无订单数据' : '暂无商品数据'"
        :description="`该 sender_id 下没有可展示的${isOrderTab ? '订单' : '商品'}。`"
      />

      <template v-else>
        <article v-for="(item, index) in list" :key="itemKey(item) ?? index" class="sidebar__item">
          <ObjectCard :message="toCardMessage(item)" />
          <AppButton
            size="sm"
            variant="secondary"
            block
            :disabled="isSending"
            @click="send(item)"
          >
            {{ isOrderTab ? '发送订单' : '发送商品' }}
          </AppButton>
        </article>
      </template>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  min-height: 0;
}

.sidebar__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  flex-shrink: 0;
}

.sidebar__title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-md);
  font-weight: var(--weight-semibold);
  color: var(--color-text-primary);
}

.sidebar__actions {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}

.iconbtn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: border-color var(--duration-fast) var(--ease-in-out), color var(--duration-fast) var(--ease-in-out);
}
.iconbtn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

/* 「演示数据」标识 */
.sidebar__mock {
  padding: 1px 7px;
  border-radius: var(--radius-full);
  border: 1px solid var(--color-warning-soft);
  background: var(--color-warning-soft);
  color: var(--color-warning);
  font-size: 11px;
  font-weight: var(--weight-semibold);
  white-space: nowrap;
}

.sidebar__hint {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.sidebar__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  overflow-y: auto;
  min-height: 0;
  flex: 1;
  padding-right: 2px;
}

.sidebar__item {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  background: var(--surface-raised);
  transition: border-color var(--duration-fast) var(--ease-in-out);
}

.sidebar__item:hover {
  border-color: var(--border-strong);
}

/* 卡在窄栏里撑满宽度 */
.sidebar__item :deep(.object-card) {
  width: 100%;
}

/* ── 收起态：竖向轨道 ─────────────────────────────────────────────── */
.sidebar--rail {
  padding: var(--space-2);
}

.rail-btn {
  width: 100%;
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-in-out), color var(--duration-fast) var(--ease-in-out);
}

.rail-btn:hover {
  background: var(--color-primary-soft-bg);
  color: var(--color-primary);
}

.rail-btn__label {
  writing-mode: vertical-rl;
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  letter-spacing: 0.42em;
}

.rail-btn__count {
  min-width: 22px;
  padding: 1px 6px;
  border-radius: var(--radius-full);
  background: var(--color-primary-soft-bg);
  color: var(--color-primary);
  font-size: 11px;
  font-weight: var(--weight-semibold);
  font-variant-numeric: tabular-nums;
}

/* 窄屏堆叠时轨道改横向 */
@media (max-width: 1179px) {
  .sidebar--rail {
    padding: var(--space-2);
  }

  .rail-btn {
    flex-direction: row;
    gap: var(--space-2);
    min-height: 44px;
    padding: var(--space-2) var(--space-3);
  }

  .rail-btn__label {
    writing-mode: horizontal-tb;
    letter-spacing: 0.24em;
  }
}
</style>
