<script setup>
/**
 * 会话记录（管理端）
 * 数据源：真实接口 GET /api/chat/history?sender_id=（后端按 sender_id 返回其历史消息，
 * 消息带 session_id，故按 session_id 归并为「一次会话」）。
 * 只读页面：不做任何后端写入。
 */
import { computed, onMounted, ref } from 'vue'
import PageHeader from '../components/layout/PageHeader.vue'
import AppCard from '../components/ui/AppCard.vue'
import AppField from '../components/ui/AppField.vue'
import AppInput from '../components/ui/AppInput.vue'
import AppButton from '../components/ui/AppButton.vue'
import AppBadge from '../components/ui/AppBadge.vue'
import Avatar from '../components/ui/Avatar.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import InlineAlert from '../components/ui/InlineAlert.vue'
import Skeleton from '../components/ui/Skeleton.vue'
import DetailDrawer from '../components/ui/DetailDrawer.vue'
import Icon from '../components/ui/Icon.vue'
import { useToast } from '../composables/useToast'
import { getStatusVariant } from '../utils/status'
import { getObjectTitle, getObjectSummary } from '../utils/format'
import { navigate } from '../router/useRoute'
import { customerService, userProfile, DEFAULT_SENDER_ID } from '../config/service'
import { withPrefix } from '../config/api-base'

const toast = useToast()

const senderId = ref(DEFAULT_SENDER_ID)
const messages = ref([])
const loading = ref(false)
const errorText = ref('')

const activeSessionId = ref('')
const drawerOpen = ref(false)

/** 按 session_id 归并成会话列表 */
const sessions = computed(() => {
  const map = new Map()
  for (const message of messages.value) {
    const key = message.session_id || 'default'
    if (!map.has(key)) {
      map.set(key, { id: key, messages: [], userCount: 0, botCount: 0 })
    }
    const session = map.get(key)
    session.messages.push(message)
    if (message.role === 'user') session.userCount += 1
    else session.botCount += 1
  }
  return Array.from(map.values()).map((session, index) => ({
    ...session,
    index: index + 1,
    preview:
      session.messages.find((m) => m.role === 'user' && m.text)?.text ||
      session.messages.find((m) => m.text)?.text ||
      '（对象消息）',
  }))
})

const activeSession = computed(
  () => sessions.value.find((session) => session.id === activeSessionId.value) || null,
)

async function load() {
  const id = senderId.value.trim()
  if (!id) {
    errorText.value = '请先填写 sender_id。'
    messages.value = []
    return
  }
  loading.value = true
  errorText.value = ''
  try {
    const response = await fetch(withPrefix(`/api/chat/history?sender_id=${encodeURIComponent(id)}`))
    const payload = await response.json()
    if (!response.ok) {
      throw new Error(payload?.detail || '加载会话记录失败。')
    }
    messages.value = Array.isArray(payload.messages) ? payload.messages : []
    toast.success(`已加载 ${messages.value.length} 条历史消息`)
  } catch (error) {
    errorText.value = error?.message || '加载会话记录失败。'
    messages.value = []
  } finally {
    loading.value = false
  }
}

function openSession(session) {
  activeSessionId.value = session.id
  drawerOpen.value = true
}

function closeDrawer() {
  drawerOpen.value = false
}

/** 把接口原始对象（{type,id,title,attributes}）包装成 utils 期望的 {objectType,payload} */
function toObjectMessage(raw) {
  const payload = raw ?? {}
  return { objectType: payload.type, payload }
}

function objectBadgeVariant(raw) {
  const payload = raw ?? {}
  if (payload.type === 'order') {
    return getStatusVariant(payload.attributes?.status ?? payload.status)
  }
  return 'info'
}

onMounted(load)
</script>

<template>
  <div class="admin-view">
    <div class="admin-view__inner">
      <PageHeader
        title="会话记录"
        subtitle="按 sender_id 查询历史会话，点击会话查看完整对话内容。"
        :breadcrumb="[{ label: '管理端' }, { label: '会话记录' }]"
        @navigate="navigate"
      >
        <template #actions>
          <AppButton :loading="loading" @click="load">
            <template #icon><Icon name="refresh" :size="16" /></template>
            刷新
          </AppButton>
        </template>
      </PageHeader>

      <AppCard class="toolbar">
        <div class="toolbar__row">
          <AppField label="sender_id（用户身份）" for-id="sessions-sender" hint="对应客服工作台右上角的用户身份">
            <AppInput
              id="sessions-sender"
              v-model="senderId"
              placeholder="例如 u1001"
              @enter="load"
            />
          </AppField>
          <AppButton variant="primary" :loading="loading" @click="load">查询</AppButton>
        </div>
      </AppCard>

      <InlineAlert
        v-if="errorText"
        class="stack-gap"
        variant="danger"
        :message="errorText"
        retryable
        @retry="load"
      />

      <div v-if="loading" class="stack-gap">
        <Skeleton variant="card" :rows="3" />
      </div>

      <EmptyState
        v-else-if="!sessions.length"
        class="stack-gap"
        icon="inbox"
        title="暂无会话记录"
        description="该 sender_id 下没有历史消息。可先在「工作台」与其对话，再回到此处查看。"
      >
        <template #action>
          <AppButton @click="navigate('/')">前往工作台</AppButton>
        </template>
      </EmptyState>

      <ul v-else class="session-list">
        <li v-for="session in sessions" :key="session.id">
          <AppCard as="article" hoverable class="session-card">
            <button type="button" class="session-card__btn" @click="openSession(session)">
              <span class="session-card__head">
                <span class="session-card__title">会话 {{ session.index }}</span>
                <AppBadge variant="primary" size="sm">{{ session.messages.length }} 条</AppBadge>
              </span>
              <span class="session-card__preview">{{ session.preview }}</span>
              <span class="session-card__meta">
                <span>用户 {{ session.userCount }}</span>
                <span aria-hidden="true">·</span>
                <span>客服 {{ session.botCount }}</span>
                <span class="session-card__id">session_id：{{ session.id }}</span>
              </span>
            </button>
          </AppCard>
        </li>
      </ul>
    </div>

    <DetailDrawer
      :open="drawerOpen"
      :title="activeSession ? `会话 ${activeSession.index}` : '会话详情'"
      :width="520"
      @close="closeDrawer"
    >
      <ul v-if="activeSession" class="transcript">
        <li
          v-for="(message, index) in activeSession.messages"
          :key="index"
          class="transcript__item"
          :class="`transcript__item--${message.role === 'user' ? 'user' : 'bot'}`"
        >
          <Avatar
            :src="message.role === 'user' ? userProfile.avatar : customerService.avatar"
            :alt="message.role === 'user' ? `${userProfile.label}头像` : `${customerService.name} 头像`"
            :size="30"
          />
          <div class="transcript__body">
            <p v-if="message.text" class="transcript__text">{{ message.text }}</p>
            <div v-else-if="message.object" class="transcript__object">
              <span class="transcript__object-title">
                {{ getObjectTitle(toObjectMessage(message.object)) }}
              </span>
              <span class="transcript__object-sub">
                {{ getObjectSummary(toObjectMessage(message.object)) }}
              </span>
              <AppBadge :variant="objectBadgeVariant(message.object)" size="sm">
                {{ message.object.type === 'order' ? '订单' : '商品' }}
              </AppBadge>
            </div>
          </div>
        </li>
      </ul>

      <EmptyState v-else icon="chat" title="未选择会话" description="从左侧列表中选择一个会话。" />
    </DetailDrawer>
  </div>
</template>

<style scoped>
.admin-view {
  padding: var(--space-6);
}
.admin-view__inner {
  width: min(var(--content-max), 100%);
  margin: 0 auto;
}

.stack-gap {
  margin-top: var(--space-4);
}

.toolbar {
  margin-bottom: var(--space-4);
}
.toolbar__row {
  display: flex;
  align-items: flex-end;
  gap: var(--space-4);
}
.toolbar__row :deep(.field) {
  flex: 1;
  min-width: 0;
}

.session-list {
  list-style: none;
  margin: var(--space-4) 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.session-card {
  width: 100%;
}

.session-card__btn {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  width: 100%;
  text-align: left;
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 0;
  color: inherit;
}

.session-card__head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.session-card__title {
  font-size: var(--text-md);
  font-weight: var(--weight-semibold);
}

.session-card__preview {
  font-size: var(--text-base);
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

.session-card__meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.session-card__id {
  margin-left: auto;
  font-family: var(--font-mono);
}

.transcript {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.transcript__item {
  display: flex;
  gap: var(--space-3);
  align-items: flex-start;
}

.transcript__item--user {
  flex-direction: row-reverse;
}

.transcript__body {
  min-width: 0;
  max-width: 84%;
}

.transcript__item--user .transcript__body {
  text-align: right;
}

.transcript__text {
  display: inline-block;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  background: var(--surface-hover);
  font-size: var(--text-base);
  line-height: var(--leading-relaxed);
  word-break: break-word;
}

.transcript__item--user .transcript__text {
  background: var(--color-primary-soft);
  color: var(--color-text-primary);
}

.transcript__object {
  display: inline-flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-1);
  padding: var(--space-3);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface-raised);
  text-align: left;
}

.transcript__object-title {
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
}

.transcript__object-sub {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

@media (max-width: 767px) {
  .admin-view {
    padding: var(--space-4);
  }
  .toolbar__row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
