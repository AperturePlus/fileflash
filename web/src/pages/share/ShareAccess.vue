<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { accessShare, downloadSharedFile, getShareDetails, previewSharedFile, saveShare } from '../../api/share';
import SelectFolderDialog from '../../components/common/SelectFolderDialog.vue';
import { useUserStore } from '../../store/user';
import type { AccessShareResponseData, Share } from '../../types/share';

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();

const shareLink = computed(() => String(route.params.shareLink || ''));

const share = ref<Share | null>(null);
const accessData = ref<AccessShareResponseData | null>(null);
const password = ref('');
const error = ref('');
const statusMessage = ref('');

const isLoading = ref(false);
const isAccessing = ref(false);
const isSaving = ref(false);
const isDownloading = ref(false);
const isPreviewing = ref(false);

const isFile = computed(() => share.value?.itemType === 'file');
const isFolder = computed(() => share.value?.itemType === 'folder');
const passwordProtected = computed(() => Boolean(share.value?.settings.passwordProtected));
const canDownload = computed(() => Boolean(accessData.value?.accessUrls.download));
const canPreview = computed(() => Boolean(accessData.value?.accessUrls.preview));

const isSelectFolderVisible = ref(false);

const loadShare = async () => {
  error.value = '';
  statusMessage.value = '';
  isLoading.value = true;

  try {
    share.value = await getShareDetails(shareLink.value);
    if (!share.value.settings.passwordProtected) {
      await requestAccess();
    }
  } catch (err) {
    console.error('Failed to load share', err);
    error.value = 'Unable to load share. The link may be invalid or expired.';
  } finally {
    isLoading.value = false;
  }
};

const requestAccess = async () => {
  if (!share.value) return;

  isAccessing.value = true;
  error.value = '';
  statusMessage.value = '';

  try {
    const data = await accessShare(shareLink.value, {
      ...(password.value.trim() ? { password: password.value.trim() } : {}),
    });
    accessData.value = data;
    statusMessage.value = 'Access granted.';
  } catch (err) {
    console.error('Failed to access share', err);
    error.value = passwordProtected.value ? 'Invalid password or share expired.' : 'Share expired or unavailable.';
  } finally {
    isAccessing.value = false;
  }
};

const handleDownload = async () => {
  if (!accessData.value) return;
  if (!isFile.value || !canDownload.value) return;

  isDownloading.value = true;
  error.value = '';
  statusMessage.value = '';

  try {
    const blob = await downloadSharedFile(shareLink.value, accessData.value.accessToken);
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = share.value?.itemInfo.name || 'download';
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    console.error('Failed to download shared file', err);
    error.value = 'Download failed.';
  } finally {
    isDownloading.value = false;
  }
};

const handlePreview = async () => {
  if (!accessData.value) return;
  if (!isFile.value || !canPreview.value) return;

  isPreviewing.value = true;
  error.value = '';
  statusMessage.value = '';

  try {
    const blob = await previewSharedFile(shareLink.value, accessData.value.accessToken);
    const url = window.URL.createObjectURL(blob);
    window.open(url, '_blank', 'noopener,noreferrer');
    setTimeout(() => window.URL.revokeObjectURL(url), 30_000);
  } catch (err) {
    console.error('Failed to preview shared file', err);
    error.value = 'Preview failed.';
  } finally {
    isPreviewing.value = false;
  }
};

const openSaveDialog = () => {
  if (!accessData.value) {
    statusMessage.value = 'Please access the share first.';
    return;
  }
  if (!userStore.isAuthenticated) {
    router.push({ name: 'Login', query: { redirect: route.fullPath } });
    return;
  }
  isSelectFolderVisible.value = true;
};

const handleSaveConfirm = async (targetFolderId: string) => {
  if (!accessData.value) return;
  isSaving.value = true;
  error.value = '';
  statusMessage.value = '';

  try {
    const resp = await saveShare(shareLink.value, {
      targetFolderId,
      shareAccessToken: accessData.value.accessToken,
    });
    statusMessage.value = `Saved successfully (${resp.itemType}).`;
  } catch (err) {
    console.error('Failed to save share', err);
    error.value = 'Save failed. Please make sure you are logged in and verified.';
  } finally {
    isSaving.value = false;
    isSelectFolderVisible.value = false;
  }
};

onMounted(loadShare);
</script>

<template>
  <section class="share-access-page">
    <header class="header">
      <div>
        <h1>Shared Link</h1>
        <p class="subtitle">Link code: <code>{{ shareLink }}</code></p>
      </div>
    </header>

    <div v-if="isLoading" class="state">Loading...</div>
    <div v-else-if="error" class="state error">{{ error }}</div>

    <template v-else-if="share">
      <div class="card">
        <div class="row">
          <div class="label">Type</div>
          <div class="value">{{ share.itemType }}</div>
        </div>
        <div class="row">
          <div class="label">Name</div>
          <div class="value"><strong>{{ share.itemInfo.name }}</strong></div>
        </div>
        <div class="row">
          <div class="label">Size</div>
          <div class="value">{{ share.itemInfo.size }} bytes</div>
        </div>
        <div class="row">
          <div class="label">Expires</div>
          <div class="value">{{ share.settings.expireAt ? share.settings.expireAt : 'Never' }}</div>
        </div>
        <div class="row">
          <div class="label">Password</div>
          <div class="value">{{ share.settings.passwordProtected ? 'Required' : 'Not required' }}</div>
        </div>
      </div>

      <div class="card">
        <h3>Access</h3>
        <div v-if="passwordProtected" class="password-form">
          <input v-model="password" type="password" placeholder="Enter password" />
          <button class="primary" :disabled="isAccessing" @click="requestAccess">
            {{ isAccessing ? 'Checking...' : 'Unlock' }}
          </button>
        </div>
        <div v-else class="actions">
          <button class="primary" :disabled="isAccessing" @click="requestAccess">
            {{ isAccessing ? 'Accessing...' : 'Get Access' }}
          </button>
        </div>

        <p v-if="statusMessage" class="hint">{{ statusMessage }}</p>
      </div>

      <div v-if="accessData" class="card">
        <h3>Actions</h3>
        <div class="actions">
          <button v-if="isFile" class="secondary" :disabled="!canPreview || isPreviewing" @click="handlePreview">
            {{ isPreviewing ? 'Loading...' : 'Preview' }}
          </button>
          <button v-if="isFile" class="secondary" :disabled="!canDownload || isDownloading" @click="handleDownload">
            {{ isDownloading ? 'Downloading...' : 'Download' }}
          </button>
          <button class="primary" :disabled="isSaving" @click="openSaveDialog">
            {{ isSaving ? 'Saving...' : isFolder ? 'Save Folder to My Space' : 'Save to My Space' }}
          </button>
        </div>
      </div>

      <SelectFolderDialog
        :is-visible="isSelectFolderVisible"
        title="Save to My Space"
        confirm-text="Save Here"
        @close="isSelectFolderVisible = false"
        @confirm="handleSaveConfirm"
      />
    </template>
  </section>
</template>

<style scoped>
.share-access-page {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  height: 100%;
}

.header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--spacing-md);
  flex-wrap: wrap;
}

.subtitle {
  margin: 6px 0 0;
  color: var(--color-text-secondary);
}

.state {
  min-height: 260px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-tertiary);
  border: 1px dashed var(--color-border);
  border-radius: var(--border-radius-md);
  background-color: var(--color-bg-secondary);
}

.state.error {
  color: var(--color-danger-dark);
  border-color: #fca5a5;
  background-color: var(--color-danger-light);
}

.card {
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius-md);
  background-color: var(--color-bg-secondary);
  padding: var(--spacing-md);
}

.row {
  display: grid;
  grid-template-columns: 90px 1fr;
  gap: 10px;
  padding: 8px 0;
}

.row + .row {
  border-top: 1px solid var(--color-divider);
}

.label {
  color: var(--color-text-tertiary);
  font-size: 12px;
}

.value {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.password-form {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  margin-top: 10px;
}

.password-form input {
  height: 38px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  background-color: var(--color-bg-primary);
  padding: 0 12px;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 10px;
}

button.primary,
button.secondary {
  height: 38px;
  border-radius: 10px;
  border: 1px solid transparent;
  padding: 0 14px;
  cursor: pointer;
}

button.primary {
  background-color: var(--color-primary);
  color: var(--color-text-on-primary);
}

button.secondary {
  background-color: var(--color-bg-primary);
  border-color: var(--color-border);
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.hint {
  margin-top: 10px;
  color: var(--color-text-secondary);
  font-size: 12px;
}

code {
  background-color: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  padding: 2px 6px;
  border-radius: 6px;
}
</style>

