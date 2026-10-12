<script setup>
/**
 * KPI 指标卡：标签 + 数值 + 可选环比/说明。
 * deltaVariant: success | danger | muted（不传则中性）
 */
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], default: '—' },
  unit: { type: String, default: '' },
  delta: { type: String, default: '' },
  deltaVariant: { type: String, default: 'muted' },
  hint: { type: String, default: '' },
})
</script>

<template>
  <div class="kpi">
    <div class="kpi__top">
      <span class="kpi__label">{{ label }}</span>
      <span v-if="$slots.icon" class="kpi__icon" aria-hidden="true"><slot name="icon" /></span>
    </div>
    <p class="kpi__value">
      {{ value }}<span v-if="unit" class="kpi__unit">{{ unit }}</span>
    </p>
    <div class="kpi__foot">
      <span v-if="delta" class="kpi__delta" :class="`kpi__delta--${deltaVariant}`">{{ delta }}</span>
      <span v-if="hint" class="kpi__hint">{{ hint }}</span>
    </div>
  </div>
</template>

<style scoped>
.kpi {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  height: 100%;
}

.kpi__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.kpi__label {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  font-weight: var(--weight-medium);
}

.kpi__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: var(--radius-sm);
  background: var(--color-primary-soft-bg);
  color: var(--color-primary);
}

.kpi__value {
  font-size: var(--text-2xl);
  font-weight: var(--weight-bold);
  color: var(--color-text-primary);
  letter-spacing: -0.02em;
  line-height: 1.15;
}

.kpi__unit {
  margin-left: 2px;
  font-size: var(--text-base);
  font-weight: var(--weight-medium);
  color: var(--color-text-muted);
}

.kpi__foot {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 18px;
  font-size: var(--text-xs);
}

.kpi__delta {
  font-weight: var(--weight-semibold);
}
.kpi__delta--success { color: var(--color-success); }
.kpi__delta--danger { color: var(--color-danger); }
.kpi__delta--muted { color: var(--color-text-muted); }

.kpi__hint {
  color: var(--color-text-muted);
}
</style>
