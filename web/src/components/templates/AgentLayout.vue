<template>
  <div class="agent-layout">
    <router-view v-slot="{ Component, route }">
      <transition name="page-fade" mode="out-in">
        <component :is="Component" :key="route.path" />
      </transition>
    </router-view>
  </div>
</template>

<style scoped>
.agent-layout { display: flex; flex-direction: column; flex: 1; min-height: 0; }
.page-fade-enter-active, .page-fade-leave-active {
  transition: opacity var(--mo-duration-mid) var(--mo-easing);
}
.page-fade-enter-from, .page-fade-leave-to { opacity: 0; }
</style>
