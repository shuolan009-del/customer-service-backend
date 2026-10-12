<script setup>
import { useRoute, navigate } from '../../router/useRoute'
import { NAV_ITEMS } from '../../router/routes'
import { useNetwork } from '../../composables/useNetwork'
import Icon from '../ui/Icon.vue'

const route = useRoute()
const { online } = useNetwork()

function go(path) {
  navigate(path)
}
</script>

<template>
  <div class="shell">
    <a class="skip-link" href="#main">跳到主内容</a>

    <header class="topbar">
      <div class="topbar__inner">
        <button
          type="button"
          class="brand"
          aria-label="返回工作台"
          @click="go('/')"
        >
          <span class="brand__mark" aria-hidden="true"><Icon name="chat" :size="16" /></span>
          <span class="brand__text">电商小二</span>
          <span class="brand__sub">智能客服系统</span>
        </button>

        <nav class="nav" aria-label="主导航">
          <button
            v-for="item in NAV_ITEMS"
            :key="item.path"
            type="button"
            class="nav__item"
            :class="{ 'is-active': route.path === item.path }"
            :aria-current="route.path === item.path ? 'page' : undefined"
            @click="go(item.path)"
          >
            <Icon :name="item.icon" :size="16" />
            <span>{{ item.label }}</span>
          </button>
        </nav>

        <div class="topbar__right">
          <span
            class="status-pill"
            :class="online ? 'status-pill--online' : 'status-pill--offline'"
            role="status"
          >
            <Icon :name="online ? 'wifi' : 'wifiOff'" :size="14" />
            <span>{{ online ? '在线' : '离线' }}</span>
          </span>
        </div>
      </div>
    </header>

    <main id="main" class="shell__main" tabindex="-1">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.shell {
  min-height: 100vh;
  background: var(--surface-raised);
  display: flex;
  flex-direction: column;
}

/* 跳转链接样式由全局 base.css 提供（.skip-link） */

.topbar {
  position: sticky;
  top: 0;
  z-index: var(--z-header);
  height: var(--shell-h);
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}

.topbar__inner {
  height: 100%;
  width: min(1760px, 100%);
  margin: 0 auto;
  padding: 0 var(--space-6);
  display: flex;
  align-items: center;
  gap: var(--space-6);
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: var(--space-3);
  border: none;
  background: transparent;
  cursor: pointer;
  padding: var(--space-1) var(--space-2);
  margin-left: calc(var(--space-2) * -1);
  border-radius: var(--radius-md);
  color: var(--color-text-primary);
}
.brand:hover {
  background: var(--surface-hover);
}

.brand__mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  background: var(--color-primary);
  color: var(--color-on-primary);
}

.brand__text {
  font-size: var(--text-md);
  font-weight: var(--weight-bold);
  letter-spacing: 0.01em;
}

.brand__sub {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  padding-left: var(--space-3);
  border-left: 1px solid var(--border);
}

.nav {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  flex: 1;
  min-width: 0;
  overflow-x: auto;
}

.nav__item {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: none;
  background: transparent;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  font-size: var(--text-base);
  font-weight: var(--weight-medium);
  cursor: pointer;
  white-space: nowrap;
  transition:
    background var(--duration-fast) var(--ease-in-out),
    color var(--duration-fast) var(--ease-in-out);
}

.nav__item:hover {
  background: var(--surface-hover);
  color: var(--color-text-primary);
}

/* 激活态：主色浅底 + 加粗 + 下划线（不只靠颜色区分） */
.nav__item.is-active {
  background: var(--color-primary-soft-bg);
  color: var(--color-primary);
  font-weight: var(--weight-semibold);
}

.nav__item.is-active::after {
  content: '';
  position: absolute;
  left: var(--space-3);
  right: var(--space-3);
  bottom: -1px;
  height: 2px;
  border-radius: var(--radius-full);
  background: var(--color-primary);
}

.topbar__right {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-shrink: 0;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: 3px var(--space-3);
  border-radius: var(--radius-full);
  border: 1px solid var(--border);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  color: var(--color-text-secondary);
  background: var(--surface);
}

.status-pill--online {
  color: var(--color-success);
  border-color: var(--color-success-soft);
  background: var(--color-success-soft);
}

.status-pill--offline {
  color: var(--color-danger);
  border-color: var(--color-danger-soft);
  background: var(--color-danger-soft);
}

.shell__main {
  flex: 1;
  min-height: 0;
  outline: none;
}

@media (max-width: 1179px) {
  .topbar__inner {
    padding: 0 var(--space-4);
    gap: var(--space-3);
  }
  .brand__sub {
    display: none;
  }
}

@media (max-width: 767px) {
  .brand__text {
    display: none;
  }
  .nav__item span {
    display: none;
  }
  .nav__item {
    padding: var(--space-2);
  }
  .status-pill span {
    display: none;
  }
}
</style>
