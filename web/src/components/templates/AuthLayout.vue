<script setup lang="ts">
</script>

<template>
  <div class="auth-layout">
    <div class="auth-card">
      <div class="auth-brand">
        <span class="auth-title">FileFlash</span>
      </div>
      <router-view v-slot="{ Component, route }">
        <transition name="page-fade" mode="out-in">
          <component :is="Component" :key="route.path" />
        </transition>
      </router-view>
    </div>
  </div>
</template>

<style scoped>
.auth-layout {
  display: flex; align-items: center; justify-content: center;
  width: 100vw; height: 100vh;
  background: var(--surface-base);
}
.auth-card {
  width: min(420px, 92vw);
  padding: var(--sp-2xl);
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
}
.auth-brand {
  display: flex; align-items: center;
  margin-bottom: var(--sp-xl);
}
.auth-title { font-size: var(--text-h1); font-weight: var(--weight-semibold); color: var(--text-primary); }

.page-fade-enter-active, .page-fade-leave-active {
  transition: opacity var(--mo-duration-mid) var(--mo-easing), transform var(--mo-duration-mid) var(--mo-easing);
}
.page-fade-enter-from { opacity: 0; transform: scale(0.98); }
.page-fade-leave-to { opacity: 0; transform: scale(1.02); }
</style>
