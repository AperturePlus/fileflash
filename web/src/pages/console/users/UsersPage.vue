<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { getAdminUsers, updateUserStatus } from '../../../api/user';
import { AdminTable, FilterBar, StatusBadge } from '../../../components/console';
import type { AdminUserItem } from '../../../types/user';
import { ui } from '../../../utils/ui';

const DAY_MS = 24 * 60 * 60 * 1000;

function toDateInput(date: Date) {
  return date.toISOString().slice(0, 10);
}

function startOfUtcDay(value: string) {
  return `${value}T00:00:00.000Z`;
}

function endOfUtcDay(value: string) {
  return `${value}T23:59:59.999Z`;
}

function formatBytes(bytes: number) {
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let value = Math.max(0, bytes);
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

function formatNumber(value: number) {
  return new Intl.NumberFormat('en-US').format(value);
}

const today = new Date();
const items = ref<AdminUserItem[]>([]);
const totalPages = ref(1);
const currentPage = ref(1);
const search = ref('');
const status = ref<'all' | 'active' | 'suspended'>('all');
const usageFrom = ref(toDateInput(new Date(today.getTime() - 7 * DAY_MS)));
const usageTo = ref(toDateInput(today));
const loading = ref(false);

async function load(page = 1) {
  loading.value = true;
  try {
    const resp = await getAdminUsers({
      page,
      perPage: 20,
      ...(search.value ? { search: search.value.trim() } : {}),
      ...(status.value !== 'all' ? { status: status.value } : {}),
      ...(usageFrom.value && usageTo.value ? {
        usageFrom: startOfUtcDay(usageFrom.value),
        usageTo: endOfUtcDay(usageTo.value),
      } : {}),
    });
    items.value = resp.items;
    totalPages.value = resp.pagination.totalPages;
    currentPage.value = resp.pagination.currentPage;
  } finally {
    loading.value = false;
  }
}

async function toggleStatus(user: AdminUserItem) {
  if (user.status !== 'active' && user.status !== 'suspended') return;
  const next = user.status === 'active' ? 'suspended' : 'active';
  await updateUserStatus(user.userId, next);
  user.status = next;
  ui.toast({ type: 'success', message: `User ${user.username} → ${next}` });
}

onMounted(() => load(1));
</script>

<template>
  <section class="page">
    <header class="page__header"><h1>Users</h1></header>

    <FilterBar @change="load(1)">
      <input v-model="search" type="text" placeholder="Search username/email" />
      <select v-model="status">
        <option value="all">All status</option>
        <option value="active">Active</option>
        <option value="suspended">Suspended</option>
      </select>
      <label class="filter-field">
        <span>Usage from</span>
        <input v-model="usageFrom" type="date" />
      </label>
      <label class="filter-field">
        <span>Usage to</span>
        <input v-model="usageTo" type="date" />
      </label>
    </FilterBar>

    <AdminTable
      :items="items"
      :loading="loading"
      :total-pages="totalPages"
      :current-page="currentPage"
      @page-change="load"
    >
      <template #row="{ row }">
        <div class="row">
          <div class="row__main">
            <strong>{{ (row as AdminUserItem).username }}</strong>
            <small>{{ (row as AdminUserItem).email }} · {{ (row as AdminUserItem).role }}</small>
            <div class="row__usage">
              <span>Uploaded {{ formatBytes((row as AdminUserItem).usageStats.trafficBytes) }}</span>
              <span>Agent {{ formatNumber((row as AdminUserItem).usageStats.agentTokens) }} tokens</span>
            </div>
          </div>
          <div class="row__actions">
            <StatusBadge
              :value="(row as AdminUserItem).status"
              :tone="(row as AdminUserItem).status === 'active' ? 'positive' : 'danger'"
            />
            <button class="row__btn" @click="toggleStatus(row as AdminUserItem)">
              {{ (row as AdminUserItem).status === 'active' ? 'Suspend' : 'Activate' }}
            </button>
          </div>
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
.filter-field {
  display: flex;
  gap: var(--sp-xs);
  align-items: center;
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  font-size: var(--text-small);
}
.row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--sp-md);
  padding: 10px 14px;
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
}
.row__main { display: flex; flex-direction: column; min-width: 0; }
.row__main strong {
  font-family: var(--font-sans);
  font-size: var(--text-body);
  color: var(--text-primary);
}
.row__main small {
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  font-size: var(--text-small);
}
.row__usage {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-sm);
  margin-top: 6px;
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: var(--text-small);
}
.row__actions { display: flex; gap: var(--sp-sm); align-items: center; }
.row__btn {
  height: 28px;
  padding: 0 var(--sp-md);
  background: var(--surface-base);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: var(--text-small);
  cursor: pointer;
}
.row__btn:hover {
  border-color: var(--ac);
  color: var(--ac);
}
</style>
