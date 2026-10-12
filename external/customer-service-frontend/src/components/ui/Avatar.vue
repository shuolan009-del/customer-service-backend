<script setup>
defineProps({
  src: { type: String, required: true },
  alt: { type: String, required: true },
  size: { type: Number, default: 42 },
  /** plain | primary | success | gradient */
  ring: { type: String, default: 'plain' },
  statusDot: { type: Boolean, default: false },
})
</script>

<template>
  <span
    class="avatar"
    :class="`avatar--${ring}`"
    :style="{ width: `${size}px`, height: `${size}px` }"
  >
    <img class="avatar__img" :src="src" :alt="alt" />
    <span v-if="statusDot" class="avatar__dot" aria-hidden="true"></span>
  </span>
</template>

<style scoped>
.avatar {
  position: relative;
  display: inline-block;
  flex-shrink: 0;
  border-radius: var(--radius-full);
}

.avatar__img {
  width: 100%;
  height: 100%;
  border-radius: var(--radius-full);
  object-fit: cover;
  display: block;
}

.avatar--plain .avatar__img {
  border: 2px solid var(--border);
  background: var(--surface-hover);
}

.avatar--primary {
  padding: 3px;
  background: var(--color-primary);
}

.avatar--success {
  padding: 2px;
  background: var(--surface);
}

.avatar--success .avatar__img {
  border: 2px solid var(--color-success);
}

.avatar--gradient {
  padding: 3px;
  background: linear-gradient(135deg, var(--color-info), var(--color-primary));
}

.avatar--gradient .avatar__img {
  background: var(--surface);
}

.avatar__dot {
  position: absolute;
  right: 1px;
  bottom: 1px;
  width: 11px;
  height: 11px;
  border-radius: var(--radius-full);
  background: var(--color-success);
  border: 2px solid var(--surface);
}
</style>
