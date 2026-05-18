<template>
  <div class="bare-layout">
    <router-view v-slot="{ Component, route }">
      <transition name="page-fade" mode="out-in">
        <component :is="Component" :key="route.path" />
      </transition>
    </router-view>
  </div>
</template>

<style scoped>
.bare-layout {
  display: flex; align-items: center; justify-content: center;
  width: 100vw; height: 100vh;
  background: var(--surface-base);
}
.page-fade-enter-active, .page-fade-leave-active {
  transition: opacity var(--mo-duration-mid) var(--mo-easing);
}
.page-fade-enter-from, .page-fade-leave-to { opacity: 0; }
</style>
