<script setup lang="ts">
import { onMounted, ref } from 'vue';
import {
  archiveAdminNotification,
  broadcastNotification,
  getAdminNotifications,
} from '../../../api/notification';
import { AdminTable, BroadcastComposer, StatusBadge } from '../../../components/console';
import { ui } from '../../../utils/ui';
import type { NotificationItem } from '../../../types/notification';

const items = ref<NotificationItem[]>([]);
const totalPages = ref(1);
const currentPage = ref(1);
const loading = ref(false);

async function load(page = 1) {
  loading.value = true;
  try {
    const resp = await getAdminNotifications({ page, perPage: 20 });
    items.value = resp.items;
    totalPages.value = resp.pagination.totalPages;
    currentPage.value = resp.pagination.currentPage;
  } finally {
    loading.value = false;
  }
}

async function broadcast(message: string, title?: string) {
  await broadcastNotification(message, title);
  ui.toast({ type: 'success', message: 'Broadcast sent' });
  await load(1);
}

async function archive(row: NotificationItem) {
  await archiveAdminNotification(row.id);
  ui.toast({ type: 'success', message: 'Archived' });
  await load(currentPage.value);
}

onMounted(() => load(1));
</script>

<template>
  <section class="page">
    <header class="page__header"><h1>Notifications</h1></header>

    <BroadcastComposer @submit="broadcast" />

    <AdminTable
      :items="items"
      :loading="loading"
      :total-pages="totalPages"
      :current-page="currentPage"
      @page-change="load"
    >
      <template #row="{ row }">
        <div class="note-row">
          <div class="note-row__main">
            <strong>{{ (row as NotificationItem).message }}</strong>
            <small>{{ new Date((row as NotificationItem).createdAt).toLocaleString() }}</small>
          </div>
          <div class="note-row__actions">
            <StatusBadge
              :value="(row as NotificationItem).isRead ? 'read' : 'unread'"
              :tone="(row as NotificationItem).isRead ? 'positive' : 'neutral'"
            />
            <button class="note-row__btn" @click="archive(row as NotificationItem)">Archive</button>
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
.note-row {
  display: flex;
  justify-content: space-between;
  gap: var(--sp-md);
  padding: 10px 14px;
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
}
.note-row__main { display: flex; flex-direction: column; min-width: 0; }
.note-row__main strong {
  font-family: var(--font-sans);
  font-size: var(--text-body);
  color: var(--text-primary);
}
.note-row__main small {
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  font-size: var(--text-small);
}
.note-row__actions { display: flex; gap: var(--sp-sm); align-items: center; }
.note-row__btn {
  height: 28px;
  padding: 0 var(--sp-md);
  background: var(--surface-base);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: var(--text-small);
  cursor: pointer;
}
.note-row__btn:hover {
  border-color: var(--ac);
  color: var(--ac);
}
</style>
