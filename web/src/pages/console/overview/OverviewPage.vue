<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { getAdminStorageSummary, getUsageTrend } from '../../../api/storage';
import { getViolations } from '../../../api/user';
import { getAdminLogs } from '../../../api/log';
import { getSystemHealth } from '../../../api/system';
import { KpiCard, TrendChart } from '../../../components/console';
import type { LogItem } from '../../../types/log';
import type { SystemHealth } from '../../../types/system';

interface AdminStorageSummary {
  storageUsed: number;
  storageLimit: number;
  storagePercentage: number;
  fileCount: number;
  userCount: number;
  updatedAt: string;
}

const summary = ref<AdminStorageSummary | null>(null);
const trend = ref<Array<{ date: string; used: number }>>([]);
const violations = ref<unknown[]>([]);
const recentLogs = ref<LogItem[]>([]);
const health = ref<SystemHealth | null>(null);

function formatBytes(bytes: number) {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

onMounted(async () => {
  const [s, tr, v, l, h] = await Promise.all([
    getAdminStorageSummary(),
    getUsageTrend({ days: 7 }),
    getViolations(),
    getAdminLogs({ page: 1, perPage: 5 }),
    getSystemHealth(),
  ]);
  summary.value = s;
  trend.value = tr.trends;
  violations.value = v.items;
  recentLogs.value = l.logs;
  health.value = h;
});
</script>

<template>
  <section class="overview">
    <header class="overview__header">
      <h1>Overview</h1>
    </header>

    <div v-if="summary && health" class="overview__kpis">
      <KpiCard title="Storage Used" :value="formatBytes(summary.storageUsed)" />
      <KpiCard title="Usage Ratio" :value="Math.round(summary.storagePercentage)" unit="%" />
      <KpiCard title="Total Files" :value="summary.fileCount" />
      <KpiCard title="Total Users" :value="summary.userCount" />
      <KpiCard
        title="Pending Violations"
        :value="violations.length"
        :accent="violations.length ? 'warning' : undefined"
      />
      <KpiCard title="Active Uploads" :value="health.activeUploadSessions" />
    </div>

    <h2 class="overview__section-title">7-Day Storage Trend</h2>
    <TrendChart v-if="trend.length" :points="trend" />

    <h2 class="overview__section-title">Recent Logs</h2>
    <ul class="overview__list">
      <li v-for="log in recentLogs" :key="log.id">
        <code>{{ new Date(log.performedAt).toLocaleString() }}</code>
        <span>{{ log.operationName }}</span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.overview {
  display: flex;
  flex-direction: column;
  gap: var(--sp-lg);
}
.overview__header h1 {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--text-h1);
  color: var(--text-primary);
  font-weight: var(--weight-medium);
  letter-spacing: var(--tracking-snug);
}
.overview__kpis {
  display: grid;
  gap: var(--sp-md);
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}
.overview__section-title {
  margin: var(--sp-sm) 0 0;
  font-family: var(--font-mono);
  font-size: var(--text-label);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wider);
  color: var(--text-tertiary);
  font-weight: var(--weight-regular);
}
.overview__list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.overview__list li {
  display: flex;
  gap: var(--sp-md);
  padding: var(--sp-sm) var(--sp-md);
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
  font-family: var(--font-mono);
  font-size: var(--text-body);
  color: var(--text-secondary);
}
.overview__list li code { color: var(--text-tertiary); }
</style>
