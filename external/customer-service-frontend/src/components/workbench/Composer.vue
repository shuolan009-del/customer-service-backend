<script setup>
import AppButton from '../ui/AppButton.vue'
import AppInput from '../ui/AppInput.vue'
import Icon from '../ui/Icon.vue'
import { useChat } from '../../composables/useChat'

const { draftMessage, isSending, sendTextMessage } = useChat()
</script>

<template>
  <form class="composer" @submit.prevent="sendTextMessage">
    <label class="sr-only" for="workbench-composer">咨询内容</label>
    <!-- Enter 提交交给 form 隐式提交（存在 submit 按钮即生效）：
         早年 AppInput 另挂了 @enter="sendTextMessage"，与 @submit 双调用，
         靠「首次同步清空 draftMessage」巧合才没双发，已移除。 -->
    <AppInput
      id="workbench-composer"
      v-model="draftMessage"
      placeholder="请输入咨询内容…"
      :disabled="isSending"
    />
    <AppButton
      type="submit"
      variant="primary"
      :disabled="isSending || !draftMessage.trim()"
      aria-label="发送消息"
    >
      <template #icon><Icon name="send" :size="16" /></template>
      {{ isSending ? '发送中…' : '发送' }}
    </AppButton>
  </form>
</template>

<style scoped>
.composer {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-5);
  border-top: 1px solid var(--bubble-in-border);
  background: var(--surface);
  flex-shrink: 0;
}

/* 聊天输入框比表单输入更柔和：浅绿浅边 + 大圆角 */
.composer :deep(.input) {
  border-color: var(--bubble-in-border);
  border-radius: var(--radius-lg);
}

/* 与 AppInput（46px）齐平 */
.composer :deep(.btn) {
  min-height: 46px;
  flex-shrink: 0;
}
</style>
