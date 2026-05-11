<template>
  <div class="agent-layout">
    <main class="agent-main">
      <router-view v-slot="{ Component, route }">
        <transition name="page-fade" mode="out-in">
          <component :is="Component" :key="route.path" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<style scoped>
.agent-layout { display: flex; flex-direction: column; width: 100vw; height: 100vh; background: var(--surface-base); }
.agent-main { flex: 1; overflow: auto; padding: var(--sp-lg); }
.page-fade-enter-active, .page-fade-leave-active {
  transition: opacity var(--mo-duration-mid) var(--mo-easing);
}
.page-fade-enter-from, .page-fade-leave-to { opacity: 0; }
</style>
