<script setup lang="ts">
import { computed, ref } from 'vue';
import { useFileStore } from '../../store/file';
import { storeToRefs } from 'pinia';
import AppHeader from '../organisms/shell/AppHeader.vue';
import LeftSidebar from '../organisms/shell/LeftSidebar.vue';
import RightSidebar from '../organisms/shell/RightSidebar.vue';
import Footer from '../organisms/shell/Footer.vue';
import Spinner from '../atoms/Spinner.vue';

const fileStore = useFileStore();
const { selectedFile } = storeToRefs(fileStore);

const leftCollapsed = ref(false);
const rightHidden = ref(false);
const rightVisible = computed(() => !!selectedFile.value && !rightHidden.value);

function toggleLeft() { leftCollapsed.value = !leftCollapsed.value; }
function toggleRight() { if (selectedFile.value) rightHidden.value = !rightHidden.value; }
</script>

<template>
  <div class="main-layout">
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
          <router-view v-slot="{ Component, route }">
            <transition name="page-fade" mode="out-in">
              <Suspense>
                <component :is="Component" :key="route.path" />
                <template #fallback>
                  <div class="fallback">
                    <Spinner label="Loading page" />
                  </div>
                </template>
              </Suspense>
            </transition>
          </router-view>
        </div>
        <Footer />
      </main>
      <RightSidebar :visible="rightVisible" />
    </div>
  </div>
</template>

<style scoped>
.main-layout { display: flex; flex-direction: column; width: 100vw; height: 100vh; }
.layout-body { display: flex; min-height: 0; flex: 1; }
.layout-content { flex: 1; min-width: 0; display: flex; flex-direction: column; overflow: hidden; }
.content-scroll { flex: 1; overflow: auto; padding: var(--sp-lg); }
.fallback { display: flex; align-items: center; justify-content: center; min-height: 240px; }

.page-fade-enter-active, .page-fade-leave-active {
  transition: opacity var(--mo-duration-mid) var(--mo-easing), transform var(--mo-duration-mid) var(--mo-easing);
}
.page-fade-enter-from { opacity: 0; transform: scale(0.98); }
.page-fade-leave-to { opacity: 0; transform: scale(1.02); }
</style>
