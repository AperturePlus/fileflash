<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { deleteShare, getShares } from '../../api/share';
import { getLogs } from '../../api/log';
import { broadcastNotification, getNotifications } from '../../api/notification';
import { getStorageSummary, getUsageTrend } from '../../api/storage';
import { getAdminUsers, getViolations, resolveViolation, updateUserStatus } from '../../api/user';
import type { StorageStats } from '../../types/user';
import type { Share } from '../../types/share';
import type { LogItem } from '../../types/log';
import type { NotificationItem } from '../../types/notification';

const isLoading = ref(false);

const storageSummary = ref<StorageStats | null>(null);
const usageTrend = ref<Array<{ date: string; used: number }>>([]);

const adminUsers = ref<any[]>([]);
const logs = ref<LogItem[]>([]);
const shares = ref<Share[]>([]);
const violations = ref<any[]>([]);
const notifications = ref<NotificationItem[]>([]);

const noticeText = ref('');

const formatBytes = (bytes: number) => {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
};

const loadDashboardData = async () => {
  isLoading.value = true;

  try {
    const [summary, trend, users, logRes, shareRes, violationRes, notificationRes] = await Promise.all([
      getStorageSummary(),
      getUsageTrend({ days: 7 }),
      getAdminUsers({ page: 1, perPage: 8 }),
      getLogs({ page: 1, perPage: 8 }),
      getShares({ page: 1, perPage: 8 }),
      getViolations(),
      getNotifications({ page: 1, perPage: 8 }),
    ]);

    storageSummary.value = summary;
    usageTrend.value = trend.trends;
    adminUsers.value = users.items;
    logs.value = logRes.logs;
    shares.value = shareRes.items;
    violations.value = violationRes.items;
    notifications.value = notificationRes.items;
  } finally {
    isLoading.value = false;
  }
};

const handleUpdateUserStatus = async (user: any, status: 'active' | 'suspended') => {
  await updateUserStatus(user.userId, status);
  user.status = status;
};

const handleResolveViolation = async (violationId: string) => {
  await resolveViolation(violationId);
  violations.value = violations.value.filter((item) => item.id !== violationId);
};

const handleDeleteShare = async (share: Share) => {
  await deleteShare(share.shareLink);
  shares.value = shares.value.filter((item) => item.shareId !== share.shareId);
};

const sendNotice = async () => {
  if (!noticeText.value.trim()) return;
  await broadcastNotification(noticeText.value.trim());
  noticeText.value = '';
  const latest = await getNotifications({ page: 1, perPage: 8 });
  notifications.value = latest.items;
};

onMounted(loadDashboardData);
</script>

<template>
  <section class="dashboard-page">
    <header class="page-header">
      <div>
        <h1>Admin Dashboard</h1>
        <p>Monitor storage, users, shares, logs, violations and notices in one place.</p>
      </div>
      <button class="refresh-btn" @click="loadDashboardData" :disabled="isLoading">
        {{ isLoading ? 'Refreshing...' : 'Refresh' }}
      </button>
    </header>

    <div class="metrics" v-if="storageSummary">
      <article class="metric-card">
        <h3>Total Storage</h3>
        <strong>{{ formatBytes(storageSummary.storageUsed) }}</strong>
        <small>/ {{ formatBytes(storageSummary.storageLimit) }}</small>
      </article>
      <article class="metric-card">
        <h3>Files</h3>
        <strong>{{ storageSummary.fileCount }}</strong>
      </article>
      <article class="metric-card">
        <h3>Folders</h3>
        <strong>{{ storageSummary.folderCount }}</strong>
      </article>
      <article class="metric-card">
        <h3>Usage</h3>
        <strong>{{ Math.round(storageSummary.storagePercentage) }}%</strong>
      </article>
    </div>

    <div class="trend-card" v-if="usageTrend.length">
      <h3>7-Day Storage Trend</h3>
      <div class="trend-bars">
        <div v-for="point in usageTrend" :key="point.date" class="bar-item">
          <div class="bar-track"><div class="bar-fill" :style="{ height: `${Math.max(6, (point.used / (usageTrend[usageTrend.length - 1].used || 1)) * 100)}%` }" /></div>
          <small>{{ point.date.slice(5) }}</small>
        </div>
      </div>
    </div>

    <div class="grid">
      <article class="card">
        <h3>User Management</h3>
        <div class="table-list">
          <div v-for="user in adminUsers" :key="user.userId" class="table-row">
            <div>
              <strong>{{ user.username }}</strong>
              <small>{{ user.email }}</small>
            </div>
            <button
              class="status-btn"
              :class="{ suspended: user.status === 'suspended' }"
              @click="handleUpdateUserStatus(user, user.status === 'active' ? 'suspended' : 'active')"
            >
              {{ user.status === 'active' ? 'Suspend' : 'Activate' }}
            </button>
          </div>
        </div>
      </article>

      <article class="card">
        <h3>Recent Logs</h3>
        <div class="table-list">
          <div v-for="log in logs" :key="log.id" class="table-row">
            <div>
              <strong>{{ log.operationName }}</strong>
              <small>{{ new Date(log.performedAt).toLocaleString() }}</small>
            </div>
            <span class="muted">{{ log.ipAddress }}</span>
          </div>
        </div>
      </article>

      <article class="card">
        <h3>Share Links</h3>
        <div class="table-list">
          <div v-for="share in shares" :key="share.shareId" class="table-row">
            <div>
              <strong>{{ share.itemInfo.name }}</strong>
              <small>{{ share.shareLink }}</small>
            </div>
            <button class="danger-btn" @click="handleDeleteShare(share)">Delete</button>
          </div>
        </div>
      </article>

      <article class="card">
        <h3>Violation Queue</h3>
        <div class="table-list">
          <div v-for="item in violations" :key="item.id" class="table-row">
            <div>
              <strong>{{ item.fileName }}</strong>
              <small>{{ item.type }} · {{ item.level }}</small>
            </div>
            <button class="status-btn" @click="handleResolveViolation(item.id)">Resolve</button>
          </div>
        </div>
      </article>

      <article class="card span-2">
        <h3>Send Notification</h3>
        <div class="notice-form">
          <textarea v-model="noticeText" placeholder="Enter a system notification for users" rows="3" />
          <button class="refresh-btn" @click="sendNotice">Send</button>
        </div>
        <div class="table-list">
          <div v-for="notice in notifications" :key="notice.id" class="table-row">
            <div>
              <strong>{{ notice.message }}</strong>
              <small>{{ new Date(notice.createdAt).toLocaleString() }}</small>
            </div>
            <span class="badge" :class="{ read: notice.isRead }">{{ notice.isRead ? 'Read' : 'Unread' }}</span>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.dashboard-page {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-md);
  flex-wrap: wrap;
}

.page-header p {
  margin: 4px 0 0;
  color: var(--color-text-secondary);
}

.refresh-btn,
.status-btn,
.danger-btn {
  height: 34px;
  border-radius: 8px;
  border: 1px solid transparent;
  padding: 0 12px;
  cursor: pointer;
}

.refresh-btn,
.status-btn {
  background-color: var(--color-bg-primary);
  border-color: var(--color-border);
}

.danger-btn,
.status-btn.suspended {
  background-color: var(--color-danger-light);
  border-color: #fca5a5;
  color: var(--color-danger-dark);
}

.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--spacing-sm);
}

.metric-card {
  border: 1px solid var(--color-border);
  border-radius: 10px;
  background-color: var(--color-bg-secondary);
  padding: 12px;
}

.metric-card h3 {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--color-text-tertiary);
}

.metric-card strong {
  font-size: 24px;
}

.metric-card small {
  color: var(--color-text-tertiary);
}

.trend-card {
  border: 1px solid var(--color-border);
  border-radius: 10px;
  background-color: var(--color-bg-secondary);
  padding: 12px;
}

.trend-card h3 {
  margin-bottom: 10px;
}

.trend-bars {
  height: 140px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(56px, 1fr));
  gap: 8px;
}

.bar-item {
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: center;
  gap: 6px;
}

.bar-track {
  width: 28px;
  height: 100%;
  border-radius: 999px;
  background-color: var(--color-bg-tertiary);
  display: flex;
  align-items: flex-end;
  overflow: hidden;
}

.bar-fill {
  width: 100%;
  border-radius: inherit;
  background: linear-gradient(180deg, #4ea8ff, var(--color-primary));
}

.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--spacing-sm);
}

.card {
  border: 1px solid var(--color-border);
  border-radius: 10px;
  background-color: var(--color-bg-secondary);
  padding: 12px;
}

.card h3 {
  margin: 0 0 10px;
}

.span-2 {
  grid-column: span 2;
}

.table-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.table-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background-color: var(--color-bg-primary);
  padding: 8px;
}

.table-row > div {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.table-row strong,
.table-row small,
.table-row span,
.table-row code {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.table-row small,
.muted {
  color: var(--color-text-tertiary);
}

.notice-form {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
}

.notice-form textarea {
  flex: 1;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background-color: var(--color-bg-primary);
  padding: 8px;
  resize: vertical;
  min-height: 72px;
}

.badge {
  font-size: 12px;
  padding: 3px 8px;
  border-radius: 999px;
  background-color: #fde68a;
}

.badge.read {
  background-color: #bbf7d0;
}

@media (max-width: 980px) {
  .grid {
    grid-template-columns: 1fr;
  }

  .span-2 {
    grid-column: span 1;
  }

  .notice-form {
    flex-direction: column;
  }
}
</style>
