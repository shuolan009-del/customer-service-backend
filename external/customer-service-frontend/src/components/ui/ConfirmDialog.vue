<script setup>
import { nextTick, ref, watch } from 'vue'
import { useConfirm } from '../../composables/useConfirm'
import AppButton from './AppButton.vue'

const { confirmState, settle } = useConfirm()
const panel = ref(null)
const confirmBtn = ref(null)

function onKeydown(event) {
  if (event.key === 'Escape') {
    event.preventDefault()
    settle(false)
    return
  }
  if (event.key !== 'Tab') return
  const focusables = panel.value?.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')
  if (!focusables || focusables.length === 0) return
  const list = Array.from(focusables)
  const first = list[0]
  const last = list[list.length - 1]
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}

watch(
  () => confirmState.open,
  async (open) => {
    if (typeof document === 'undefined') return
    document.body.style.overflow = open ? 'hidden' : ''
    if (open) {
      await nextTick()
      confirmBtn.value?.focus()
    }
  },
)
</script>

<template>
  <Teleport to="body">
    <Transition name="dialog">
      <div
        v-if="confirmState.open"
        class="dialog-backdrop"
        @click.self="settle(false)"
        @keydown="onKeydown"
      >
        <div
          ref="panel"
          class="dialog"
          role="alertdialog"
          aria-modal="true"
          :aria-label="confirmState.title"
        >
          <h2 class="dialog__title">{{ confirmState.title }}</h2>
          <p v-if="confirmState.description" class="dialog__desc">{{ confirmState.description }}</p>
          <div class="dialog__actions">
            <AppButton variant="secondary" @click="settle(false)">{{ confirmState.cancelText }}</AppButton>
            <AppButton
              ref="confirmBtn"
              :variant="confirmState.danger ? 'danger' : 'primary'"
              @click="settle(true)"
            >
              {{ confirmState.confirmText }}
            </AppButton>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.dialog-backdrop {
  position: fixed;
  inset: 0;
  z-index: var(--z-dialog);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-4);
  background: rgba(15, 23, 42, 0.42);
}

.dialog {
  width: min(420px, 100%);
  padding: var(--space-6);
  background: var(--surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
}

.dialog__title {
  font-size: var(--text-lg);
  font-weight: var(--weight-semibold);
  color: var(--color-text-primary);
}

.dialog__desc {
  margin-top: var(--space-2);
  font-size: var(--text-base);
  line-height: var(--leading-normal);
  color: var(--color-text-secondary);
}

.dialog__actions {
  margin-top: var(--space-6);
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
}

.dialog-enter-active,
.dialog-leave-active {
  transition: opacity var(--duration-base) var(--ease-standard);
}
.dialog-enter-from,
.dialog-leave-to {
  opacity: 0;
}
</style>
