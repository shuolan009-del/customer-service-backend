<script setup>
defineProps({
  /** success | warning | info | danger | muted | primary */
  variant: { type: String, default: 'muted' },
  /** sm | md */
  size: { type: String, default: 'md' },
})
</script>

<template>
  <span class="badge" :class="[`badge--${variant}`, `badge--${size}`]">
    <slot />
  </span>
</template>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 12px;
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  letter-spacing: 0.02em;
  border: 1px solid transparent;
  white-space: nowrap;
}

.badge--sm {
  padding: 2px 9px;
  font-size: 11px;
}

.badge--success {
  background: var(--color-success-soft);
  color: var(--color-success);
  border-color: var(--color-success);
}

.badge--warning {
  background: var(--color-warning-soft);
  color: var(--color-warning);
  border-color: var(--color-warning);
}

.badge--info {
  background: var(--color-info-soft);
  color: var(--color-info);
  border-color: var(--color-info);
}

.badge--danger {
  background: var(--color-danger-soft);
  color: var(--color-danger);
  border-color: var(--color-danger);
}

.badge--muted {
  background: var(--border-light);
  color: var(--color-text-muted);
  border-color: var(--border);
}

.badge--primary {
  background: var(--color-primary-soft);
  color: var(--color-primary);
  border-color: var(--color-primary-soft);
}
</style>
