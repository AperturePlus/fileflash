<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRoute } from 'vue-router';
import { useFileStore } from '../../store/file';
import { storeToRefs } from 'pinia';
import AppHeader from '../organisms/shell/AppHeader.vue';
import LeftSidebar from '../organisms/shell/LeftSidebar.vue';
import RightSidebar from '../organisms/shell/RightSidebar.vue';
import Footer from '../organisms/shell/Footer.vue';
import Spinner from '../atoms/Spinner.vue';
import FilePreviewDialog from '../organisms/files/FilePreviewDialog.vue';
import type { FileItem } from '../../types/file';

const route = useRoute();
const fileStore = useFileStore();
const { previewFile } = storeToRefs(fileStore);

const leftCollapsed = ref(false);
const rightVisible = ref(false);

const fullscreen = computed(() => route.matched.some((r) => r.meta?.fullscreen));

const previewForDialog = computed<FileItem | null>(() =>
  previewFile.value && previewFile.value.itemType === 'file' ? (previewFile.value as FileItem) : null,
);

function toggleLeft() { leftCollapsed.value = !leftCollapsed.value; }
function toggleRight() { rightVisible.value = !rightVisible.value; }
function onClosePreview() {
  fileStore.previewFile = null;
  document.body.style.overflow = '';
}
</script>

<template>
  <div class="main-layout" :class="{ 'is-fullscreen': fullscreen }">
    <AppHeader
      :left-collapsed="leftCollapsed"
      :right-visible="rightVisible"
      @toggle-left="toggleLeft"
      @toggle-right="toggleRight"
    />
    <div class="layout-body">
      <LeftSidebar :collapsed="leftCollapsed" />
      <main class="layout-content">
        <div class="content-scroll">
          <router-view v-slot="{ Component, route: r }">
            <transition name="page-fade" mode="out-in">
              <Suspense>
                <component :is="Component" :key="r.path" />
                <template #fallback>
                  <div class="fallback">
                    <Spinner label="Loading page" />
                  </div>
                </template>
              </Suspense>
            </transition>
          </router-view>
        </div>
        <Footer v-if="!fullscreen" />
      </main>
      <RightSidebar :visible="rightVisible" />
    </div>
    <FilePreviewDialog :file="previewForDialog" @close="onClosePreview" />
  </div>
</template>

<style scoped>
.main-layout { display: flex; flex-direction: column; width: 100vw; height: 100vh; }
.layout-body { display: flex; min-height: 0; flex: 1; }
.layout-content { flex: 1; min-width: 0; display: flex; flex-direction: column; overflow: hidden; }
.content-scroll { flex: 1; overflow: auto; padding: var(--sp-lg); }
.fallback { display: flex; align-items: center; justify-content: center; min-height: 240px; }

.main-layout.is-fullscreen .content-scroll {
  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.page-fade-enter-active, .page-fade-leave-active {
  transition: opacity var(--mo-duration-mid) var(--mo-easing), transform var(--mo-duration-mid) var(--mo-easing);
}
.page-fade-enter-from { opacity: 0; transform: scale(0.98); }
.page-fade-leave-to { opacity: 0; transform: scale(1.02); }
</style>
