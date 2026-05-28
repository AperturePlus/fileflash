<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { getAdminLogs } from '../../../api/log';
import { AdminTable, FilterBar } from '../../../components/console';
import type { LogItem } from '../../../types/log';

const items = ref<LogItem[]>([]);
const totalPages = ref(1);
const currentPage = ref(1);
const userId = ref('');
const operation = ref('');
const loading = ref(false);

async function load(page = 1) {
  loading.value = true;
  try {
    const resp = await getAdminLogs({
      page,
      perPage: 20,
      ...(userId.value ? { userId: userId.value.trim() } : {}),
      ...(operation.value ? { operation: operation.value.trim() } : {}),
    });
    items.value = resp.logs;
    totalPages.value = resp.pagination.totalPages;
    currentPage.value = resp.pagination.currentPage;
  } finally {
    loading.value = false;
  }
}

onMounted(() => load(1));
</script>

<template>
  <section class="page">
    <header class="page__header"><h1>Logs</h1></header>

    <FilterBar @change="load(1)">
      <input v-model="userId" type="text" placeholder="User ID" />
      <input v-model="operation" type="text" placeholder="Operation" />
    </FilterBar>

    <AdminTable
      :items="items"
      :loading="loading"
      :total-pages="totalPages"
      :current-page="currentPage"
      @page-change="load"
    >
      <template #row="{ row }">
        <div class="log-row">
          <code>{{ new Date((row as LogItem).performedAt).toLocaleString() }}</code>
          <strong>{{ (row as LogItem).operationName }}</strong>
          <small>{{ (row as LogItem).ipAddress }} · {{ (row as LogItem).userId || 'system' }}</small>
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
.log-row {
  display: grid;
  grid-template-columns: 200px 1fr 200px;
  gap: var(--sp-md);
  align-items: center;
  padding: var(--sp-sm) 14px;
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
  font-family: var(--font-mono);
  font-size: var(--text-small);
}
.log-row code {
  color: var(--text-tertiary);
  font-variant-numeric: tabular-nums;
}
.log-row strong {
  color: var(--text-primary);
  font-weight: var(--weight-regular);
}
.log-row small {
  color: var(--text-tertiary);
  text-align: right;
  font-variant-numeric: tabular-nums;
}
</style>
