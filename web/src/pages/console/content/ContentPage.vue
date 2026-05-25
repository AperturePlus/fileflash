<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import {
  getAdminFileDetail,
  getAdminFiles,
  getAdminPreviewUrl,
  previewAdminFile,
  rescanAdminFile,
} from '../../../api/file';
import { AdminTable, FilterBar, StatusBadge } from '../../../components/console';
import FilePreviewDialog from '../../../components/organisms/files/FilePreviewDialog.vue';
import { ui } from '../../../utils/ui';
import type { AdminFileAuditDetail, AdminFileAuditItem, FileItem } from '../../../types/file';

const items = ref<AdminFileAuditItem[]>([]);
const totalPages = ref(1);
const currentPage = ref(1);
const search = ref('');
const status = ref<'all' | 'clean' | 'pending' | 'flagged'>('all');
const loading = ref(false);
const detailLoading = ref(false);
const selected = ref<AdminFileAuditDetail | null>(null);
const selectedId = ref<string | null>(null);
const previewTarget = ref<FileItem | null>(null);

function fmt(b: number) {
  const u = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = b ? Math.floor(Math.log(b) / Math.log(1024)) : 0;
  return `${(b / Math.pow(1024, i)).toFixed(i ? 1 : 0)} ${u[i]}`;
}

function formatDate(value?: string | null) {
  if (!value) return '--';
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

const toneFor = (s: AdminFileAuditItem['virusStatus']) =>
  s === 'clean' ? 'positive' : s === 'flagged' ? 'danger' : 'warning';

const selectedMeta = computed(() => {
  if (!selected.value) return [];
  return [
    ['Object', selected.value.objectId],
    ['Hash', selected.value.objectHash || selected.value.hash],
    ['Algorithm', selected.value.hashAlgorithm],
    ['Storage', selected.value.storageStatus],
    ['Scanned', formatDate(selected.value.scannedAt)],
  ];
});

function toPreviewFile(file: AdminFileAuditItem | AdminFileAuditDetail): FileItem {
  return {
    itemType: 'file',
    id: file.id,
    name: file.name,
    size: file.size,
    mimeType: file.mimeType,
    ownerName: file.ownerName,
    updatedAt: file.updatedAt,
    createdAt: file.createdAt,
    folderId: 'admin-audit',
    permission: 'read',
  };
}

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
    if (selectedId.value && !items.value.some((item) => item.id === selectedId.value)) {
      selected.value = null;
      selectedId.value = null;
    }
  } finally {
    loading.value = false;
  }
}

async function selectFile(file: AdminFileAuditItem) {
  selectedId.value = file.id;
  detailLoading.value = true;
  try {
    selected.value = await getAdminFileDetail(file.id);
  } finally {
    detailLoading.value = false;
  }
}

async function rescan(file: AdminFileAuditItem | AdminFileAuditDetail) {
  const result = await rescanAdminFile(file.id);
  file.virusStatus = result.virusStatus;
  file.scannedAt = result.scannedAt;
  const listItem = items.value.find((item) => item.id === file.id);
  if (listItem) {
    listItem.virusStatus = result.virusStatus;
    listItem.scannedAt = result.scannedAt;
  }
  if (selectedId.value === file.id) {
    selected.value = await getAdminFileDetail(file.id);
  }
  ui.toast({ type: 'info', message: `Rescan requested for ${file.name}` });
}

function openPreview(file: AdminFileAuditItem | AdminFileAuditDetail) {
  previewTarget.value = toPreviewFile(file);
}

onMounted(() => load(1));
</script>

<template>
  <section class="page">
    <header class="page__header">
      <h1>Content Audit</h1>
    </header>

    <FilterBar @change="load(1)">
      <input v-model="search" type="text" placeholder="Search file name" />
      <select v-model="status">
        <option value="all">All status</option>
        <option value="clean">Clean</option>
        <option value="pending">Pending</option>
        <option value="flagged">Flagged</option>
      </select>
    </FilterBar>

    <div class="audit-grid">
      <AdminTable
        :items="items"
        :loading="loading"
        :total-pages="totalPages"
        :current-page="currentPage"
        @page-change="load"
      >
        <template #row="{ row }">
          <div
            class="row"
            :class="{ 'is-selected': selectedId === (row as AdminFileAuditItem).id }"
            role="button"
            tabindex="0"
            @click="selectFile(row as AdminFileAuditItem)"
            @keydown.enter="selectFile(row as AdminFileAuditItem)"
          >
            <div class="row__main">
              <strong>{{ (row as AdminFileAuditItem).name }}</strong>
              <small>
                {{ (row as AdminFileAuditItem).mimeType }} ·
                {{ fmt((row as AdminFileAuditItem).size) }} ·
                {{ (row as AdminFileAuditItem).hash }}
              </small>
              <span class="row__counts">
                {{ (row as AdminFileAuditItem).uploadCount }} uploads ·
                {{ (row as AdminFileAuditItem).ownerCount }} owners
              </span>
            </div>
            <div class="row__actions">
              <StatusBadge
                :value="(row as AdminFileAuditItem).virusStatus"
                :tone="toneFor((row as AdminFileAuditItem).virusStatus)"
              />
              <button class="row__btn" @click.stop="openPreview(row as AdminFileAuditItem)">Preview</button>
              <button class="row__btn" @click.stop="rescan(row as AdminFileAuditItem)">Rescan</button>
            </div>
          </div>
        </template>
      </AdminTable>

      <aside class="detail" aria-label="Selected file audit detail">
        <div v-if="detailLoading" class="detail__empty">Loading detail...</div>
        <div v-else-if="!selected" class="detail__empty">Select a file to inspect ownership and preview content.</div>
        <template v-else>
          <header class="detail__header">
            <div class="detail__title">
              <h2>{{ selected.name }}</h2>
              <p>{{ selected.mimeType }} · {{ fmt(selected.size) }}</p>
            </div>
            <StatusBadge :value="selected.virusStatus" :tone="toneFor(selected.virusStatus)" />
          </header>

          <div class="detail__stats">
            <div>
              <strong>{{ selected.uploadCount }}</strong>
              <span>Uploads</span>
            </div>
            <div>
              <strong>{{ selected.ownerCount }}</strong>
              <span>Owners</span>
            </div>
            <div>
              <strong>{{ selected.isShared ? 'Yes' : 'No' }}</strong>
              <span>Shared</span>
            </div>
          </div>

          <div class="detail__actions">
            <button class="row__btn" @click="openPreview(selected)">Preview</button>
            <button class="row__btn" @click="rescan(selected)">Rescan</button>
          </div>

          <dl class="detail__meta">
            <template v-for="[label, value] in selectedMeta" :key="label">
              <dt>{{ label }}</dt>
              <dd>{{ value }}</dd>
            </template>
          </dl>

          <section class="owners">
            <h3>Owners</h3>
            <div class="owners__table">
              <div class="owners__head">
                <span>User</span>
                <span>Files</span>
                <span>Last upload</span>
              </div>
              <div v-for="owner in selected.owners" :key="owner.userId" class="owners__row">
                <span>
                  <strong>{{ owner.username }}</strong>
                  <small>{{ owner.email }}</small>
                </span>
                <span>{{ owner.fileCount }}</span>
                <span>{{ formatDate(owner.lastUploadedAt) }}</span>
              </div>
            </div>
          </section>
        </template>
      </aside>
    </div>

    <FilePreviewDialog
      :file="previewTarget"
      :preview-loader="previewAdminFile"
      :preview-url-loader="getAdminPreviewUrl"
      :show-download="false"
      @close="previewTarget = null"
    />
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
.audit-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(320px, 0.8fr);
  gap: var(--sp-lg);
  align-items: start;
}
.row {
  display: flex;
  justify-content: space-between;
  gap: var(--sp-md);
  padding: 10px 14px;
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
  cursor: pointer;
}
.row:hover,
.row.is-selected {
  border-color: var(--ac);
}
.row__main {
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 2px;
}
.row__main strong {
  font-family: var(--font-sans);
  font-size: var(--text-body);
  color: var(--text-primary);
  word-break: break-word;
}
.row__main small,
.row__counts {
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  font-size: var(--text-small);
  word-break: break-word;
}
.row__actions {
  display: flex;
  gap: var(--sp-sm);
  align-items: center;
  flex-shrink: 0;
}
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
.detail {
  position: sticky;
  top: var(--sp-lg);
  display: flex;
  flex-direction: column;
  gap: var(--sp-md);
  min-height: 320px;
  padding: var(--sp-lg);
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
}
.detail__empty {
  min-height: 260px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  font-size: var(--text-small);
  text-align: center;
}
.detail__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sp-md);
}
.detail__title {
  min-width: 0;
}
.detail__title h2 {
  margin: 0;
  color: var(--text-primary);
  font-size: var(--text-h2);
  line-height: var(--leading-snug);
  word-break: break-word;
}
.detail__title p {
  margin: 4px 0 0;
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  font-size: var(--text-small);
  word-break: break-word;
}
.detail__stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  border: 1px solid var(--border-default);
  background: var(--surface-base);
}
.detail__stats div {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: var(--sp-md);
  border-right: 1px solid var(--border-default);
}
.detail__stats div:last-child {
  border-right: 0;
}
.detail__stats strong {
  color: var(--text-primary);
  font-size: var(--text-h2);
}
.detail__stats span {
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  font-size: var(--text-small);
}
.detail__actions {
  display: flex;
  gap: var(--sp-sm);
}
.detail__meta {
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr);
  gap: 8px var(--sp-sm);
  margin: 0;
  padding: var(--sp-md) 0;
  border-top: 1px solid var(--border-subtle);
  border-bottom: 1px solid var(--border-subtle);
}
.detail__meta dt {
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  font-size: var(--text-small);
}
.detail__meta dd {
  min-width: 0;
  margin: 0;
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: var(--text-small);
  word-break: break-word;
}
.owners {
  display: flex;
  flex-direction: column;
  gap: var(--sp-sm);
}
.owners h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: var(--text-body);
}
.owners__table {
  border: 1px solid var(--border-default);
  background: var(--surface-base);
}
.owners__head,
.owners__row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 64px 128px;
  gap: var(--sp-sm);
  align-items: center;
  padding: 8px var(--sp-sm);
}
.owners__head {
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  font-size: var(--text-small);
  border-bottom: 1px solid var(--border-default);
}
.owners__row {
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: var(--text-small);
  border-bottom: 1px solid var(--border-subtle);
}
.owners__row:last-child {
  border-bottom: 0;
}
.owners__row span:first-child {
  display: flex;
  min-width: 0;
  flex-direction: column;
}
.owners__row strong,
.owners__row small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.owners__row strong {
  color: var(--text-primary);
}
.owners__row small {
  color: var(--text-tertiary);
}
@media (max-width: 980px) {
  .audit-grid {
    grid-template-columns: 1fr;
  }
  .detail {
    position: static;
  }
}
@media (max-width: 720px) {
  .row,
  .row__actions {
    align-items: flex-start;
    flex-direction: column;
  }
  .detail__stats {
    grid-template-columns: 1fr;
  }
  .detail__stats div {
    border-right: 0;
    border-bottom: 1px solid var(--border-default);
  }
  .detail__stats div:last-child {
    border-bottom: 0;
  }
  .owners__head,
  .owners__row {
    grid-template-columns: minmax(0, 1fr) 48px 104px;
  }
}
</style>
