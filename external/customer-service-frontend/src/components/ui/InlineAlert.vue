<script setup>
import { computed } from 'vue'
import Icon from './Icon.vue'
import AppButton from './AppButton.vue'

const props = defineProps({
  /** danger | warning | info | success */
  variant: { type: String, default: 'danger' },
  message: { type: String, default: '' },
  retryable: { type: Boolean, default: false },
  closable: { type: Boolean, default: false },
})

defineEmits(['retry', 'close'])

const ICON_MAP = { danger: 'alert', warning: 'warning', info: 'info', success: 'checkCircle' }
const iconName = computed(() => ICON_MAP[props.variant] || 'alert')
</script>

<template>
  <div class="alert" :class="`alert--${variant}`" role="alert" aria-live="assertive">
    <span class="alert__icon"><Icon :name="iconName" :size="16" /></span>
    <p class="alert__message"><slot>{{ message }}</slot></p>
    <AppButton v-if="retryable" variant="ghost" size="sm" @click="$emit('retry')">重试</AppButton>
    <button
      v-if="closable"
      type="button"
      class="alert__close"
      aria-label="关闭提示"
      @click="$emit('close')"
    >
      <Icon name="close" :size="14" />
    </button>
  </div>
</template>

<style scoped>
.alert {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  border: 1px solid transparent;
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
}

.alert__icon {
  display: inline-flex;
  flex-shrink: 0;
}

.alert__message {
  flex: 1;
  min-width: 0;
  font-weight: var(--weight-medium);
}

.alert--danger {
  background: var(--color-danger-soft);
  border-color: var(--color-danger);
  color: var(--color-danger);
}

.alert--warning {
  background: var(--color-warning-soft);
  border-color: var(--color-warning);
  color: var(--color-warning);
}

.alert--info {
  background: var(--color-info-soft);
  border-color: var(--color-info);
  color: var(--color-info);
}

.alert--success {
  background: var(--color-success-soft);
  border-color: var(--color-success);
  color: var(--color-success);
}

.alert__close {
  border: none;
  background: transparent;
  color: inherit;
  cursor: pointer;
  padding: 2px;
  display: inline-flex;
}
</style>
