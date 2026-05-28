<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { getViolations, resolveViolation } from '../../../api/user';
import { AdminTable, FilterBar, StatusBadge } from '../../../components/console';
import { ui } from '../../../utils/ui';

interface ViolationRow {
  id: string;
  fileId: string | null;
  fileName: string | null;
  type: string;
  level: 'low' | 'medium' | 'high';
  reportedAt: string;
  status: 'pending' | 'under_review' | 'resolved';
}

const items = ref<ViolationRow[]>([]);
const statusFilter = ref<'all' | 'pending' | 'under_review' | 'resolved'>('pending');
const loading = ref(false);

const levelTone = (l: ViolationRow['level']) =>
  l === 'high' ? 'danger' : l === 'medium' ? 'warning' : 'neutral';

async function load() {
  loading.value = true;
  try {
    const resp = await getViolations();
    items.value = (resp.items as ViolationRow[]).filter(
      (r) => statusFilter.value === 'all' || r.status === statusFilter.value,
    );
  } finally {
    loading.value = false;
  }
}

async function resolve(row: ViolationRow) {
  await resolveViolation(row.id);
  row.status = 'resolved';
  ui.toast({ type: 'success', message: 'Violation resolved' });
}

onMounted(load);
</script>

<template>
  <section class="page">
    <header class="page__header"><h1>Moderation</h1></header>

    <FilterBar @change="load">
      <select v-model="statusFilter">
        <option value="all">All</option>
        <option value="pending">Pending</option>
        <option value="under_review">Under Review</option>
        <option value="resolved">Resolved</option>
      </select>
    </FilterBar>

    <AdminTable :items="items" :loading="loading">
      <template #row="{ row }">
        <div class="row">
          <div class="row__main">
            <strong>{{ (row as ViolationRow).fileName || '—' }}</strong>
            <small>
              {{ (row as ViolationRow).type }} ·
              {{ new Date((row as ViolationRow).reportedAt).toLocaleString() }}
            </small>
          </div>
          <div class="row__actions">
            <StatusBadge
              :value="(row as ViolationRow).level"
              :tone="levelTone((row as ViolationRow).level)"
            />
            <StatusBadge
              :value="(row as ViolationRow).status"
              :tone="(row as ViolationRow).status === 'resolved' ? 'positive' : 'warning'"
            />
            <button
              class="row__btn"
              :disabled="(row as ViolationRow).status === 'resolved'"
              @click="resolve(row as ViolationRow)"
            >
              Resolve
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
.row__btn:hover:not(:disabled) {
  border-color: var(--ac);
  color: var(--ac);
}
.row__btn:disabled { opacity: 0.4; cursor: not-allowed; }
</style>
