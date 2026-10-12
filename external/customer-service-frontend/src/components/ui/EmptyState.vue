<script setup>
import Icon from './Icon.vue'

defineProps({
  icon: { type: String, default: 'inbox' },
  title: { type: String, default: '' },
  description: { type: String, default: '' },
})
</script>

<template>
  <div class="empty">
    <span class="empty__icon"><Icon :name="icon" :size="28" /></span>
    <p v-if="title" class="empty__title">{{ title }}</p>
    <p v-if="description" class="empty__desc">{{ description }}</p>
    <div v-if="$slots.action" class="empty__action">
      <slot name="action" />
    </div>
  </div>
</template>

<style scoped>
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-8) var(--space-4);
  text-align: center;
  color: var(--color-text-muted);
}

.empty__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  border-radius: var(--radius-full);
  background: var(--surface-hover);
  color: var(--ink-400);
  margin-bottom: var(--space-1);
}

.empty__title {
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
  color: var(--color-text-secondary);
}

.empty__desc {
  font-size: var(--text-sm);
  max-width: 320px;
  line-height: var(--leading-normal);
}

.empty__action {
  margin-top: var(--space-2);
}
</style>
