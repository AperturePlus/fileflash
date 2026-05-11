<template>
  <div class="share-layout">
    <header class="share-header">
      <span class="share-brand">FileFlash</span>
    </header>
    <main class="share-main">
      <router-view v-slot="{ Component, route }">
        <transition name="page-fade" mode="out-in">
          <component :is="Component" :key="route.path" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<style scoped>
.share-layout { display: flex; flex-direction: column; width: 100vw; height: 100vh; background: var(--surface-base); }
.share-header { height: var(--layout-header-height); display: flex; align-items: center; padding: 0 var(--sp-lg); border-bottom: 1px solid var(--border-default); }
.share-brand { font-size: var(--text-h2); font-weight: var(--weight-semibold); color: var(--text-primary); }
.share-main { flex: 1; overflow: auto; padding: var(--sp-xl); }
.page-fade-enter-active, .page-fade-leave-active {
  transition: opacity var(--mo-duration-mid) var(--mo-easing);
}
.page-fade-enter-from, .page-fade-leave-to { opacity: 0; }
</style>
