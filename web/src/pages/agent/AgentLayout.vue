<script setup lang="ts">
import { computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import SegmentedControl from '../../components/molecules/SegmentedControl.vue';

const router = useRouter();
const route = useRoute();

const TABS = [
  { value: 'workspace', label: 'WORKSPACE' },
  { value: 'skills', label: 'SKILLS' },
];

const currentTab = computed(() =>
  route.path.startsWith('/agent/skills') ? 'skills' : 'workspace',
);

const onTab = (v: string | number) =>
  router.push(v === 'skills' ? '/agent/skills' : '/agent');
</script>

<template>
  <div class="agent-layout">
    <header class="agent-layout__head">
      <span class="agent-layout__brand">[ FILEFLASH · AGENT ]</span>
      <SegmentedControl :model-value="currentTab" :options="TABS" @update:model-value="onTab" />
    </header>
    <router-view v-slot="{ Component }">
      <Transition name="page-fade" mode="out-in"><component :is="Component" /></Transition>
    </router-view>
  </div>
</template>

<style scoped>
.agent-layout { display: flex; flex-direction: column; height: 100%; min-height: 0; }
.agent-layout__head {
  display: flex; align-items: center; justify-content: space-between;
  gap: var(--sp-md); height: 48px; padding: 0 var(--sp-lg);
  border-bottom: 1px solid var(--border-default); background: var(--surface-base);
}
.agent-layout__brand {
  font-family: var(--font-mono); font-size: var(--text-label);
  letter-spacing: var(--tracking-wide); text-transform: uppercase;
  color: var(--text-tertiary);
}
.page-fade-enter-active, .page-fade-leave-active { transition: opacity 180ms var(--mo-easing); }
.page-fade-enter-from, .page-fade-leave-to { opacity: 0; }
</style>
