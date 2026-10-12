<script setup>
defineProps({
  /** line | avatar | card | list-item */
  variant: { type: String, default: 'line' },
  rows: { type: Number, default: 3 },
})
</script>

<template>
  <div class="skeleton" :class="`skeleton--${variant}`" aria-hidden="true">
    <template v-if="variant === 'list-item'">
      <div v-for="i in rows" :key="i" class="skeleton__item">
        <span class="skeleton__block skeleton__thumb"></span>
        <span class="skeleton__lines">
          <span class="skeleton__line skeleton__line--80"></span>
          <span class="skeleton__line skeleton__line--50"></span>
        </span>
      </div>
    </template>
    <template v-else-if="variant === 'card'">
      <div v-for="i in rows" :key="i" class="skeleton__card">
        <span class="skeleton__line skeleton__line--40"></span>
        <span class="skeleton__line skeleton__line--90"></span>
        <span class="skeleton__line skeleton__line--70"></span>
      </div>
    </template>
    <template v-else-if="variant === 'avatar'">
      <span class="skeleton__avatar"></span>
    </template>
    <template v-else>
      <span
        v-for="i in rows"
        :key="i"
        class="skeleton__line"
        :style="{ width: i === rows ? '60%' : '100%' }"
      ></span>
    </template>
  </div>
</template>

<style scoped>
.skeleton {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.skeleton__card,
.skeleton__item {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  background: var(--surface);
}

.skeleton__card {
  flex-direction: column;
}

.skeleton__lines {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  flex: 1;
}

.skeleton__block {
  background: linear-gradient(90deg, var(--ink-100) 25%, var(--ink-200) 37%, var(--ink-100) 63%);
  background-size: 400% 100%;
  animation: skeletonShimmer 1.4s ease infinite;
  border-radius: var(--radius-sm);
}

.skeleton__line {
  height: 12px;
  width: 100%;
  display: block;
  border-radius: var(--radius-xs);
  background: linear-gradient(90deg, var(--ink-100) 25%, var(--ink-200) 37%, var(--ink-100) 63%);
  background-size: 400% 100%;
  animation: skeletonShimmer 1.4s ease infinite;
}

.skeleton__line--40 { width: 40%; }
.skeleton__line--50 { width: 50%; }
.skeleton__line--70 { width: 70%; }
.skeleton__line--80 { width: 80%; }
.skeleton__line--90 { width: 90%; }

.skeleton__thumb {
  width: 100%;
  height: 64px;
  flex-shrink: 0;
}

.skeleton__item .skeleton__thumb {
  width: 72px;
  height: 56px;
}

.skeleton__avatar {
  width: 42px;
  height: 42px;
  border-radius: var(--radius-full);
  display: block;
  background: linear-gradient(90deg, var(--ink-100) 25%, var(--ink-200) 37%, var(--ink-100) 63%);
  background-size: 400% 100%;
  animation: skeletonShimmer 1.4s ease infinite;
}

@keyframes skeletonShimmer {
  0% { background-position: 100% 50%; }
  100% { background-position: 0 50%; }
}

@media (prefers-reduced-motion: reduce) {
  .skeleton__line,
  .skeleton__block,
  .skeleton__avatar {
    animation: none;
  }
}
</style>
