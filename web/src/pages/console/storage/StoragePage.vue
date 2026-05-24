<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import {
  getAdminStorageSummary,
  getStorageUsers,
  getUsageTrend,
  updateStorageQuota,
} from '../../../api/storage';
import { AdminTable, KpiCard, QuotaEditor, TrendChart } from '../../../components/console';
import { ui } from '../../../utils/ui';

interface StorageUserRow {
  userId: string;
  username: string;
  email: string;
  storageLimit: number;
  storageUsed: number;
  usagePercentage: number;
}

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
const days = ref<7 | 14 | 30>(7);
const users = ref<StorageUserRow[]>([]);
const editingId = ref<string | null>(null);

function fmt(b: number) {
  const u = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = b ? Math.floor(Math.log(b) / Math.log(1024)) : 0;
  return `${(b / Math.pow(1024, i)).toFixed(i ? 1 : 0)} ${u[i]}`;
}

async function reload() {
  const [s, t, u] = await Promise.all([
    getAdminStorageSummary(),
    getUsageTrend({ days: days.value }),
    getStorageUsers(),
  ]);
  summary.value = s;
  trend.value = t.trends;
  users.value = u.items as StorageUserRow[];
}

watch(days, () => reload());

async function applyQuota(user: StorageUserRow, bytes: number) {
  const result = await updateStorageQuota(user.userId, bytes);
  user.storageLimit = result.storageLimit;
  user.usagePercentage = result.usagePercentage;
  editingId.value = null;
  ui.toast({ type: 'success', message: 'Quota updated' });
}

onMounted(reload);
</script>

<template>
  <section class="page">
    <header class="page__header"><h1>Storage</h1></header>

    <div v-if="summary" class="kpis">
      <KpiCard title="Used" :value="fmt(summary.storageUsed)" />
      <KpiCard title="Limit" :value="fmt(summary.storageLimit)" />
      <KpiCard title="Users" :value="summary.userCount" />
    </div>

    <div class="trend-controls">
      <label v-for="opt in ([7, 14, 30] as const)" :key="opt">
        <input type="radio" :value="opt" v-model="days" /> {{ opt }}d
      </label>
    </div>
    <TrendChart v-if="trend.length" :points="trend" />

    <AdminTable :items="users">
      <template #row="{ row }">
        <div class="quota-row">
          <div class="quota-row__main">
            <strong>{{ (row as StorageUserRow).username }}</strong>
            <small>
              {{ fmt((row as StorageUserRow).storageUsed) }} /
              {{ fmt((row as StorageUserRow).storageLimit) }} ·
              {{ (row as StorageUserRow).usagePercentage.toFixed(1) }}%
            </small>
          </div>
          <QuotaEditor
            v-if="editingId === (row as StorageUserRow).userId"
            :current-bytes="(row as StorageUserRow).storageLimit"
            :storage-used="(row as StorageUserRow).storageUsed"
            @submit="(bytes) => applyQuota(row as StorageUserRow, bytes)"
          />
          <button
            v-else
            class="quota-row__btn"
            @click="editingId = (row as StorageUserRow).userId"
          >
            Adjust
          </button>
        </div>
      </template>
    </AdminTable>
  </section>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: var(--sp-lg);
}
.page__header h1 {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--text-h1);
  color: var(--text-primary);
  font-weight: var(--weight-medium);
  letter-spacing: var(--tracking-snug);
}
.kpis {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--sp-md);
}
.trend-controls {
  display: flex;
  gap: var(--sp-md);
  font-family: var(--font-mono);
  font-size: var(--text-small);
  color: var(--text-secondary);
}
.trend-controls label {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-xs);
  cursor: pointer;
}
.quota-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
  gap: var(--sp-md);
}
.quota-row__main { display: flex; flex-direction: column; }
.quota-row__main strong {
  font-family: var(--font-sans);
  font-size: var(--text-body);
  color: var(--text-primary);
}
.quota-row__main small {
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  font-size: var(--text-small);
}
.quota-row__btn {
  height: 28px;
  padding: 0 var(--sp-md);
  background: var(--surface-base);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: var(--text-small);
  cursor: pointer;
}
.quota-row__btn:hover {
  border-color: var(--ac);
  color: var(--ac);
}
</style>
