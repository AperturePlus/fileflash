<script setup lang="ts">
import { computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { NButton, NSpace } from 'naive-ui';
import { useLocaleStore } from '../../store/locale';

const router = useRouter();
const route = useRoute();
const localeStore = useLocaleStore();
const t = localeStore.t;

const isSkills = computed(() => route.path.startsWith('/agent/skills'));

const goWorkspace = () => {
  router.push('/agent');
};

const goSkills = () => {
  router.push('/agent/skills');
};
</script>

<template>
  <div class="agent-layout">
    <header class="agent-header">
      <div class="heading">
        <h1>{{ t('agent.pageTitle') }}</h1>
        <p>{{ t('agent.pageDescription') }}</p>
      </div>
      <NSpace size="small">
        <NButton :type="isSkills ? 'default' : 'primary'" secondary strong @click="goWorkspace">
          {{ t('agent.nav.workspace') }}
        </NButton>
        <NButton :type="isSkills ? 'primary' : 'default'" secondary strong @click="goSkills">
          {{ t('agent.nav.skills') }}
        </NButton>
      </NSpace>
    </header>

    <router-view />
  </div>
</template>

<style scoped>
.agent-layout {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.agent-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius-lg);
  background:
    radial-gradient(720px 420px at 0% -10%, rgba(var(--color-primary-rgb), 0.14), transparent 60%),
    var(--color-bg-secondary);
}

.heading h1 {
  margin: 0;
  font-size: 30px;
}

.heading p {
  margin: 8px 0 0;
  color: var(--color-text-tertiary);
}

@media (max-width: 920px) {
  .agent-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
