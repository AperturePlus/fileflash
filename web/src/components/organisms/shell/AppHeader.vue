<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useDebounceFn } from '@vueuse/core';
import { useThemeStore } from '../../../store/theme';
import { useLocaleStore } from '../../../store/locale';
import { eventBus } from '../../../utils/eventBus';
import IconButton from '../../molecules/IconButton.vue';
import SearchField from '../../molecules/SearchField.vue';
import UserMenu from './UserMenu.vue';

defineProps<{
  leftCollapsed: boolean;
  rightVisible: boolean;
}>();

const emit = defineEmits(['toggle-left', 'toggle-right']);

const router = useRouter();
const themeStore = useThemeStore();
const localeStore = useLocaleStore();
const t = localeStore.t;

const searchQuery = ref('');

const dispatchSearch = useDebounceFn((query: string) => {
  eventBus.emit('search-files', { query });
}, 280);

function onSearchInput(value: string) {
  searchQuery.value = value;
  dispatchSearch(value.trim());
}

function goHome() { router.push('/files'); }
</script>

<template>
  <header class="app-header">
    <div class="header-left">
      <IconButton
        :icon="leftCollapsed ? 'chevronRight' : 'menu'"
        :label="leftCollapsed ? t('header.expandSidebar') : t('header.collapseSidebar')"
        variant="ghost"
        @click="emit('toggle-left')"
      />
      <div class="brand" @click="goHome">
        <div class="brand-text">
          <strong>FileFlash</strong>
          <span>{{ t('header.brandSubtitle') }}</span>
        </div>
      </div>
    </div>

    <div class="header-center">
      <SearchField
        v-model="searchQuery"
        :placeholder="t('header.searchPlaceholder')"
        @update:model-value="onSearchInput"
      />
    </div>

    <div class="header-right">
      <IconButton
        :icon="themeStore.theme === 'light' ? 'sun' : 'moon'"
        :label="t('header.toggleTheme')"
        variant="ghost"
        @click="themeStore.toggleTheme"
      />
      <IconButton
        icon="more"
        :label="rightVisible ? t('header.hidePreviewPanel') : t('header.showPreviewPanel')"
        variant="ghost"
        @click="emit('toggle-right')"
      />
      <UserMenu />
    </div>
  </header>
</template>

<style scoped>
.app-header {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  height: var(--layout-header-height);
  padding: 0 var(--sp-lg);
  gap: var(--sp-lg);
  background: var(--surface-raised);
  border-bottom: 1px solid var(--border-default);
  position: relative;
  z-index: 20;
}
.header-left, .header-center, .header-right { display: flex; align-items: center; min-width: 0; gap: var(--sp-md); }
.brand { display: flex; align-items: center; gap: var(--sp-sm); cursor: pointer; padding: 4px 8px; border-radius: var(--radius-sm); transition: background-color var(--mo-duration-fast) var(--mo-easing); }
.brand:hover { background: var(--surface-inset); }
.brand-text { display: flex; flex-direction: column; line-height: 1.1; }
.brand-text strong { font-size: var(--text-body); color: var(--text-primary); }
.brand-text span { font-size: var(--text-label); color: var(--text-dim); }
.header-center { justify-content: center; }
.header-center .ff-searchfield { width: min(560px, 50vw); }
@media (max-width: 980px) { .brand-text { display: none; } .header-center .ff-searchfield { max-width: 360px; } }
@media (max-width: 760px) { .app-header { padding: 0 var(--sp-sm); gap: var(--sp-sm); } }
</style>
