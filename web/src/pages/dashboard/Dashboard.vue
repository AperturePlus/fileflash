<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { getStorageStats } from '../../api/user';
import type { StorageStats } from '../../types/user';

const stats = ref<StorageStats | null>(null);
const isLoading = ref(true);

onMounted(async () => {
  try {
    stats.value = await getStorageStats();
  } catch (error) {
    console.error('Failed to fetch storage stats:', error);
  } finally {
    isLoading.value = false;
  }
});
</script>

<template>
  <div class="dashboard-page">
    <h2>Dashboard</h2>
    <div v-if="isLoading" class="loading">Loading stats...</div>
    <div v-else-if="stats" class="stats-grid">
      <div class="stat-card">
        <h4>Storage Usage</h4>
        <p>{{ (stats.storageUsed / 1024 / 1024 / 1024).toFixed(2) }} GB / {{ (stats.storageLimit / 1024 / 1024 / 1024).toFixed(2) }} GB</p>
        <progress :value="stats.storageUsed" :max="stats.storageLimit"></progress>
      </div>
      <div class="stat-card">
        <h4>File Count</h4>
        <p>{{ stats.fileCount }}</p>
      </div>
      <div class="stat-card">
        <h4>Folder Count</h4>
        <p>{{ stats.folderCount }}</p>
      </div>
      <!-- More stats can be added here -->
    </div>
    <div v-else class="error">
      Could not load statistics.
    </div>
  </div>
</template>

<style scoped>
.dashboard-page h2 {
  margin-bottom: var(--spacing-lg);
}
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: var(--spacing-lg);
}
.stat-card {
  background-color: var(--color-bg-secondary);
  padding: var(--spacing-lg);
  border-radius: var(--border-radius-md);
  box-shadow: var(--shadow-sm);
}
.stat-card h4 {
  margin-bottom: var(--spacing-sm);
  color: var(--color-text-secondary);
}
.stat-card p {
  font-size: 1.5rem;
  font-weight: var(--font-weight-semibold);
  margin: 0;
}
.stat-card progress {
  width: 100%;
  margin-top: var(--spacing-md);
}
</style> 