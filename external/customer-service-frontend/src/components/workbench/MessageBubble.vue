<script setup>
import { computed } from 'vue'
import Avatar from '../ui/Avatar.vue'
import Icon from '../ui/Icon.vue'
import ObjectCard from './ObjectCard.vue'
import { dayKeyOf, formatClock } from '../../utils/format'

/**
 * 单条消息气泡（纯展示组件）。
 *
 * 与旧实现的区别：
 *  - 不再按 Turn 分块 —— 消息直接排在连续流里，只有「同一发送者的首条」显示头像与姓名时间
 *  - position 决定气泡圆角的折角方向，让同一发送者的连续消息看起来是「一组」而不是「一块块」
 *  - 播报 / 复制按钮由「每条常驻」改为 hover 或键盘聚焦时出现（触摸设备常显）
 */
const props = defineProps({
  message: { type: Object, required: true },
  /** single | head | middle | tail —— 同一发送者连续消息中的位置 */
  position: { type: String, default: 'single' },
  timeLabel: { type: String, default: '' },
  speaker: { type: String, default: '' },
  speakerRole: { type: String, default: '' },
  avatarSrc: { type: String, default: '' },
  avatarAlt: { type: String, default: '' },
  /** 本条是否正在语音播报 */
  playing: { type: Boolean, default: false },
  /** 本条是否已复制 */
  copied: { type: Boolean, default: false },
  /** 发送中：禁用建议词 */
  disabled: { type: Boolean, default: false },
  /** ?debug=1：显示分组位置与时间来源 */
  debug: { type: Boolean, default: false },
})

defineEmits(['tts', 'copy', 'suggestion'])

const isOutgoing = computed(() => props.message.role === 'user')
const showsHead = computed(() => props.position === 'head' || props.position === 'single')
const isObject = computed(() => props.message.type === 'object')
const suggestions = computed(() => props.message.suggestions ?? [])
const canSpeak = computed(() => !isOutgoing.value && !isObject.value && Boolean(props.message.text))

/** 调试浮层：验证「本地时间轴 / 无时间」与分组位置是否符合预期 */
const debugLabel = computed(() => {
  if (!props.debug) return ''
  const at = props.message.at
  const source = Number.isFinite(at) ? `${dayKeyOf(at)} ${formatClock(at)}` : 'no-time'
  return `${props.position} · ${source}`
})
</script>

<template>
  <div
    class="row"
    :class="[
      isOutgoing ? 'row--out' : 'row--in',
      `row--${position}`,
      { 'row--grouped': position === 'middle' || position === 'tail' },
    ]"
  >
    <div class="row__gutter">
      <Avatar
        v-if="showsHead"
        :src="avatarSrc"
        :alt="avatarAlt"
        :size="34"
        :ring="isOutgoing ? 'plain' : 'success'"
        :status-dot="!isOutgoing"
      />
    </div>

    <div class="row__body">
      <p v-if="showsHead" class="row__meta">
        <span class="row__speaker">{{ speaker }}</span>
        <span class="row__role">{{ speakerRole }}</span>
        <time v-if="timeLabel" class="row__time">{{ timeLabel }}</time>
      </p>

      <p v-if="debugLabel" class="row__debug">{{ debugLabel }}</p>

      <div class="bubble" :class="{ 'bubble--object': isObject }">
        <ObjectCard v-if="isObject" :message="message" />
        <p v-else class="bubble__text">{{ message.text }}</p>

        <div v-if="canSpeak" class="bubble__actions">
          <button
            type="button"
            class="bubble__action"
            :class="{ 'is-active': playing }"
            :title="playing ? '正在播报，点击停止' : '语音播报'"
            :aria-label="playing ? '停止语音播报' : '语音播报本条回复'"
            :aria-pressed="playing ? 'true' : 'false'"
            @click="$emit('tts', message)"
          >
            <span v-if="playing" class="bars" aria-hidden="true">
              <span></span><span></span><span></span>
            </span>
            <Icon v-else name="speaker" :size="15" />
          </button>

          <button
            type="button"
            class="bubble__action"
            :class="{ 'is-active': copied }"
            :title="copied ? '已复制' : '复制文字'"
            :aria-label="copied ? '已复制本条回复' : '复制本条回复文字'"
            @click="$emit('copy', message)"
          >
            <Icon :name="copied ? 'check' : 'copy'" :size="15" />
          </button>
        </div>
      </div>

      <div v-if="suggestions.length" class="chips">
        <button
          v-for="suggestion in suggestions"
          :key="suggestion"
          type="button"
          class="chip"
          :disabled="disabled"
          @click="$emit('suggestion', suggestion)"
        >
          {{ suggestion }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.row {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
}

/* 组间留白 16px，同组内 4px —— 靠间距区分「一组话」而不是靠卡片外壳 */
.row + .row {
  margin-top: var(--space-4);
}

.row + .row--grouped {
  margin-top: var(--bubble-group-gap);
}

.row--out {
  flex-direction: row-reverse;
}

.row__gutter {
  flex-shrink: 0;
  width: 34px;
}

.row__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
  max-width: min(560px, 82%);
}

.row--out .row__body {
  align-items: flex-end;
}

.row__meta {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.row__speaker {
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--color-text-secondary);
}

.row__role {
  color: var(--color-text-muted);
}

.row__time {
  font-variant-numeric: tabular-nums;
}

.row__debug {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-warning);
  background: var(--color-warning-soft);
  border-radius: var(--radius-xs);
  padding: 0 4px;
}

.bubble {
  position: relative;
  padding: 11px 14px;
  border: 1px solid var(--bubble-in-border);
  background: var(--bubble-in-bg);
  box-shadow: var(--bubble-shadow);
  font-size: var(--text-md);
  line-height: var(--leading-relaxed);
  color: var(--color-text-primary);
  /* 默认（single）：靠发送者一侧上下折角 */
  border-radius: var(--bubble-r);
}

/* ── 折角：紧贴头像一侧收紧上角，同组内再收紧下角 → 一组的观感 ───────── */
.row--in .bubble {
  border-top-left-radius: var(--bubble-r-tail);
}
.row--in.row--head .bubble,
.row--in.row--middle .bubble {
  border-bottom-left-radius: var(--bubble-r-tail);
}

.row--out .bubble {
  background: var(--color-primary-soft);
  border-color: transparent;
  box-shadow: var(--bubble-shadow);
  border-top-right-radius: var(--bubble-r-tail);
}
.row--out.row--head .bubble,
.row--out.row--middle .bubble {
  border-bottom-right-radius: var(--bubble-r-tail);
}

/* 对象消息自带卡片外壳，气泡层退掉 */
.bubble--object {
  padding: 0;
  border: none;
  background: transparent;
  box-shadow: none;
}

.bubble__text {
  white-space: pre-wrap;
  word-break: break-word;
}

.bubble__actions {
  display: flex;
  gap: var(--space-1);
  margin-top: var(--space-1);
  opacity: 0;
  transition: opacity var(--duration-fast) var(--ease-in-out);
}

.bubble:hover .bubble__actions,
.bubble:focus-within .bubble__actions {
  opacity: 1;
}

@media (hover: none) {
  .bubble__actions {
    opacity: 1;
  }
}

.bubble__action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  transition:
    background var(--duration-fast) var(--ease-in-out),
    color var(--duration-fast) var(--ease-in-out);
}

.bubble__action:hover {
  background: var(--surface-hover);
  color: var(--color-primary);
}

.bubble__action.is-active {
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

/* 播报中的三格律动 */
.bars {
  display: inline-flex;
  align-items: flex-end;
  gap: 2px;
  height: 14px;
}

.bars span {
  width: 3px;
  border-radius: var(--radius-full);
  background: currentColor;
  animation: bars 0.9s ease-in-out infinite;
}

.bars span:nth-child(1) { height: 6px; animation-delay: 0s; }
.bars span:nth-child(2) { height: 12px; animation-delay: 0.15s; }
.bars span:nth-child(3) { height: 8px; animation-delay: 0.3s; }

@keyframes bars {
  0%, 100% { transform: scaleY(0.5); }
  50% { transform: scaleY(1); }
}

@media (prefers-reduced-motion: reduce) {
  .bars span { animation: none; }
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-1);
}

.chip {
  padding: 6px 14px;
  border: 1px solid var(--color-primary-soft);
  border-radius: var(--radius-full);
  background: var(--color-primary-soft-bg);
  color: var(--color-primary);
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  cursor: pointer;
  transition:
    background var(--duration-fast) var(--ease-in-out),
    border-color var(--duration-fast) var(--ease-in-out);
}

.chip:hover:not(:disabled) {
  background: var(--color-primary-soft);
  border-color: var(--color-primary);
}

.chip:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>
