<script setup>
import { nextTick, ref, watch } from 'vue'
import Icon from './Icon.vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, default: '' },
  width: { type: Number, default: 480 },
})

const emit = defineEmits(['close'])

const panel = ref(null)
const closeBtn = ref(null)

function close() {
  emit('close')
}

function onKeydown(event) {
  if (event.key === 'Escape') {
    event.preventDefault()
    close()
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
  () => props.open,
  async (open) => {
    if (typeof document === 'undefined') return
    document.body.style.overflow = open ? 'hidden' : ''
    if (open) {
      await nextTick()
      closeBtn.value?.focus()
    }
  },
)
</script>

<template>
  <Teleport to="body">
    <Transition name="drawer">
      <div v-if="open" class="drawer-backdrop" @click.self="close" @keydown="onKeydown">
        <aside
          ref="panel"
          class="drawer"
          role="dialog"
          aria-modal="true"
          :aria-label="title"
          :style="{ width: `${width}px` }"
        >
          <header class="drawer__header">
            <h2 class="drawer__title">{{ title }}</h2>
            <button ref="closeBtn" type="button" class="drawer__close" aria-label="关闭抽屉" @click="close">
              <Icon name="close" :size="18" />
            </button>
          </header>
          <div class="drawer__body">
            <slot />
          </div>
          <footer v-if="$slots.footer" class="drawer__footer">
            <slot name="footer" />
          </footer>
        </aside>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.drawer-backdrop {
  position: fixed;
  inset: 0;
  z-index: var(--z-drawer);
  display: flex;
  justify-content: flex-end;
  background: rgba(15, 23, 42, 0.42);
}

.drawer {
  max-width: 100vw;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--surface);
  box-shadow: var(--shadow-lg);
}

.drawer__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-5) var(--space-6);
  border-bottom: 1px solid var(--border-light);
}

.drawer__title {
  font-size: var(--text-lg);
  font-weight: var(--weight-semibold);
}

.drawer__close {
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  display: inline-flex;
  padding: var(--space-1);
  border-radius: var(--radius-sm);
}

.drawer__close:hover {
  background: var(--surface-hover);
  color: var(--color-text-primary);
}

.drawer__body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: var(--space-6);
}

.drawer__footer {
  padding: var(--space-4) var(--space-6);
  border-top: 1px solid var(--border-light);
  background: var(--surface-raised);
}

.drawer-enter-active,
.drawer-leave-active {
  transition: opacity var(--duration-base) var(--ease-standard);
}
.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}
</style>
