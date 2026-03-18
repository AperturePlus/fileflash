<script setup lang="ts">
import { useThemeStore } from './store/theme';

// Initialize the theme store to apply the theme on app load.
// This is kept here as it applies classes to the <body> tag globally.
useThemeStore();
</script>

<template>
  <router-view />
</template>

<style>
/* Global styles are in style.css */
/* This can remain empty or be used for truly global, non-scoped styles if needed. */
</style>
