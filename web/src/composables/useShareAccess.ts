import { computed, ref, type Ref } from 'vue';
import { accessShare, downloadSharedFile, getShareDetails, previewSharedFile, saveShare } from '../api/share';
import { useLocaleStore } from '../store/locale';
import type { AccessShareResponseData, Share } from '../types/share';

export function useShareAccess(shareLink: Ref<string>) {
  const localeStore = useLocaleStore();
  const t = localeStore.t;

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

  const loadShare = async () => {
    error.value = ''; statusMessage.value = ''; isLoading.value = true;
    try {
      share.value = await getShareDetails(shareLink.value);
      if (!share.value.settings.passwordProtected) await requestAccess();
    } catch (e) {
      console.error('Failed to load share', e);
      error.value = t('share.status.loadFailed');
    }
    finally { isLoading.value = false; }
  };

  const requestAccess = async () => {
    if (!share.value) return;
    isAccessing.value = true; error.value = ''; statusMessage.value = '';
    try {
      accessData.value = await accessShare(shareLink.value, password.value.trim() ? { password: password.value.trim() } : {});
      statusMessage.value = t('share.status.accessGranted');
    } catch (e) {
      console.error('Failed to access share', e);
      error.value = passwordProtected.value ? t('share.status.invalidPasswordOrExpired') : t('share.status.expiredOrUnavailable');
    }
    finally { isAccessing.value = false; }
  };

  const handleDownload = async () => {
    if (!accessData.value || !isFile.value || !canDownload.value) return;
    isDownloading.value = true; error.value = ''; statusMessage.value = '';
    try {
      const blob = await downloadSharedFile(shareLink.value, accessData.value.accessToken);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = share.value?.itemInfo.name || 'download';
      document.body.appendChild(a); a.click(); a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      console.error('Failed to download shared file', e);
      error.value = t('share.status.downloadFailed');
    }
    finally { isDownloading.value = false; }
  };

  const handlePreview = async () => {
    if (!accessData.value || !isFile.value || !canPreview.value) return;
    isPreviewing.value = true; error.value = ''; statusMessage.value = '';
    try {
      const blob = await previewSharedFile(shareLink.value, accessData.value.accessToken);
      const url = window.URL.createObjectURL(blob);
      window.open(url, '_blank', 'noopener,noreferrer');
      setTimeout(() => window.URL.revokeObjectURL(url), 30_000);
    } catch (e) {
      console.error('Failed to preview shared file', e);
      error.value = t('share.status.previewFailed');
    }
    finally { isPreviewing.value = false; }
  };

  const saveToFolder = async (targetFolderId: string) => {
    if (!accessData.value) return;
    isSaving.value = true; error.value = ''; statusMessage.value = '';
    try {
      const resp = await saveShare(shareLink.value, { targetFolderId, shareAccessToken: accessData.value.accessToken });
      const itemTypeLabel = resp.itemType === 'folder' ? t('share.itemType.folder') : t('share.itemType.file');
      statusMessage.value = t('share.status.savedSuccess').replace('{itemType}', itemTypeLabel);
    } catch (e) {
      console.error('Failed to save share', e);
      error.value = t('share.status.saveFailed');
    }
    finally { isSaving.value = false; }
  };

  return {
    share, accessData, password, error, statusMessage,
    isLoading, isAccessing, isSaving, isDownloading, isPreviewing,
    isFile, isFolder, passwordProtected, canDownload, canPreview,
    loadShare, requestAccess, handleDownload, handlePreview, saveToFolder,
  };
}
