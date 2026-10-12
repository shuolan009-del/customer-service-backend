<script setup>
import { computed, onMounted, ref } from 'vue'
import Avatar from '../ui/Avatar.vue'
import Icon from '../ui/Icon.vue'
import InlineAlert from '../ui/InlineAlert.vue'
import Skeleton from '../ui/Skeleton.vue'
import MessageBubble from './MessageBubble.vue'
import { useChat } from '../../composables/useChat'
import { useAvatar } from '../../composables/useAvatar'
import { useClipboard } from '../../composables/useClipboard'
import { customerService, userProfile, QUICK_QUESTIONS } from '../../config/service'

/**
 * 消息流：按自然日分组的连续对话。
 * 取代原先的「Turn 卡片」——不再把一段对话切成一格一格，而是排成一条时间轴。
 */
defineProps({
  /** ?debug=1 时在每条消息上标注分组位置与时间来源 */
  debug: { type: Boolean, default: false },
})

const {
  messageGroups,
  isEmpty,
  isSending,
  errorMessage,
  historyLoading,
  scrolledToBottom,
  unreadCount,
  canRetry,
  setContainer,
  scrollToBottom,
  onScroll,
  retryLast,
  sendQuickText,
  sendSuggestion,
} = useChat()

const { ttsState, playTts } = useAvatar()
const { copy, isCopied } = useClipboard()

const scroller = ref(null)

onMounted(() => setContainer(scroller.value))

const jumpLabel = computed(() =>
  unreadCount.value > 0 ? `${unreadCount.value} 条新消息` : '回到最新',
)

function handleTts(message) {
  playTts(message)
}

function handleCopy(message) {
  copy(message.text, message.id)
}
</script>

<template>
  <div class="stream-wrap">
    <section
      ref="scroller"
      class="stream"
      role="log"
      aria-live="polite"
      aria-label="对话消息"
      @scroll.passive="onScroll"
    >
      <div class="stream__inner">
        <Skeleton v-if="historyLoading && isEmpty" variant="card" :rows="3" />

        <div v-else-if="isEmpty" class="welcome">
          <div class="welcome__avatar">
            <Avatar :src="customerService.avatar" :alt="`${customerService.name} 头像`" :size="64" ring="success" status-dot />
          </div>
          <h2 class="welcome__title">Hi，我是 {{ customerService.name }}</h2>
          <p class="welcome__subtitle">你的专属电商客服，随时为你服务</p>

          <div class="welcome__chips">
            <button
              v-for="question in QUICK_QUESTIONS"
              :key="question"
              type="button"
              class="welcome__chip"
              :disabled="isSending"
              @click="sendQuickText(question)"
            >
              {{ question }}
            </button>
          </div>

          <p class="welcome__features">
            <span><Icon name="chat" :size="14" /> 文字对话</span>
            <span><Icon name="speaker" :size="14" /> 语音播报</span>
            <span><Icon name="package" :size="14" /> 订单查询</span>
            <span><Icon name="bag" :size="14" /> 商品咨询</span>
          </p>
        </div>

        <template v-else>
          <section v-for="group in messageGroups" :key="group.key" class="day">
            <p class="day__label">
              <span>{{ group.label }}</span>
            </p>

            <MessageBubble
              v-for="(item, index) in group.items"
              :key="item.message.id || index"
              :message="item.message"
              :position="item.position"
              :time-label="item.timeLabel"
              :speaker="item.message.role === 'user' ? userProfile.name : customerService.name"
              :speaker-role="item.message.role === 'user' ? userProfile.label : customerService.title"
              :avatar-src="item.message.role === 'user' ? userProfile.avatar : customerService.avatar"
              :avatar-alt="item.message.role === 'user' ? `${userProfile.label}头像` : `${customerService.name} 头像`"
              :playing="ttsState[item.message.id] === 'playing'"
              :copied="isCopied(item.message.id)"
              :disabled="isSending"
              :debug="debug"
              @tts="handleTts"
              @copy="handleCopy"
              @suggestion="sendSuggestion"
            />
          </section>

          <div v-if="isSending" class="typing" role="status" aria-live="polite">
            <Avatar :src="customerService.avatar" alt="" :size="34" ring="success" />
            <div class="typing__bubble">
              <span class="typing__dots" aria-hidden="true">
                <span></span><span></span><span></span>
              </span>
              <span class="typing__label">{{ customerService.name }} 正在输入…</span>
            </div>
          </div>
        </template>
      </div>
    </section>

    <button
      v-if="!scrolledToBottom"
      type="button"
      class="jump"
      @click="scrollToBottom(true)"
    >
      <Icon name="arrow-down" :size="14" />
      <span>{{ jumpLabel }}</span>
    </button>

    <InlineAlert
      v-if="errorMessage"
      class="stream-wrap__alert"
      variant="danger"
      :message="errorMessage"
      :retryable="canRetry"
      @retry="retryLast"
    />
  </div>
</template>

<style scoped>
.stream-wrap {
  position: relative;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.stream {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  scroll-behavior: smooth;
}

.stream__inner {
  display: flex;
  flex-direction: column;
  padding: var(--space-4) var(--space-5) var(--space-6);
}

/* ── 日期分隔（吸顶）─────────────────────────────────────────────── */
.day {
  display: flex;
  flex-direction: column;
}

.day + .day {
  margin-top: var(--space-5);
}

.day__label {
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  justify-content: center;
  margin-bottom: var(--space-4);
  padding: var(--space-1) 0;
  /* 吸顶时用渐变把下方滚过的消息压暗，避免内容从胶囊两侧透出来 */
  background: linear-gradient(
    180deg,
    var(--surface) 0%,
    var(--surface) 78%,
    transparent 100%
  );
}

.day__label span {
  padding: 3px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-full);
  background: var(--surface-hover);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  color: var(--color-text-muted);
}

/* ── 欢迎态 ──────────────────────────────────────────────────────── */
.welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  margin: auto;
  padding: var(--space-10) var(--space-4);
  text-align: center;
}

.welcome__avatar {
  margin-bottom: var(--space-2);
}

.welcome__title {
  font-size: var(--text-lg);
  font-weight: var(--weight-bold);
  color: var(--color-text-primary);
}

.welcome__subtitle {
  font-size: var(--text-base);
  color: var(--color-text-secondary);
}

.welcome__chips {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--space-2);
  margin-top: var(--space-4);
}

.welcome__chip {
  padding: 8px 18px;
  border: 1px solid var(--border);
  border-radius: var(--radius-full);
  background: var(--surface);
  color: var(--color-text-primary);
  font-size: var(--text-base);
  font-weight: var(--weight-medium);
  cursor: pointer;
  transition:
    background var(--duration-fast) var(--ease-in-out),
    border-color var(--duration-fast) var(--ease-in-out),
    color var(--duration-fast) var(--ease-in-out);
}

.welcome__chip:hover:not(:disabled) {
  background: var(--color-primary-soft);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.welcome__chip:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.welcome__features {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--space-4);
  margin-top: var(--space-5);
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

.welcome__features span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

/* ── 输入中 ──────────────────────────────────────────────────────── */
.typing {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  margin-top: var(--space-4);
}

.typing__bubble {
  display: inline-flex;
  align-items: center;
  gap: var(--space-3);
  padding: 10px var(--space-3);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  border-top-left-radius: var(--radius-xs);
  background: var(--surface);
}

.typing__dots {
  display: inline-flex;
  gap: 4px;
}

.typing__dots span {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-full);
  background: var(--ink-400);
  animation: typingBlink 1.2s ease-in-out infinite;
}

.typing__dots span:nth-child(2) { animation-delay: 0.18s; }
.typing__dots span:nth-child(3) { animation-delay: 0.36s; }

@keyframes typingBlink {
  0%, 100% { opacity: 0.3; transform: translateY(0); }
  50% { opacity: 1; transform: translateY(-2px); }
}

@media (prefers-reduced-motion: reduce) {
  .typing__dots span { animation: none; opacity: 0.7; }
}

.typing__label {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

/* ── 回到最新浮标 ─────────────────────────────────────────────────── */
.jump {
  position: absolute;
  right: var(--space-5);
  bottom: var(--space-4);
  z-index: 3;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-full);
  background: var(--surface);
  box-shadow: var(--shadow-md);
  color: var(--color-primary);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  cursor: pointer;
}

.jump:hover {
  background: var(--color-primary-soft-bg);
  border-color: var(--color-primary);
}

.stream-wrap__alert {
  margin: var(--space-2) var(--space-5) 0;
}
</style>
