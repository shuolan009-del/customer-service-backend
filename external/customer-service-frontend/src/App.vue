<script setup>
/**
 * 应用根：只负责
 *   ① 顶栏页壳（AppShell，含主导航与联网状态）
 *   ② 按 hash 路由渲染当前视图
 *   ③ 挂载全局单例：Toast（提示）与 ConfirmDialog（二次确认）
 * 具体业务在 src/views/* 中实现。
 */
import { computed } from 'vue'
import AppShell from './components/layout/AppShell.vue'
import ToastHost from './components/ui/ToastHost.vue'
import ConfirmDialog from './components/ui/ConfirmDialog.vue'
import { useRoute } from './router/useRoute'
import { resolveView } from './router/routes'

const route = useRoute()
const currentView = computed(() => resolveView(route.path))
</script>

<template>
  <AppShell>
    <component :is="currentView" />
  </AppShell>

  <ToastHost />
  <ConfirmDialog />
</template>
