<script setup>
/**
 * 管理端页面头：标题 + 副标题 + 面包屑 + 右侧操作区。
 * 三个管理端视图（会话记录 / 数据看板 / 系统设置）共用。
 */
import Icon from '../ui/Icon.vue'

defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  /** [{ label, path? }]，最后一项为当前页（不可点） */
  breadcrumb: { type: Array, default: () => [] },
})

const emit = defineEmits(['navigate'])
</script>

<template>
  <header class="page-header">
    <nav v-if="breadcrumb.length" class="crumbs" aria-label="面包屑">
      <template v-for="(crumb, index) in breadcrumb" :key="crumb.label">
        <button
          v-if="crumb.path && index !== breadcrumb.length - 1"
          type="button"
          class="crumbs__link"
          @click="emit('navigate', crumb.path)"
        >
          {{ crumb.label }}
        </button>
        <span v-else class="crumbs__current" aria-current="page">{{ crumb.label }}</span>
        <span v-if="index !== breadcrumb.length - 1" class="crumbs__sep" aria-hidden="true">
          <Icon name="chevron-right" :size="12" />
        </span>
      </template>
    </nav>

    <div class="page-header__row">
      <div class="page-header__text">
        <h1 class="page-header__title">{{ title }}</h1>
        <p v-if="subtitle" class="page-header__subtitle">{{ subtitle }}</p>
      </div>
      <div v-if="$slots.actions" class="page-header__actions">
        <slot name="actions" />
      </div>
    </div>
  </header>
</template>

<style scoped>
.page-header {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-bottom: var(--space-6);
}

.crumbs {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.crumbs__link {
  border: none;
  background: transparent;
  padding: 0;
  cursor: pointer;
  color: var(--color-text-muted);
  font-size: inherit;
  border-radius: var(--radius-xs);
}
.crumbs__link:hover {
  color: var(--color-primary);
  text-decoration: underline;
}

.crumbs__current {
  color: var(--color-text-secondary);
  font-weight: var(--weight-medium);
}

.crumbs__sep {
  display: inline-flex;
  color: var(--ink-300);
}

.page-header__row {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-4);
  flex-wrap: wrap;
}

.page-header__title {
  font-size: var(--text-xl);
  font-weight: var(--weight-bold);
  color: var(--color-text-primary);
  letter-spacing: -0.01em;
}

.page-header__subtitle {
  margin-top: var(--space-1);
  font-size: var(--text-base);
  color: var(--color-text-secondary);
  line-height: var(--leading-normal);
}

.page-header__actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}
</style>
