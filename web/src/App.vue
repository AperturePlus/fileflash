<script setup lang="ts">
import { computed } from 'vue';
import { darkTheme, NConfigProvider, NDialogProvider, NMessageProvider } from 'naive-ui';
import { useThemeStore } from './store/theme';
import { useLocaleStore } from './store/locale';
import ConfirmDialog from './components/common/ConfirmDialog.vue';
import PromptDialog from './components/common/PromptDialog.vue';
import ToastStack from './components/common/ToastStack.vue';

useThemeStore();
useLocaleStore();

const themeStore = useThemeStore();
const naiveTheme = computed(() => (themeStore.theme === 'dark' ? darkTheme : null));
</script>

<template>
  <NConfigProvider :theme="naiveTheme">
    <NDialogProvider>
      <NMessageProvider placement="top-right" :max="4">
        <router-view />
        <ConfirmDialog />
        <PromptDialog />
        <ToastStack />
      </NMessageProvider>
    </NDialogProvider>
  </NConfigProvider>
</template>

<style>
</style>
