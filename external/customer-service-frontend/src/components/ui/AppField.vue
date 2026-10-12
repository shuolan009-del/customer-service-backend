<script setup>
defineProps({
  label: { type: String, default: '' },
  hint: { type: String, default: '' },
  error: { type: String, default: '' },
  forId: { type: String, default: '' },
  required: { type: Boolean, default: false },
})
</script>

<template>
  <div class="field">
    <div class="field__top">
      <label v-if="label" class="field__label" :for="forId || undefined">
        {{ label }}<span v-if="required" class="field__req" aria-hidden="true">*</span>
      </label>
      <slot name="label-right" />
    </div>
    <slot />
    <p v-if="error" class="field__error" role="alert">{{ error }}</p>
    <p v-else-if="hint" class="field__hint">{{ hint }}</p>
  </div>
</template>

<style scoped>
.field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.field__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  min-height: 20px;
}

.field__label {
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  color: var(--color-text-secondary);
}

.field__req {
  color: var(--color-danger);
  margin-left: 2px;
}

.field__hint {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.field__error {
  font-size: var(--text-xs);
  color: var(--color-danger);
}
</style>
