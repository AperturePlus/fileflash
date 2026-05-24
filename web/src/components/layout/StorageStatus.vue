<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed, type PropType } from 'vue';
import { useUserStore } from '../../store/user';
import type { StorageStats } from '../../types/user';
import { eventBus } from '../../utils/eventBus';

const props = defineProps({
  stats: {
    type: Object as PropType<StorageStats | null>,
    default: null,
  },
});

const userStore = useUserStore();
const localStats = ref<StorageStats | null>(null);
const isLoading = ref(false);

const storageData = computed(() => props.stats || localStats.value);
const progressPercentage = computed(() => {
  if (!storageData.value) return 0;
  const raw = Number(storageData.value.storagePercentage);
  if (!Number.isFinite(raw)) return 0;
  return Math.min(100, Math.max(0, raw));
});
const progressWidthPercentage = computed(() => {
  const stats = storageData.value;
  if (!stats) return 0;
  if (stats.storageUsed > 0 && progressPercentage.value > 0 && progressPercentage.value < 1) {
    return 1;
  }
  return progressPercentage.value;
});

const formatBytes = (bytes: number, decimals = 2) => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

watch(
  () => userStore.storageStats,
  (nextStats) => {
    if (!props.stats) {
      localStats.value = nextStats;
    }
  },
  { immediate: true },
);

function refreshStorageStats() {
  userStore.scheduleStorageStatsRefresh();
}

onMounted(async () => {
  eventBus.on('refresh-file-tree', refreshStorageStats);
  if (props.stats) {
    return;
  }
  isLoading.value = true;
  try {
    await userStore.fetchStorageStats();
    localStats.value = userStore.storageStats;
  } catch (error) {
    console.error('Failed to load storage stats in component:', error);
  } finally {
    isLoading.value = false;
  }
});

onUnmounted(() => {
  eventBus.off('refresh-file-tree', refreshStorageStats);
});
</script>

<template>
  <div class="storage-status">
    <div v-if="isLoading" class="loading-indicator">
      Loading storage...
    </div>
    <div v-else-if="storageData" class="stats-container">
      <div class="progress-bar-wrapper">
        <div class="progress-bar">
          <div 
            class="progress-bar-fill" 
            :style="{ width: progressWidthPercentage + '%' }"
          ></div>
        </div>
      </div>
      <div class="stats-text">
        <span>{{ formatBytes(storageData.storageUsed) }}</span> of 
        <span>{{ formatBytes(storageData.storageLimit) }}</span> used
      </div>
    </div>
    <div v-else class="error-indicator">
      Could not load storage data.
    </div>
  </div>
</template>

<style scoped>
.storage-status {
  padding: var(--spacing-sm) 0;
}
.progress-bar-wrapper {
  width: 100%;
  height: 12px;
  background-color: var(--color-bg-tertiary);
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: var(--spacing-sm);
}
.progress-bar-fill {
  height: 100%;
  background-color: var(--color-primary);
  border-radius: 6px;
  transition: width 0.5s ease-in-out;
}
.stats-text {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  text-align: center;
}
.stats-text span {
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
}
.loading-indicator, .error-indicator {
  text-align: center;
  color: var(--color-text-secondary);
  padding: var(--spacing-lg) 0;
}
</style> 
