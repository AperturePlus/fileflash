<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useFileStore } from '../../store/file';
import { storeToRefs } from 'pinia';
import AppHeader from './Header.vue';
import LeftSidebar from './LeftSidebar.vue';
import RightSidebar from './RightSidebar.vue';
import AppFooter from './Footer.vue';

const fileStore = useFileStore();
const { selectedFile } = storeToRefs(fileStore);

const leftSidebarCollapsed = ref(false);
const rightSidebarHidden = ref(false);

const rightSidebarVisible = computed(() => !!selectedFile.value && !rightSidebarHidden.value);

watch(selectedFile, (value) => {
  if (!value) {
    rightSidebarHidden.value = false;
  }
});

const toggleLeftSidebar = () => {
  leftSidebarCollapsed.value = !leftSidebarCollapsed.value;
};

const toggleRightSidebar = () => {
  if (!selectedFile.value) return;
  rightSidebarHidden.value = !rightSidebarHidden.value;
};
</script>

<template>
  <div class="main-layout">
    <AppHeader
      :left-sidebar-collapsed="leftSidebarCollapsed"
      :right-sidebar-visible="rightSidebarVisible"
      @toggle-left-sidebar="toggleLeftSidebar"
      @toggle-right-sidebar="toggleRightSidebar"
    />

    <div class="layout-body">
      <LeftSidebar :collapsed="leftSidebarCollapsed" />

      <main class="main-content">
        <section class="content-wrapper">
          <router-view v-slot="{ Component }">
            <template v-if="Component">
              <Suspense>
                <component :is="Component" />
                <template #fallback>
                  <div class="loading-fallback">Loading...</div>
                </template>
              </Suspense>
            </template>
          </router-view>
        </section>
        <AppFooter />
      </main>

      <RightSidebar :visible="rightSidebarVisible" />
    </div>
  </div>
</template>

<style scoped>
.main-layout {
  display: flex;
  flex-direction: column;
  width: 100vw;
  height: 100vh;
}

.layout-body {
  display: flex;
  min-height: 0;
  flex: 1;
}

.main-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.content-wrapper {
  flex: 1;
  overflow: auto;
  padding: var(--spacing-lg);
}

.loading-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 240px;
  color: var(--color-text-tertiary);
}

@media (max-width: 960px) {
  .content-wrapper {
    padding: var(--spacing-md);
  }
}
</style>
