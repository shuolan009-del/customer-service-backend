<script setup>
/**
 * 系统设置（管理端）
 * 真实只读数据：GET /api/avatar/status、GET /api/avatar/consume-record
 * 本地偏好：localStorage（键 cs-prefs），不涉及后端写入。
 */
import { onMounted, reactive, ref } from 'vue'
import PageHeader from '../components/layout/PageHeader.vue'
import AppCard from '../components/ui/AppCard.vue'
import AppField from '../components/ui/AppField.vue'
import AppInput from '../components/ui/AppInput.vue'
import AppButton from '../components/ui/AppButton.vue'
import AppBadge from '../components/ui/AppBadge.vue'
import InlineAlert from '../components/ui/InlineAlert.vue'
import Skeleton from '../components/ui/Skeleton.vue'
import StatTable from '../components/ui/StatTable.vue'
import Icon from '../components/ui/Icon.vue'
import { useToast } from '../composables/useToast'
import { useConfirm } from '../composables/useConfirm'
import { navigate } from '../router/useRoute'
import { DEFAULT_SENDER_ID } from '../config/service'
import { readPrefs, writePrefs } from '../utils/prefs'

const toast = useToast()
const { confirm } = useConfirm()

const status = ref(null)
const statusLoading = ref(false)
const statusError = ref('')

const consume = ref(null)
const consumeLoading = ref(false)
const consumeError = ref('')

const prefs = reactive({
  defaultSenderId: DEFAULT_SENDER_ID,
  autoConnectAvatar: false,
  reduceMotion: false,
})

function savePrefs() {
  try {
    writePrefs({ ...prefs })
    toast.success('偏好设置已保存到本机')
  } catch {
    toast.error('保存失败：浏览器本地存储不可用')
  }
}

async function resetPrefs() {
  const ok = await confirm({
    title: '重置本地偏好？',
    description: '将恢复为默认值（默认 sender_id、不自动连接数字人、跟随系统动效）。此操作不涉及服务端数据。',
    confirmText: '重置',
    danger: true,
  })
  if (!ok) return
  prefs.defaultSenderId = DEFAULT_SENDER_ID
  prefs.autoConnectAvatar = false
  prefs.reduceMotion = false
  savePrefs()
}

async function fetchJson(url) {
  const response = await fetch(url)
  let payload = null
  try {
    payload = await response.json()
  } catch {
    payload = null
  }
  if (!response.ok) {
    const detail = payload?.detail || payload?.message
    throw new Error(detail || `请求失败（HTTP ${response.status}）`)
  }
  return payload
}

async function loadStatus() {
  statusLoading.value = true
  statusError.value = ''
  try {
    status.value = await fetchJson('/api/avatar/status')
  } catch (error) {
    statusError.value = error?.message || '获取数字人状态失败。'
    status.value = null
  } finally {
    statusLoading.value = false
  }
}

async function loadConsume() {
  consumeLoading.value = true
  consumeError.value = ''
  try {
    consume.value = await fetchJson('/api/avatar/consume-record')
  } catch (error) {
    consumeError.value = error?.message || '获取积分消耗记录失败。'
    consume.value = null
  } finally {
    consumeLoading.value = false
  }
}

const recordColumns = [
  { key: 'created_at', label: '时间' },
  { key: 'avatar_id', label: '数字人' },
  { key: 'amount', label: '消耗', align: 'right' },
]

function recordRows() {
  const records = consume.value?.records
  if (!Array.isArray(records)) return []
  return records.map((item, index) => ({
    id: item.id ?? `r-${index}`,
    created_at: item.created_at ?? '—',
    avatar_id: item.avatar_id ?? '—',
    amount: item.amount ?? '—',
  }))
}

const usableVariant = (usable) => (usable ? 'success' : 'muted')

onMounted(() => {
  Object.assign(prefs, readPrefs())
  loadStatus()
  loadConsume()
})
</script>

<template>
  <div class="admin-view">
    <div class="admin-view__inner">
      <PageHeader
        title="系统设置"
        subtitle="数字人运行状态（只读）与本机偏好设置。"
        :breadcrumb="[{ label: '管理端' }, { label: '系统设置' }]"
        @navigate="navigate"
      >
        <template #actions>
          <AppButton :loading="statusLoading || consumeLoading" @click="loadStatus(); loadConsume()">
            <template #icon><Icon name="refresh" :size="16" /></template>
            刷新状态
          </AppButton>
        </template>
      </PageHeader>

      <div class="grid">
        <!-- 数字人状态 -->
        <AppCard>
          <template #header>
            <div class="card-head">
              <h2 class="card-head__title">数字人运行状态</h2>
              <AppBadge v-if="status" :variant="usableVariant(status.usable)">
                {{ status.usable ? '可用' : '未启用' }}
              </AppBadge>
            </div>
          </template>

          <Skeleton v-if="statusLoading" variant="line" :rows="4" />
          <InlineAlert
            v-else-if="statusError"
            variant="warning"
            :message="`${statusError}（若后端未启用数字人，此处返回 503 属预期行为。）`"
            retryable
            @retry="loadStatus"
          />
          <dl v-else-if="status" class="kv">
            <div class="kv__row">
              <dt>能力开关</dt>
              <dd>{{ status.enabled ? '已启用' : '未启用' }}</dd>
            </div>
            <div class="kv__row">
              <dt>凭据就绪</dt>
              <dd>{{ status.credentials_ready ? '是' : '否' }}</dd>
            </div>
            <div class="kv__row">
              <dt>App ID</dt>
              <dd class="kv__mono">{{ status.app_id_masked || '—' }}</dd>
            </div>
            <div class="kv__row">
              <dt>驱动模式</dt>
              <dd>{{ status.drive_mode || '—' }}</dd>
            </div>
            <div class="kv__row">
              <dt>默认形象</dt>
              <dd class="kv__mono">{{ status.default_avatar_id || '—' }}</dd>
            </div>
            <div class="kv__row">
              <dt>网关地址</dt>
              <dd class="kv__mono kv__ellipsis">{{ status.gateway_server || '—' }}</dd>
            </div>
          </dl>
        </AppCard>

        <!-- 偏好设置 -->
        <AppCard>
          <template #header>
            <div class="card-head">
              <h2 class="card-head__title">本机偏好</h2>
              <span class="card-head__hint">仅保存在本机浏览器</span>
            </div>
          </template>

          <div class="form">
            <AppField
              label="默认 sender_id"
              for-id="pref-sender"
              hint="打开工作台时预填的用户身份"
            >
              <AppInput id="pref-sender" v-model="prefs.defaultSenderId" placeholder="u1001" />
            </AppField>

            <label class="switch">
              <input v-model="prefs.autoConnectAvatar" type="checkbox" class="switch__input" />
              <span class="switch__track" aria-hidden="true"></span>
              <span class="switch__text">
                打开工作台时自动连接数字人
                <small>数字人未配置时不会生效</small>
              </span>
            </label>

            <label class="switch">
              <input v-model="prefs.reduceMotion" type="checkbox" class="switch__input" />
              <span class="switch__track" aria-hidden="true"></span>
              <span class="switch__text">
                减弱动效
                <small>关闭过渡与动画，等价于系统 prefers-reduced-motion</small>
              </span>
            </label>

            <div class="form__actions">
              <AppButton variant="primary" @click="savePrefs">保存偏好</AppButton>
              <AppButton @click="resetPrefs">重置</AppButton>
            </div>
          </div>
        </AppCard>

        <!-- 积分消耗 -->
        <AppCard class="grid__wide">
          <template #header>
            <div class="card-head">
              <h2 class="card-head__title">数字人积分消耗</h2>
              <AppBadge v-if="consume" variant="info" size="sm">
                共 {{ consume.count ?? 0 }} 条 / 合计 {{ consume.total_amount ?? 0 }}
              </AppBadge>
            </div>
          </template>

          <Skeleton v-if="consumeLoading" variant="line" :rows="3" />
          <InlineAlert
            v-else-if="consumeError"
            variant="warning"
            :message="consumeError"
            retryable
            @retry="loadConsume"
          />
          <StatTable v-else :columns="recordColumns" :rows="recordRows()" row-key="id" />
        </AppCard>
      </div>
    </div>
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

.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-4);
  align-items: start;
}

.grid__wide {
  grid-column: 1 / -1;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.card-head__title {
  font-size: var(--text-lg);
  font-weight: var(--weight-semibold);
}

.card-head__hint {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.kv {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.kv__row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-4);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--border-light);
}
.kv__row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.kv__row dt {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.kv__row dd {
  font-size: var(--text-base);
  color: var(--color-text-primary);
  text-align: right;
  min-width: 0;
}

.kv__mono {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
}

.kv__ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 60%;
}

.form {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.switch {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  cursor: pointer;
}

.switch__input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.switch__track {
  position: relative;
  flex-shrink: 0;
  width: 40px;
  height: 22px;
  margin-top: 2px;
  border-radius: var(--radius-full);
  background: var(--ink-300);
  transition: background var(--duration-fast) var(--ease-in-out);
}

.switch__track::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 18px;
  height: 18px;
  border-radius: var(--radius-full);
  background: #fff;
  transition: transform var(--duration-fast) var(--ease-standard);
}

.switch__input:checked + .switch__track {
  background: var(--color-primary);
}

.switch__input:checked + .switch__track::after {
  transform: translateX(18px);
}

.switch__input:focus-visible + .switch__track {
  box-shadow: var(--focus-ring);
}

.switch__text {
  font-size: var(--text-base);
  color: var(--color-text-primary);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.switch__text small {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.form__actions {
  display: flex;
  gap: var(--space-3);
}

@media (max-width: 1179px) {
  .grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 767px) {
  .admin-view {
    padding: var(--space-4);
  }
}
</style>
