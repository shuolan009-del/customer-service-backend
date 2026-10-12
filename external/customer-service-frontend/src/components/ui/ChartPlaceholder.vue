<script setup>
import { computed } from 'vue'
import AppBadge from './AppBadge.vue'
import EmptyState from './EmptyState.vue'

/**
 * 零依赖柱状图占位组件（纯 CSS，无 canvas/SVG 库）。
 * 后端当前没有看板聚合接口，故本组件仅用于「示例数据」展示。
 */
const props = defineProps({
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  /** [{ label, value }] */
  series: { type: Array, default: () => [] },
  height: { type: Number, default: 180 },
  /** 是否为示例数据（显示「示例数据」徽标） */
  sample: { type: Boolean, default: true },
})

const maxValue = computed(() => {
  const values = props.series.map((item) => Number(item.value) || 0)
  return Math.max(1, ...values)
})

function barHeight(value) {
  const numeric = Number(value) || 0
  return `${Math.max(2, Math.round((numeric / maxValue.value) * 100))}%`
}
</script>

<template>
  <section class="chart">
    <header class="chart__head">
      <div>
        <h3 class="chart__title">{{ title }}</h3>
        <p v-if="subtitle" class="chart__subtitle">{{ subtitle }}</p>
      </div>
      <AppBadge v-if="sample" variant="warning" size="sm">示例数据</AppBadge>
    </header>

    <div v-if="series.length" class="chart__body" :style="{ height: `${height}px` }">
      <div v-for="item in series" :key="item.label" class="chart__col">
        <span class="chart__value">{{ item.value }}</span>
        <span class="chart__bar" :style="{ height: barHeight(item.value) }"></span>
        <span class="chart__label">{{ item.label }}</span>
      </div>
    </div>

    <EmptyState v-else title="暂无数据" description="等待后端看板聚合接口接入。" />
  </section>
</template>

<style scoped>
.chart {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.chart__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
}

.chart__title {
  font-size: var(--text-lg);
  font-weight: var(--weight-semibold);
  color: var(--color-text-primary);
}

.chart__subtitle {
  margin-top: var(--space-1);
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

.chart__body {
  display: flex;
  align-items: flex-end;
  gap: var(--space-3);
  padding-top: var(--space-5);
  border-bottom: 1px solid var(--border);
}

.chart__col {
  flex: 1;
  min-width: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-2);
}

.chart__value {
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  color: var(--color-text-secondary);
}

.chart__bar {
  width: 100%;
  max-width: 42px;
  min-height: 2px;
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
  background: var(--color-primary);
  opacity: 0.85;
  transition: height var(--duration-slow) var(--ease-out);
}

.chart__col:hover .chart__bar {
  opacity: 1;
}

.chart__label {
  padding-bottom: var(--space-2);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}
</style>
