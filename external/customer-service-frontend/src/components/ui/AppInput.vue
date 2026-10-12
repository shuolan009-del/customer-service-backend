<script setup>
defineProps({
  modelValue: { type: [String, Number], default: '' },
  id: { type: String, default: '' },
  type: { type: String, default: 'text' },
  placeholder: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  autocomplete: { type: String, default: 'off' },
})

const emit = defineEmits(['update:modelValue', 'enter'])

function onInput(event) {
  emit('update:modelValue', event.target.value)
}

function onKeydown(event) {
  if (event.key === 'Enter') emit('enter', event)
}
</script>

<template>
  <input
    class="input"
    :id="id || undefined"
    :type="type"
    :value="modelValue"
    :placeholder="placeholder"
    :disabled="disabled"
    :autocomplete="autocomplete"
    @input="onInput"
    @keydown="onKeydown"
  />
</template>

<style scoped>
.input {
  width: 100%;
  min-width: 0;
  min-height: 46px;
  padding: 11px 14px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-md);
  background: var(--surface-field);
  color: var(--color-text-primary);
  font-size: var(--text-md);
  line-height: 1.4;
  transition:
    border-color var(--duration-fast) var(--ease-in-out),
    box-shadow var(--duration-fast) var(--ease-in-out);
}

.input::placeholder {
  color: var(--color-text-muted);
}

.input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: var(--focus-ring);
}

.input:disabled {
  background: var(--surface-hover);
  cursor: not-allowed;
  opacity: 0.8;
}
</style>
