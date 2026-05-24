<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { getAdminUsers, updateUserStatus } from '../../../api/user';
import { AdminTable, FilterBar, StatusBadge } from '../../../components/console';
import { ui } from '../../../utils/ui';

interface AdminUser {
  userId: string;
  username: string;
  email: string;
  role: string;
  status: 'active' | 'suspended';
  lastLoginAt: string | null;
  createdAt: string;
}

const items = ref<AdminUser[]>([]);
const totalPages = ref(1);
const currentPage = ref(1);
const search = ref('');
const status = ref<'all' | 'active' | 'suspended'>('all');
const loading = ref(false);

async function load(page = 1) {
  loading.value = true;
  try {
    const resp = await getAdminUsers({
      page,
      perPage: 20,
      ...(search.value ? { search: search.value.trim() } : {}),
      ...(status.value !== 'all' ? { status: status.value } : {}),
    });
    items.value = resp.items as AdminUser[];
    totalPages.value = resp.pagination.totalPages;
    currentPage.value = resp.pagination.currentPage;
  } finally {
    loading.value = false;
  }
}

async function toggleStatus(user: AdminUser) {
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
            <strong>{{ (row as AdminUser).username }}</strong>
            <small>{{ (row as AdminUser).email }} · {{ (row as AdminUser).role }}</small>
          </div>
          <div class="row__actions">
            <StatusBadge
              :value="(row as AdminUser).status"
              :tone="(row as AdminUser).status === 'active' ? 'positive' : 'danger'"
            />
            <button class="row__btn" @click="toggleStatus(row as AdminUser)">
              {{ (row as AdminUser).status === 'active' ? 'Suspend' : 'Activate' }}
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
