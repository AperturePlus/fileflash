<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { getStorageStats } from '../../../api/user';
import type { StorageStats } from '../../../types/user';
import Text from '../../atoms/Text.vue';
import MonoNumber from '../../atoms/MonoNumber.vue';
import Bar from '../../atoms/Bar.vue';

defineProps<{ collapsed: boolean }>();

const storage = ref<StorageStats | null>(null);

const pct = computed(() => {
  if (!storage.value || storage.value.storageLimit === 0) return 0;
  return Math.min(1, storage.value.storageUsed / storage.value.storageLimit);
});
const pctLabel = computed(() => Math.round(pct.value * 100));

function fmt(bytes: number, decimals = 1) {
  if (bytes === 0) return '0 B';
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const k = 1024;
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(decimals < 0 ? 0 : decimals))} ${sizes[i]}`;
}

onMounted(() => {
  getStorageStats().then(s => storage.value = s);
});
</script>

<template>
  <div class="storage-widget" :class="{ 'storage-widget--collapsed': collapsed }">
    <div class="storage-head">
      <Text v-if="!collapsed" variant="label">Storage</Text>
      <MonoNumber :value="`${pctLabel}%`" accent />
    </div>
    <Bar :value="pct" :tone="pct > 0.9 ? 'error' : 'accent'" />
    <p v-if="!collapsed" class="storage-meta">
      {{ fmt(storage?.storageUsed ?? 0) }} / {{ fmt(storage?.storageLimit ?? 0) }}
    </p>
  </div>
</template>

<style scoped>
.storage-widget { padding: 10px; background: var(--surface-inset); border: 1px solid var(--border-subtle); }
.storage-widget--collapsed { padding: 8px; }
.storage-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.storage-meta { margin: 6px 0 0; font-size: var(--text-small); color: var(--text-dim); }
</style>
