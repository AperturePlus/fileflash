<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import SelectFolderDialog from '../../components/common/SelectFolderDialog.vue';
import { Text } from '../../components/atoms';
import { EmptyState } from '../../components/organisms/files';
import { ShareInfoCard, ShareAccessPanel, ShareActionsPanel } from '../../components/organisms/share';
import { useShareAccess } from '../../composables/useShareAccess';
import { useLocaleStore } from '../../store/locale';
import { useUserStore } from '../../store/user';

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
const localeStore = useLocaleStore();
const t = localeStore.t;
const shareLink = computed(() => String(route.params.shareLink || ''));

const s = useShareAccess(shareLink);
const isSelectFolderVisible = ref(false);

const openSaveDialog = () => {
  if (!s.accessData.value) { s.statusMessage.value = t('share.page.needAccessFirst'); return; }
  if (!userStore.isAuthenticated) { router.push({ name: 'Login', query: { redirect: route.fullPath } }); return; }
  isSelectFolderVisible.value = true;
};

const handleSaveConfirm = async (targetFolderId: string) => {
  await s.saveToFolder(targetFolderId);
  isSelectFolderVisible.value = false;
};

onMounted(s.loadShare);
</script>

<template>
  <section class="page">
    <header class="page__header">
      <Text variant="h1" as="h1">{{ t('share.page.title') }}</Text>
      <Text variant="small" as="p">{{ t('share.page.linkCode') }} <code>{{ shareLink }}</code></Text>
    </header>

    <EmptyState v-if="s.isLoading.value" variant="loading" />
    <EmptyState v-else-if="s.error.value" variant="error" :message="s.error.value" />

    <template v-else-if="s.share.value">
      <ShareInfoCard :share="s.share.value" />
      <ShareAccessPanel
        :password-protected="s.passwordProtected.value"
        :password="s.password.value"
        :is-accessing="s.isAccessing.value"
        :status-message="s.statusMessage.value"
        @update:password="s.password.value = $event"
        @request-access="s.requestAccess"
      />
      <ShareActionsPanel
        v-if="s.accessData.value"
        :is-file="s.isFile.value" :is-folder="s.isFolder.value"
        :can-preview="s.canPreview.value" :can-download="s.canDownload.value"
        :is-previewing="s.isPreviewing.value" :is-downloading="s.isDownloading.value" :is-saving="s.isSaving.value"
        @preview="s.handlePreview" @download="s.handleDownload" @save="openSaveDialog"
      />

      <SelectFolderDialog
        :is-visible="isSelectFolderVisible"
        :title="t('share.page.saveDialogTitle')"
        :confirm-text="t('share.page.saveDialogConfirm')"
        @close="isSelectFolderVisible = false"
        @confirm="handleSaveConfirm"
      />
    </template>
  </section>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; height: 100%; min-height: 0; }
.page__header { display: flex; flex-direction: column; gap: 4px; }
code {
  font-family: var(--font-mono);
  font-size: var(--text-data);
  background: var(--surface-inset);
  border: 1px solid var(--border-default);
  padding: 2px 6px;
  color: var(--text-primary);
}
</style>
