<script setup>
defineProps({
  as: { type: String, default: 'div' },
  padded: { type: Boolean, default: true },
  hoverable: { type: Boolean, default: false },
})
</script>

<template>
  <component
    :is="as"
    class="card"
    :class="{ 'card--padded': padded, 'card--hoverable': hoverable }"
  >
    <header v-if="$slots.header" class="card__header">
      <slot name="header" />
    </header>
    <div class="card__body">
      <slot />
    </div>
    <footer v-if="$slots.footer" class="card__footer">
      <slot name="footer" />
    </footer>
  </component>
</template>

<style scoped>
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition:
    border-color var(--duration-base) var(--ease-in-out),
    background var(--duration-base) var(--ease-in-out),
    box-shadow var(--duration-base) var(--ease-in-out);
}

.card--padded .card__body {
  padding: var(--space-5) var(--space-6);
}

.card--hoverable:hover {
  background: var(--surface-hover);
  border-color: var(--border-strong);
  box-shadow: var(--shadow-sm);
}

.card__header {
  padding: var(--space-4) var(--space-6);
  border-bottom: 1px solid var(--border-light);
}

.card__footer {
  padding: var(--space-4) var(--space-6);
  border-top: 1px solid var(--border-light);
  background: var(--surface-raised);
}
</style>
