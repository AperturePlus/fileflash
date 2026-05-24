<script setup lang="ts">
import ConsoleSidebar from './ConsoleSidebar.vue';
</script>

<template>
  <div class="console-layout">
    <ConsoleSidebar />
    <main class="console-main">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.console-layout {
  display: flex;
  min-height: 100%;
  margin: calc(var(--sp-lg) * -1);
  background: var(--surface-base);
}
.console-main {
  flex: 1;
  min-width: 0;
  padding: var(--sp-xl);
  overflow: auto;
}
</style>
