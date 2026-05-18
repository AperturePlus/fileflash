import { computed, ref } from 'vue';
import { acceptSharedItem, deleteShare, getSharedItems, getShares } from '../api/share';
import { useLocaleStore } from '../store/locale';
import { useFileSelection } from './useFileSelection';
import type { Share, SharedItem } from '../types/share';
import { ui } from '../utils/ui';

export type SharedTab = 'received' | 'links';

export function useSharingCenter() {
  const localeStore = useLocaleStore();
  const t = localeStore.t;
  const activeTab = ref<SharedTab>('received');
  const isLoading = ref(false);
  const sharedItems = ref<SharedItem[]>([]);
  const myShares = ref<Share[]>([]);

  const selection = useFileSelection();
  const showBatch = computed(() => selection.selectedCount.value > 0 && activeTab.value === 'received');

  const loadReceived = async () => { sharedItems.value = (await getSharedItems({ page: 1, perPage: 50, sort: 'sharedAt', order: 'desc' })).items; };
  const loadLinks = async () => { myShares.value = (await getShares({ page: 1, perPage: 50 })).items; };

  const loadData = async () => {
    isLoading.value = true;
    try { activeTab.value === 'received' ? await loadReceived() : await loadLinks(); }
    finally { isLoading.value = false; }
  };

  const switchTab = async (tab: SharedTab) => {
    activeTab.value = tab; selection.clear(); await loadData();
  };

  const toggleAll = (next: boolean) => {
    if (next) sharedItems.value.forEach((i) => selection.selectedItems.value.add(i.id));
    else selection.clear();
  };

  const acceptOne = async (item: SharedItem) => {
    try { await acceptSharedItem(item.id); await loadReceived(); }
    catch (e) { console.error('Failed to accept shared item', e); }
  };

  const acceptSelected = async () => {
    if (!selection.selectedItems.value.size) return;
    await Promise.allSettled(Array.from(selection.selectedItems.value).map((id) => acceptSharedItem(id)));
    selection.clear();
    await loadReceived();
  };

  const removeShare = async (share: Share) => {
    const ok = await ui.confirm({
      title: t('sharing.confirm.deleteLink.title'),
      message: t('sharing.confirm.deleteLink.message').replace('{shareLink}', share.shareLink),
      confirmText: t('sharing.confirm.deleteLink.confirm'),
      danger: true,
    });
    if (!ok) return;
    try {
      await deleteShare(share.shareLink);
      myShares.value = myShares.value.filter((e) => e.shareLink !== share.shareLink);
      ui.toast({ type: 'success', message: t('sharing.toast.linkDeleted') });
    } catch (e) {
      console.error('Failed to delete share link', e);
      ui.toast({ type: 'error', message: t('sharing.toast.linkDeleteFailed') });
    }
  };

  const copyShare = async (share: Share) => {
    const link = `${window.location.origin}/share/${share.shareLink}`;
    try {
      await navigator.clipboard.writeText(link);
      ui.toast({ type: 'success', message: t('sharing.toast.linkCopied') });
    } catch {
      await ui.copyText({
        title: t('sharing.copyDialog.title'),
        message: t('sharing.copyDialog.message'),
        text: link,
      });
    }
  };

  return {
    activeTab, isLoading, sharedItems, myShares, selection, showBatch,
    loadData, switchTab, toggleAll, acceptOne, acceptSelected, removeShare, copyShare,
  };
}
