<script setup>
import AppButton from '../ui/AppButton.vue'
import InlineAlert from '../ui/InlineAlert.vue'
import Icon from '../ui/Icon.vue'
import { useAvatar } from '../../composables/useAvatar'

/**
 * 数字人面板（魔珐星云）。
 * 生命周期与 WS 连接全部由 useAvatar 单例负责，本组件只负责呈现与触发。
 *
 * ⚠️ #digital-human-sdk 容器必须始终存在于 DOM 且具备明确宽高（SDK 的硬要求），
 *    因此这里用遮罩层表达状态，而不是 v-if 掉容器。
 */

const {
  humanReady,
  humanConnecting,
  humanProgress,
  humanError,
  buttonText,
  statusText,
  statusClass,
  wsStatusText,
  wsState,
  toggle,
} = useAvatar()
</script>

<template>
  <aside class="avatar-panel">
    <header class="avatar-panel__header">
      <h2 class="avatar-panel__title">
        <Icon name="user" :size="16" />
        <span>数字人</span>
      </h2>
      <span class="avatar-panel__status" :class="statusClass">{{ statusText }}</span>
    </header>

    <div class="avatar-panel__stage">
      <div id="digital-human-sdk" class="avatar-panel__canvas"></div>

      <div v-if="!humanReady" class="avatar-panel__mask">
        <template v-if="humanConnecting">
          <span class="avatar-panel__spinner" aria-hidden="true"></span>
          <span>正在加载数字人 {{ humanProgress }}%</span>
        </template>
        <template v-else>
          <span class="avatar-panel__mask-icon" aria-hidden="true">
            <Icon name="plug" :size="24" />
          </span>
          <span>数字人未连接</span>
          <span class="avatar-panel__hint">点击下方按钮连接</span>
        </template>
      </div>
    </div>

    <div
      v-if="humanConnecting"
      class="avatar-panel__progress"
      role="progressbar"
      :aria-valuenow="humanProgress"
      aria-valuemin="0"
      aria-valuemax="100"
      aria-label="数字人资源下载进度"
    >
      <div class="avatar-panel__progress-bar" :style="{ width: `${humanProgress}%` }"></div>
    </div>

    <AppButton
      variant="primary"
      block
      :loading="humanConnecting"
      :disabled="humanConnecting"
      :title="humanReady ? '断开并释放数字人房间' : '连接数字人（需下载 3D 资源）'"
      @click="toggle"
    >
      <template #icon>
        <Icon :name="humanReady ? 'close' : 'plug'" :size="16" />
      </template>
      {{ buttonText }}
    </AppButton>

    <p v-if="humanReady" class="avatar-panel__ws">
      <span class="avatar-panel__dot" :class="{ 'is-open': wsState.status === 'open' }" aria-hidden="true"></span>
      {{ wsStatusText }}
    </p>

    <InlineAlert v-if="humanError" variant="danger" :message="humanError" />
    <p v-else-if="!humanReady" class="avatar-panel__tip">连接后，客服回复会自动由数字人朗读</p>
  </aside>
</template>

<style scoped>
.avatar-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-5) var(--space-4);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.avatar-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  flex-shrink: 0;
}

.avatar-panel__title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-md);
  font-weight: var(--weight-semibold);
  color: var(--color-text-primary);
}

.avatar-panel__status {
  padding: 3px 10px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  color: var(--color-text-muted);
  white-space: nowrap;
}

.avatar-panel__status.is-ready {
  color: var(--color-success);
  border-color: var(--color-success);
  background: var(--color-success-soft);
}

.avatar-panel__status.is-loading {
  color: var(--color-warning);
  border-color: var(--color-warning);
  background: var(--color-warning-soft);
}

/* 官方推荐 9:16 竖屏（最小 270×480），按比例约束避免成像被拉长 */
.avatar-panel__stage {
  position: relative;
  width: 100%;
  flex: 0 1 auto;
  min-height: 0;
  max-height: 100%;
  aspect-ratio: 9 / 16;
  margin: auto 0;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  overflow: hidden;
  background:
    radial-gradient(120% 80% at 50% 0%, var(--color-primary-soft-bg), transparent 62%),
    linear-gradient(180deg, var(--surface) 0%, var(--surface-raised) 100%);
}

/* SDK 要求渲染容器必须有明确宽高 */
.avatar-panel__canvas {
  width: 100%;
  height: 100%;
}

.avatar-panel__mask {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-4);
  text-align: center;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  background: linear-gradient(180deg, transparent 0%, var(--surface-raised) 100%);
}

.avatar-panel__mask-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  margin-bottom: var(--space-1);
  border: 1px solid var(--border);
  border-radius: var(--radius-full);
  background: var(--surface);
  color: var(--color-primary);
  box-shadow: var(--shadow-sm);
}

.avatar-panel__spinner {
  width: 22px;
  height: 22px;
  border: 2px solid var(--border);
  border-top-color: var(--color-primary);
  border-radius: var(--radius-full);
  animation: avatarSpin 0.8s linear infinite;
}

@keyframes avatarSpin {
  to { transform: rotate(360deg); }
}

@media (prefers-reduced-motion: reduce) {
  .avatar-panel__spinner { animation-duration: 1.6s; }
}

.avatar-panel__hint {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.avatar-panel__progress {
  height: 4px;
  border-radius: var(--radius-full);
  background: var(--surface-hover);
  overflow: hidden;
  flex-shrink: 0;
}

.avatar-panel__progress-bar {
  height: 100%;
  border-radius: var(--radius-full);
  background: var(--color-primary);
  transition: width var(--duration-base) var(--ease-in-out);
}

.avatar-panel__ws {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.avatar-panel__dot {
  width: 7px;
  height: 7px;
  border-radius: var(--radius-full);
  background: var(--ink-400);
  flex-shrink: 0;
}

.avatar-panel__dot.is-open {
  background: var(--color-success);
}

.avatar-panel__tip {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  text-align: center;
}

/* 单列堆叠时，面板不再受视口高度约束，改成给舞台封顶（保持 9:16） */
@media (max-width: 1179px) {
  .avatar-panel {
    padding: var(--space-4);
  }

  .avatar-panel__stage {
    max-width: 260px;
    margin-inline: auto;
  }
}
</style>
