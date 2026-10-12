<script setup>
import { ref } from 'vue'

/**
 * 注意：不提供 ariaLabel prop。Vue 3 的 fallthrough attr 会覆盖组件内同名绑定，
 * 提供 prop 反而会成为「永远不生效的死 prop」；无障碍标签由使用方透传：
 *   <SegmentedControl aria-label="业务对象类型" ... />
 */
const props = defineProps({
  modelValue: { type: String, default: '' },
  options: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:modelValue'])

const buttons = ref([])

function select(value) {
  emit('update:modelValue', value)
}

/** roving tabindex + ←/→ 方向键 */
function onKeydown(event, index) {
  const { key } = event
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(key)) return
  event.preventDefault()
  const count = props.options.length
  let next = index
  if (key === 'ArrowLeft') next = (index - 1 + count) % count
  else if (key === 'ArrowRight') next = (index + 1) % count
  else if (key === 'Home') next = 0
  else if (key === 'End') next = count - 1
  select(props.options[next].value)
  const target = buttons.value[next]
  if (target) target.focus()
}
</script>

<template>
  <div class="segmented" role="tablist">
    <button
      v-for="(option, index) in options"
      :key="option.value"
      ref="buttons"
      type="button"
      role="tab"
      class="segmented__item"
      :class="{ 'is-active': modelValue === option.value }"
      :aria-selected="modelValue === option.value"
      :tabindex="modelValue === option.value ? 0 : -1"
      @click="select(option.value)"
      @keydown="onKeydown($event, index)"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<style scoped>
.segmented {
  display: inline-flex;
  gap: var(--space-2);
}

.segmented__item {
  min-width: 80px;
  min-height: 38px;
  padding: 8px var(--space-4);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface);
  color: var(--color-text-primary);
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
  cursor: pointer;
  transition:
    background var(--duration-fast) var(--ease-in-out),
    border-color var(--duration-fast) var(--ease-in-out),
    color var(--duration-fast) var(--ease-in-out);
}

.segmented__item:hover:not(.is-active) {
  background: var(--surface-hover);
}

.segmented__item.is-active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: var(--color-on-primary);
}
</style>
