<script setup>
import AppBadge from './AppBadge.vue'
import EmptyState from './EmptyState.vue'

/**
 * 轻量统计表（零依赖，无虚拟滚动）。
 * columns: [{ key, label, align?: 'left'|'right'|'center', width?: string }]
 * rows: [{ [key]: 任意 }]
 * 单元格可用 #cell-<key> 具名插槽自定义渲染，作用域为 { row, value }。
 */
defineProps({
  title: { type: String, default: '' },
  columns: { type: Array, default: () => [] },
  rows: { type: Array, default: () => [] },
  rowKey: { type: String, default: 'id' },
  sample: { type: Boolean, default: false },
})
</script>

<template>
  <section class="table-wrap">
    <header v-if="title || sample" class="table-wrap__head">
      <h3 v-if="title" class="table-wrap__title">{{ title }}</h3>
      <AppBadge v-if="sample" variant="warning" size="sm">示例数据</AppBadge>
    </header>

    <div v-if="rows.length" class="table-wrap__scroll">
      <table class="table">
        <thead>
          <tr>
            <th
              v-for="column in columns"
              :key="column.key"
              scope="col"
              :style="{ textAlign: column.align || 'left', width: column.width }"
            >
              {{ column.label }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row[rowKey]">
            <td
              v-for="column in columns"
              :key="column.key"
              :style="{ textAlign: column.align || 'left' }"
            >
              <slot :name="`cell-${column.key}`" :row="row" :value="row[column.key]">
                {{ row[column.key] }}
              </slot>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <EmptyState v-else title="暂无数据" description="没有可展示的记录。" />
  </section>
</template>

<style scoped>
.table-wrap {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.table-wrap__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.table-wrap__title {
  font-size: var(--text-lg);
  font-weight: var(--weight-semibold);
}

.table-wrap__scroll {
  overflow-x: auto;
}

.table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-base);
}

.table th {
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}

.table td {
  padding: var(--space-3);
  border-bottom: 1px solid var(--border-light);
  color: var(--color-text-primary);
  vertical-align: middle;
}

.table tbody tr:hover td {
  background: var(--surface-hover);
}

.table tbody tr:last-child td {
  border-bottom: none;
}
</style>
