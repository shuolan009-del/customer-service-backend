<script setup>
/**
 * 客服工作台（编排层）。
 *
 * 2509 行的单文件已拆分为 components/workbench/*：
 *   AvatarPanel / MessageStream / ObjectSidebar / Composer
 * 全部业务状态改由模块级单例 composable 提供（useChat / useAvatar / useSidebar），
 * 与「会话记录」「系统设置」共用同一份 sender_id 与数字人状态。
 *
 * 对话展示：按自然日分组的连续消息流（时间来源见 utils/timeline.js）。
 */
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import AppButton from '../components/ui/AppButton.vue'
import AppField from '../components/ui/AppField.vue'
import AppInput from '../components/ui/AppInput.vue'
import Avatar from '../components/ui/Avatar.vue'
import Icon from '../components/ui/Icon.vue'
import AvatarPanel from '../components/workbench/AvatarPanel.vue'
import Composer from '../components/workbench/Composer.vue'
import MessageStream from '../components/workbench/MessageStream.vue'
import ObjectSidebar from '../components/workbench/ObjectSidebar.vue'
import { useAvatar } from '../composables/useAvatar'
import { useChat } from '../composables/useChat'
import { useSidebar } from '../composables/useSidebar'
import { customerService, DEFAULT_SENDER_ID } from '../config/service'
import { readPrefs } from '../utils/prefs'

const { senderId, reset, fetchHistory } = useChat()
const { dispose, init: connectAvatar, humanReady, humanConnecting } = useAvatar()
const { load: loadObjects } = useSidebar()

/** 右侧业务对象栏收起态：默认收起（2026-10-16），点击轨道/按钮切换 */
const sidebarCollapsed = ref(true)

/** ?debug=1 → 消息流内显示分组位置与时间来源，便于核对「按天管理」是否生效 */
const debug = computed(
  () => new URLSearchParams(window.location.search).get('debug') === '1',
)

let prefsApplied = false
let wantsAutoConnect = false

/** 读取「系统设置」写入的本地偏好（此前全仓无人读取，属死设置） */
function applyPrefs() {
  if (prefsApplied) return
  prefsApplied = true

  const prefs = readPrefs()
  const preferred = String(prefs.defaultSenderId ?? '').trim()
  if (preferred && senderId.value === DEFAULT_SENDER_ID) senderId.value = preferred
  wantsAutoConnect = Boolean(prefs.autoConnectAvatar)
}

applyPrefs()

// 切换 sender_id → 重置会话 + 重拉历史 + 重拉右侧对象（immediate 覆盖首次加载）
watch(
  () => senderId.value.trim(),
  async (value, previous) => {
    if (value === previous) return
    reset()
    if (!value) return
    await Promise.all([loadObjects(value), fetchHistory()])
  },
  { immediate: true },
)

function handleBeforeUnload() {
  // 页面关闭 / 刷新前主动释放房间连接，避免触发并发限制（错误码 10005）
  dispose()
}

onMounted(() => {
  window.addEventListener('beforeunload', handleBeforeUnload)
  // 数字人容器此时已挂载，自动连接放这里才不会拿不到 #digital-human-sdk
  if (wantsAutoConnect && !humanReady.value && !humanConnecting.value) connectAvatar()
})

onUnmounted(() => {
  window.removeEventListener('beforeunload', handleBeforeUnload)
  // 容器随本视图卸载，SDK 实例必须一并释放，否则重新进入会渲染到已脱离文档的节点
  dispose()
})
</script>

<template>
  <div class="workbench">
    <div class="workbench__grid" :class="{ 'workbench__grid--sbmin': sidebarCollapsed }">
      <AvatarPanel />

      <section class="chat-card">
        <header class="chat-card__header">
          <div class="chat-card__identity">
            <Avatar
              :src="customerService.avatar"
              :alt="`${customerService.name} 头像`"
              :size="42"
              ring="success"
              status-dot
            />
            <div class="chat-card__who">
              <h1 class="chat-card__title">电商客服系统</h1>
              <p class="chat-card__meta">
                <span class="chat-card__name">{{ customerService.name }}</span>
                <span aria-hidden="true">·</span>
                <span>{{ customerService.title }}</span>
                <span aria-hidden="true">·</span>
                <span class="chat-card__online">{{ customerService.status }}</span>
              </p>
            </div>
          </div>

          <AppButton
            variant="ghost"
            size="sm"
            title="清空当前对话视图（不删除服务端记录）"
            @click="reset"
          >
            <template #icon><Icon name="refresh" :size="15" /></template>
            新对话
          </AppButton>
        </header>

        <div class="chat-card__toolbar">
          <AppField
            label="sender_id"
            for-id="workbench-sender"
            hint="切换用户身份后自动重新加载会话与业务对象"
          >
            <AppInput
              id="workbench-sender"
              v-model="senderId"
              placeholder="u1001"
              @enter="loadObjects(senderId)"
            />
          </AppField>
        </div>

        <MessageStream :debug="debug" />
        <Composer />
      </section>

      <ObjectSidebar :collapsed="sidebarCollapsed" @toggle="sidebarCollapsed = !sidebarCollapsed" />
    </div>
  </div>
</template>

<style scoped>
/* 三栏共用一个高度来源：顶栏之外的视口高度。此前左栏少减了 --shell-h，
   导致数字人栏比中右两栏高 56px、三栏顶底错位。 */
.workbench {
  height: calc(100vh - var(--shell-h));
  padding: var(--space-6);
  overflow: hidden;
}

.workbench__grid {
  width: min(1760px, 100%);
  height: 100%;
  margin: 0 auto;
  display: grid;
  grid-template-columns: var(--wb-left) minmax(0, 1fr) var(--wb-right);
  gap: var(--wb-gap);
  /* 收起/展开时右栏宽度平滑过渡（grid-template-columns 可动画） */
  transition: grid-template-columns 0.28s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 收起态：右栏压成竖向轨道 */
.workbench__grid--sbmin {
  --wb-right: 56px;
}

.workbench__grid > * {
  min-height: 0;
}

.chat-card {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.chat-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--border-light);
  flex-shrink: 0;
}

.chat-card__identity {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-width: 0;
}

.chat-card__who {
  min-width: 0;
}

.chat-card__title {
  font-size: var(--text-lg);
  font-weight: var(--weight-bold);
  color: var(--color-text-primary);
  line-height: var(--leading-tight);
}

.chat-card__meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: 2px;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.chat-card__name {
  font-weight: var(--weight-semibold);
  color: var(--color-text-secondary);
}

.chat-card__online {
  color: var(--color-success);
}

.chat-card__toolbar {
  padding: var(--space-3) var(--space-5);
  border-bottom: 1px solid var(--border-light);
  background: var(--surface-raised);
  flex-shrink: 0;
}

@media (max-width: 1439px) {
  .workbench {
    padding: var(--space-4);
  }

  .workbench__grid {
    --wb-left: 300px;
    --wb-right: 340px;
    --wb-gap: 16px;
  }
}

@media (max-width: 1179px) {
  /* 单列堆叠：高度交还文档流，由各块自己决定 */
  .workbench {
    height: auto;
    overflow: visible;
  }

  .workbench__grid {
    grid-template-columns: minmax(0, 1fr);
    height: auto;
  }

  .chat-card {
    height: min(72vh, 680px);
  }
}
</style>
