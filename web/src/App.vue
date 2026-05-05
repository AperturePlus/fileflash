<script setup lang="ts">
import { useThemeStore } from './store/theme';
import { useLocaleStore } from './store/locale';
import ConfirmDialog from './components/common/ConfirmDialog.vue';
import PromptDialog from './components/common/PromptDialog.vue';
import ToastStack from './components/common/ToastStack.vue';

// Initialize the theme store to apply the theme on app load.
// This is kept here as it applies classes to the <body> tag globally.
useThemeStore();
useLocaleStore();
</script>

<template>
  <router-view />
  <ConfirmDialog />
  <PromptDialog />
  <ToastStack />
</template>

<style>
/* Global styles are in style.css */
/* This can remain empty or be used for truly global, non-scoped styles if needed. */
</style>
