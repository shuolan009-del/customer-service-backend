<script setup>
import Spinner from './Spinner.vue'

defineProps({
  /** primary | secondary | ghost | danger | chip */
  variant: { type: String, default: 'secondary' },
  /** sm | md */
  size: { type: String, default: 'md' },
  block: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  type: { type: String, default: 'button' },
  title: { type: String, default: '' },
})

defineEmits(['click'])
</script>

<template>
  <button
    :type="type"
    class="btn"
    :class="[`btn--${variant}`, `btn--${size}`, { 'btn--block': block }]"
    :disabled="disabled || loading"
    :aria-busy="loading ? 'true' : undefined"
    :title="title || undefined"
    @click="$emit('click', $event)"
  >
    <Spinner v-if="loading" :size="14" />
    <slot name="icon" />
    <span class="btn__label"><slot /></span>
  </button>
</template>

<style scoped>
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  min-height: 42px;
  padding: 9px var(--space-4);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface);
  color: var(--color-text-primary);
  cursor: pointer;
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
  line-height: 1.2;
  white-space: nowrap;
  transition:
    background var(--duration-fast) var(--ease-in-out),
    border-color var(--duration-fast) var(--ease-in-out),
    box-shadow var(--duration-fast) var(--ease-standard),
    transform var(--duration-fast) var(--ease-standard);
}

.btn:hover:not(:disabled) {
  box-shadow: var(--shadow-sm);
  transform: translateY(-1px);
}

.btn:active:not(:disabled) {
  transform: translateY(0);
}

.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.btn--block {
  width: 100%;
}

.btn--sm {
  min-height: 34px;
  padding: 6px var(--space-3);
  font-size: var(--text-sm);
}

/* 主按钮 */
.btn--primary {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: var(--color-on-primary);
}

.btn--primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
  border-color: var(--color-primary-hover);
}

.btn--primary:active:not(:disabled) {
  background: var(--color-primary-active);
}

/* 次级按钮 */
.btn--secondary:hover:not(:disabled) {
  background: var(--color-primary-soft-bg);
  border-color: var(--color-primary-soft);
}

/* 幽灵按钮 */
.btn--ghost {
  background: transparent;
  border-color: transparent;
  color: var(--color-text-secondary);
}

.btn--ghost:hover:not(:disabled) {
  background: var(--color-primary-soft-bg);
  color: var(--color-primary);
}

/* 危险按钮 */
.btn--danger {
  background: var(--color-danger-soft);
  border-color: var(--color-danger);
  color: var(--color-danger);
}

.btn--danger:hover:not(:disabled) {
  background: var(--color-danger);
  color: var(--color-on-primary);
}

/* chip 胶囊按钮 */
.btn--chip {
  min-height: 0;
  padding: 8px 18px;
  border-radius: var(--radius-full);
  background: var(--color-primary-soft-bg);
  border-color: var(--border);
  color: var(--color-primary);
  font-weight: var(--weight-medium);
}

.btn--chip:hover:not(:disabled) {
  background: var(--color-primary-soft);
  border-color: var(--color-primary);
}
</style>
