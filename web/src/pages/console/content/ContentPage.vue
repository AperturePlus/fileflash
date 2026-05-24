<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { getAdminFiles, rescanAdminFile } from '../../../api/file';
import { AdminTable, FilterBar, StatusBadge } from '../../../components/console';
import { ui } from '../../../utils/ui';
import type { AdminFileAuditItem } from '../../../types/file';

const items = ref<AdminFileAuditItem[]>([]);
const totalPages = ref(1);
const currentPage = ref(1);
const search = ref('');
const status = ref<'all' | 'clean' | 'pending' | 'flagged'>('all');
const loading = ref(false);

function fmt(b: number) {
  const u = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = b ? Math.floor(Math.log(b) / Math.log(1024)) : 0;
  return `${(b / Math.pow(1024, i)).toFixed(i ? 1 : 0)} ${u[i]}`;
}

const toneFor = (s: AdminFileAuditItem['virusStatus']) =>
  s === 'clean' ? 'positive' : s === 'flagged' ? 'danger' : 'warning';

async function load(page = 1) {
  loading.value = true;
  try {
    const resp = await getAdminFiles({
      page,
      perPage: 20,
      sort: 'updatedAt',
      order: 'desc',
      ...(search.value ? { search: search.value.trim() } : {}),
      ...(status.value !== 'all' ? { virusStatus: status.value } : {}),
    });
    items.value = resp.items;
    totalPages.value = resp.pagination.totalPages;
    currentPage.value = resp.pagination.currentPage;
  } finally {
    loading.value = false;
  }
}

async function rescan(file: AdminFileAuditItem) {
  const result = await rescanAdminFile(file.id);
  file.virusStatus = result.virusStatus;
  ui.toast({ type: 'info', message: `Rescan requested for ${file.name}` });
}

onMounted(() => load(1));
</script>

<template>
  <section class="page">
    <header class="page__header"><h1>Content Audit</h1></header>

    <FilterBar @change="load(1)">
      <input v-model="search" type="text" placeholder="Search file name" />
      <select v-model="status">
        <option value="all">All status</option>
        <option value="clean">Clean</option>
        <option value="pending">Pending</option>
        <option value="flagged">Flagged</option>
      </select>
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
            <strong>{{ (row as AdminFileAuditItem).name }}</strong>
            <small>
              {{ (row as AdminFileAuditItem).mimeType }} ·
              {{ fmt((row as AdminFileAuditItem).size) }} ·
              {{ (row as AdminFileAuditItem).hash }}
            </small>
          </div>
          <div class="row__actions">
            <StatusBadge
              :value="(row as AdminFileAuditItem).virusStatus"
              :tone="toneFor((row as AdminFileAuditItem).virusStatus)"
            />
            <button class="row__btn" @click="rescan(row as AdminFileAuditItem)">Rescan</button>
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
.row {
  display: flex;
  justify-content: space-between;
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
