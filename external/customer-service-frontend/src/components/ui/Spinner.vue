<script setup>
defineProps({
  size: { type: Number, default: 16 },
  label: { type: String, default: '' },
})
</script>

<template>
  <span
    class="spinner"
    :style="{ width: `${size}px`, height: `${size}px` }"
    role="status"
    :aria-label="label || '加载中'"
  ></span>
</template>

<style scoped>
.spinner {
  display: inline-block;
  flex-shrink: 0;
  border-radius: 50%;
  border: 2px solid var(--border);
  border-top-color: var(--color-primary);
  animation: spinnerSpin 0.7s linear infinite;
}

@keyframes spinnerSpin {
  to { transform: rotate(360deg); }
}
</style>
