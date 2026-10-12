<script setup>
import { computed, ref } from 'vue'
import AppBadge from '../ui/AppBadge.vue'
import Icon from '../ui/Icon.vue'
import {
  getObjectAmount,
  getObjectIdentifier,
  getObjectSummary,
  getObjectTitle,
} from '../../utils/format'
import { getStatusVariant } from '../../utils/status'

/**
 * 业务对象卡（订单 / 商品）。
 * 只读展示，供消息流内的对象消息与右侧列表复用。
 * 横向布局：左侧封面 64px，右侧标题 / 编号 / 状态 / 金额 —— 比竖向卡片矮得多，
 * 不会把连续对话流割断。
 */
const props = defineProps({
  message: { type: Object, required: true },
})

const imageFailed = ref(false)

const isOrder = computed(() => props.message.objectType === 'order')
const payload = computed(() => props.message.payload ?? {})
const coverUrl = computed(() => payload.value.cover_url || '')
const status = computed(() =>
  isOrder.value ? payload.value.status ?? payload.value.attributes?.status : '',
)
const showCover = computed(() => Boolean(coverUrl.value) && !imageFailed.value)
</script>

<template>
  <article class="object-card" :class="`object-card--${isOrder ? 'order' : 'product'}`">
    <div class="object-card__media">
      <img
        v-if="showCover"
        class="object-card__image"
        :src="coverUrl"
        :alt="getObjectTitle(message)"
        @error="imageFailed = true"
      />
      <span v-else class="object-card__placeholder" aria-hidden="true">
        <Icon :name="isOrder ? 'package' : 'bag'" :size="22" />
      </span>
    </div>

    <div class="object-card__body">
      <header class="object-card__head">
        <AppBadge :variant="isOrder ? 'info' : 'primary'" size="sm">
          {{ isOrder ? '订单' : '商品' }}
        </AppBadge>
        <span class="object-card__amount">{{ getObjectAmount(message) }}</span>
      </header>

      <h4 class="object-card__title">{{ getObjectTitle(message) }}</h4>

      <p class="object-card__meta">
        <span>{{ getObjectIdentifier(message) }}</span>
      </p>

      <p class="object-card__meta">
        <AppBadge v-if="status" :variant="getStatusVariant(status)" size="sm">{{ status }}</AppBadge>
        <span v-else>{{ getObjectSummary(message) }}</span>
      </p>
    </div>
  </article>
</template>

<style scoped>
.object-card {
  display: flex;
  gap: var(--space-3);
  align-items: stretch;
  padding: var(--space-3);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface);
  width: min(320px, 100%);
}

.object-card__media {
  flex-shrink: 0;
  width: 64px;
  height: 64px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--surface-hover);
}

.object-card__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.object-card__placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  color: var(--ink-400);
}

.object-card__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
  flex: 1;
}

.object-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.object-card__amount {
  font-size: var(--text-base);
  font-weight: var(--weight-bold);
  color: var(--color-danger);
  white-space: nowrap;
}

.object-card__title {
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
  color: var(--color-text-primary);
  line-height: var(--leading-tight);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.object-card__meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  line-height: var(--leading-normal);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.object-card--order {
  border-color: var(--color-info-soft);
}
</style>
