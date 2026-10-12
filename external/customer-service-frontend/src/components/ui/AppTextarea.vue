<script setup>
defineProps({
  modelValue: { type: String, default: '' },
  id: { type: String, default: '' },
  rows: { type: Number, default: 4 },
  placeholder: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  autoGrow: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

function onInput(event) {
  emit('update:modelValue', event.target.value)
  if (autoGrow) {
    const el = event.target
    el.style.height = 'auto'
    el.style.height = `${el.scrollHeight}px`
  }
}
</script>

<template>
  <textarea
    class="textarea"
    :id="id || undefined"
    :rows="rows"
    :value="modelValue"
    :placeholder="placeholder"
    :disabled="disabled"
    @input="onInput"
  ></textarea>
</template>

<style scoped>
.textarea {
  width: 100%;
  min-height: 96px;
  padding: 11px 14px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-md);
  background: var(--surface-field);
  color: var(--color-text-primary);
  font-size: var(--text-md);
  font-family: inherit;
  line-height: 1.6;
  resize: vertical;
  transition:
    border-color var(--duration-fast) var(--ease-in-out),
    box-shadow var(--duration-fast) var(--ease-in-out);
}

.textarea::placeholder {
  color: var(--color-text-muted);
}

.textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: var(--focus-ring);
}
</style>
