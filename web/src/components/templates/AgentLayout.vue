<script setup lang="ts">
import { computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import SegmentedControl from '../molecules/SegmentedControl.vue';
import { useLocaleStore } from '../../store/locale';

const router = useRouter();
const route = useRoute();
const localeStore = useLocaleStore();
const t = localeStore.t;

const TABS = computed(() => [
  { value: 'workspace', label: t('agent.v2.layout.tab.workspace') },
  { value: 'skills', label: t('agent.v2.layout.tab.skills') },
]);

const currentTab = computed(() =>
  route.path.startsWith('/agent/skills') ? 'skills' : 'workspace',
);

const onTab = (v: string | number) =>
  router.push(v === 'skills' ? '/agent/skills' : '/agent');
</script>

<template>
  <div class="agent-layout">
    <header class="agent-layout__head">
      <span class="agent-layout__brand">{{ t('agent.v2.layout.brand') }}</span>
      <SegmentedControl :model-value="currentTab" :options="TABS" @update:model-value="onTab" />
    </header>
    <div class="agent-layout__body">
      <router-view v-slot="{ Component, route: r }">
        <transition name="page-fade" mode="out-in">
          <component :is="Component" :key="r.path" class="agent-layout__page" />
        </transition>
      </router-view>
    </div>
  </div>
</template>

<style scoped>
.agent-layout {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  min-width: 0;
}
.agent-layout__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-md);
  height: 48px;
  padding: 0 var(--sp-lg);
  border-bottom: 1px solid var(--border-default);
  background: var(--surface-base);
  flex-shrink: 0;
}
.agent-layout__brand {
  font-family: var(--font-mono);
  font-size: var(--text-label);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
  color: var(--text-tertiary);
}
.agent-layout__body {
  flex: 1;
  min-height: 0;
  min-width: 0;
  display: flex;
  position: relative;
}
.agent-layout__page {
  flex: 1;
  min-height: 0;
  min-width: 0;
}

.page-fade-enter-active, .page-fade-leave-active {
  transition: opacity var(--mo-duration-mid) var(--mo-easing);
}
.page-fade-enter-from, .page-fade-leave-to { opacity: 0; }
</style>
