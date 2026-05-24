<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useLocaleStore } from '../../store/locale';
import type { LocaleKey } from '../../i18n/messages';

interface NavItem {
  key: string;
  path: string;
  labelKey: LocaleKey;
}

const route = useRoute();
const router = useRouter();
const t = useLocaleStore().t;

const items: NavItem[] = [
  { key: 'overview', path: '/console/overview', labelKey: 'console.nav.overview' },
  { key: 'users', path: '/console/users', labelKey: 'console.nav.users' },
  { key: 'storage', path: '/console/storage', labelKey: 'console.nav.storage' },
  { key: 'content', path: '/console/content', labelKey: 'console.nav.content' },
  { key: 'moderation', path: '/console/moderation', labelKey: 'console.nav.moderation' },
  { key: 'system', path: '/console/system', labelKey: 'console.nav.system' },
  { key: 'logs', path: '/console/logs', labelKey: 'console.nav.logs' },
  { key: 'notifications', path: '/console/notifications', labelKey: 'console.nav.notifications' },
  { key: 'rules', path: '/console/rules', labelKey: 'console.nav.rules' },
];

const activeKey = computed(() => items.find((item) => route.path.startsWith(item.path))?.key);
</script>

<template>
  <aside class="console-sidebar">
    <div class="console-sidebar__header">{{ t('console.title') }}</div>
    <nav class="console-sidebar__nav">
      <button
        v-for="item in items"
        :key="item.key"
        class="console-sidebar__item"
        :class="{ 'is-active': activeKey === item.key }"
        @click="router.push(item.path)"
      >
        {{ t(item.labelKey) }}
      </button>
    </nav>
  </aside>
</template>

<style scoped>
.console-sidebar {
  width: 200px;
  flex-shrink: 0;
  background: var(--surface-base);
  border-right: 1px solid var(--border-default);
  display: flex;
  flex-direction: column;
}
.console-sidebar__header {
  padding: var(--sp-lg);
  font-family: var(--font-mono);
  font-size: var(--text-label);
  color: var(--text-tertiary);
  letter-spacing: var(--tracking-wider);
  text-transform: uppercase;
}
.console-sidebar__nav {
  display: flex;
  flex-direction: column;
}
.console-sidebar__item {
  display: block;
  padding: 10px var(--sp-lg);
  background: transparent;
  border: none;
  color: var(--text-secondary);
  font-family: var(--font-sans);
  font-size: var(--text-body);
  text-align: left;
  cursor: pointer;
  border-left: 2px solid transparent;
  transition: background-color var(--mo-duration-fast) var(--mo-easing),
    color var(--mo-duration-fast) var(--mo-easing);
}
.console-sidebar__item:hover {
  background: var(--surface-raised);
  color: var(--text-primary);
}
.console-sidebar__item.is-active {
  color: var(--text-primary);
  background: var(--surface-raised);
  border-left-color: var(--ac);
}
</style>
