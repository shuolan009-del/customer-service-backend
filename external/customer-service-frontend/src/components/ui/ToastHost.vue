<script setup>
import { useToast } from '../../composables/useToast'
import Icon from './Icon.vue'

const { items, dismiss } = useToast()

const ICON_MAP = { success: 'checkCircle', error: 'alert', warning: 'warning', info: 'info' }
</script>

<template>
  <div class="toast-host" role="status" aria-live="polite">
    <TransitionGroup name="toast">
      <div
        v-for="item in items"
        :key="item.id"
        class="toast"
        :class="`toast--${item.variant}`"
      >
        <span class="toast__icon"><Icon :name="ICON_MAP[item.variant] || 'info'" :size="16" /></span>
        <span class="toast__text">{{ item.message }}</span>
        <button type="button" class="toast__close" aria-label="关闭提示" @click="dismiss(item.id)">
          <Icon name="close" :size="14" />
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-host {
  position: fixed;
  top: var(--space-4);
  left: 50%;
  transform: translateX(-50%);
  z-index: var(--z-toast);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  align-items: center;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 220px;
  max-width: 420px;
  padding: 10px var(--space-4);
  border-radius: var(--radius-md);
  background: var(--ink-800);
  color: #fff;
  box-shadow: var(--shadow-lg);
  font-size: var(--text-base);
  pointer-events: auto;
}

.toast__icon { display: inline-flex; }
.toast__text { flex: 1; }
.toast__close {
  border: none;
  background: transparent;
  color: inherit;
  opacity: 0.7;
  cursor: pointer;
  display: inline-flex;
  padding: 2px;
}
.toast__close:hover { opacity: 1; }

.toast--success { background: var(--color-success); }
.toast--error { background: var(--color-danger); }
.toast--warning { background: var(--color-warning); }
.toast--info { background: var(--ink-800); }

.toast-enter-active,
.toast-leave-active {
  transition: opacity var(--duration-base) var(--ease-standard), transform var(--duration-base) var(--ease-standard);
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
