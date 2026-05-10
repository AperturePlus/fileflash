<script setup lang="ts">
import { computed } from 'vue';
import { darkTheme, NConfigProvider, NDialogProvider, NMessageProvider } from 'naive-ui';
import { useThemeStore } from './store/theme';
import { useLocaleStore } from './store/locale';
import ConfirmDialog from './components/common/ConfirmDialog.vue';
import PromptDialog from './components/common/PromptDialog.vue';
import ToastStack from './components/common/ToastStack.vue';

// Initialize the theme store to apply the theme on app load.
// This is kept here as it applies classes to the <body> tag globally.
useThemeStore();
useLocaleStore();

const themeStore = useThemeStore();
const naiveTheme = computed(() => (themeStore.theme === 'dark' ? darkTheme : null));
</script>

<template>
  <NConfigProvider :theme="naiveTheme">
    <NDialogProvider>
      <NMessageProvider placement="top-right" :max="4">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
        <ConfirmDialog />
        <PromptDialog />
        <ToastStack />
      </NMessageProvider>
    </NDialogProvider>
  </NConfigProvider>
</template>

<style>
/* Global styles are in style.css */
/* This can remain empty or be used for truly global, non-scoped styles if needed. */
.page-enter-active,
.page-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.page-enter-from {
  opacity: 0;
  transform: translateY(10px);
}
.page-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
