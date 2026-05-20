<script setup lang="ts">
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { storeToRefs } from 'pinia';
import { useUserStore } from '../../store/user';
import { useLocaleStore } from '../../store/locale';
import Button from '../molecules/Button.vue';

const router = useRouter();
const { isAuthenticated } = storeToRefs(useUserStore());
const localeStore = useLocaleStore();
const { locale } = storeToRefs(localeStore);

const isZh = computed(() => locale.value === 'zh-CN');
const homeLabel = computed(() => (isZh.value ? '返回主页' : 'Back to Home'));

function goHome() {
  router.push(isAuthenticated.value ? '/files' : '/login');
}
</script>

<template>
  <div class="bare-layout">
    <header class="bare-topbar">
      <span class="bare-topbar__brand">[ FILEFLASH ]</span>
      <Button variant="ghost" size="sm" icon="chevronLeft" @click="goHome">
        {{ homeLabel }}
      </Button>
    </header>

    <main class="bare-layout__main">
      <router-view v-slot="{ Component, route }">
        <transition name="page-fade" mode="out-in">
          <component :is="Component" :key="route.path" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<style scoped>
.bare-layout {
  display: flex;
  flex-direction: column;
  width: 100vw;
  height: 100vh;
  background: var(--surface-base);
}

.bare-topbar {
  flex-shrink: 0;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--sp-xl);
  border-bottom: 1px solid var(--border-default);
  background: var(--surface-raised);
}

.bare-topbar__brand {
  font-family: var(--font-mono);
  font-size: var(--text-label);
  font-weight: var(--weight-bold);
  letter-spacing: var(--tracking-wider);
  text-transform: uppercase;
  color: var(--text-secondary);
}

.bare-layout__main {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: auto;
  padding: var(--sp-xl) 0;
}

.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity var(--mo-duration-mid) var(--mo-easing);
}
.page-fade-enter-from,
.page-fade-leave-to {
  opacity: 0;
}
</style>
