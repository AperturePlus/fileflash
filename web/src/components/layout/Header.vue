<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useDebounceFn } from '@vueuse/core';
import { useThemeStore } from '../../store/theme';
import { useUserStore } from '../../store/user';
import { eventBus } from '../../utils/eventBus';
import DropdownMenu from '../common/DropdownMenu.vue';
import logoLight from '../../assets/logo/icon_white.png';
import logoDark from '../../assets/logo/icon_dark.png';

const themeStore = useThemeStore();
const userStore = useUserStore();
const router = useRouter();
const searchQuery = ref('');

defineProps<{
  leftSidebarCollapsed: boolean;
  rightSidebarVisible: boolean;
}>();

const emit = defineEmits(['toggle-left-sidebar', 'toggle-right-sidebar']);

const handleLogout = () => {
  userStore.logout();
  router.push('/login');
};

const dispatchSearch = useDebounceFn((query: string) => {
  eventBus.emit('search-files', { query });
}, 280);

const handleSearchInput = (event: Event) => {
  const value = (event.target as HTMLInputElement).value.trim();
  dispatchSearch(value);
};
</script>

<template>
  <header class="app-header">
    <div class="header-left">
      <button
        class="icon-btn"
        :aria-label="leftSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
        @click="$emit('toggle-left-sidebar')"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M3 6h18M3 12h18M3 18h18" />
        </svg>
      </button>

      <div class="brand" @click="router.push('/files')">
        <img :src="themeStore.theme === 'light' ? logoLight : logoDark" alt="FileFlash" class="brand-logo" />
        <div class="brand-text">
          <strong>FileFlash</strong>
          <span>Cloud Workspace</span>
        </div>
      </div>
    </div>

    <div class="header-center">
      <div class="search-box">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M11 4a7 7 0 1 0 4.9 12l4.6 4.6l1.4-1.4l-4.6-4.6A7 7 0 0 0 11 4" />
        </svg>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search files, folders, and shared content"
          @input="handleSearchInput"
        />
      </div>
    </div>

    <div class="header-right">
      <button class="icon-btn" aria-label="Toggle theme" @click="themeStore.toggleTheme">
        <svg v-if="themeStore.theme === 'light'" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 5V2m0 20v-3m7-7h3M2 12h3m11.3 4.3l2.1 2.1M5.6 5.6l2.1 2.1m8.6 0l2.1-2.1m-12.8 12.8l2.1-2.1M12 8a4 4 0 1 0 0 8a4 4 0 0 0 0-8" />
        </svg>
        <svg v-else viewBox="0 0 24 24" aria-hidden="true">
          <path d="M21 13a8 8 0 1 1-10-10a7 7 0 0 0 10 10" />
        </svg>
      </button>

      <button
        class="icon-btn"
        :aria-label="rightSidebarVisible ? 'Hide preview panel' : 'Show preview panel'"
        @click="$emit('toggle-right-sidebar')"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M4 4h16v16H4zM14 4v16" />
        </svg>
      </button>

      <DropdownMenu>
        <template #trigger>
          <button class="profile-trigger" aria-label="User menu">
            <img src="../../assets/generic/user.svg" alt="User avatar" class="avatar" />
            <span class="name">{{ userStore.user?.username || 'User' }}</span>
          </button>
        </template>
        <template #content>
          <div class="menu">
            <div class="menu-header">
              <strong>{{ userStore.user?.username || 'User' }}</strong>
              <small>{{ userStore.user?.email || 'user@example.com' }}</small>
            </div>
            <router-link class="menu-item" to="/profile">Profile</router-link>
            <router-link class="menu-item" to="/settings">Settings</router-link>
            <router-link class="menu-item" to="/dashboard">Dashboard</router-link>
            <button class="menu-item danger" @click="handleLogout">Log out</button>
          </div>
        </template>
      </DropdownMenu>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  height: var(--layout-header-height);
  padding: 0 var(--spacing-lg);
  gap: var(--spacing-lg);
  background: linear-gradient(180deg, var(--color-bg-primary), var(--color-bg-secondary));
  border-bottom: 1px solid var(--color-border);
  backdrop-filter: blur(8px);
  position: relative;
  z-index: 20;
}

.header-left,
.header-center,
.header-right {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: var(--spacing-md);
}

.brand {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  cursor: pointer;
  padding: 4px 8px;
  border-radius: var(--border-radius-md);
  transition: background-color 0.2s ease;
}

.brand:hover {
  background-color: var(--color-bg-tertiary);
}

.brand-logo {
  width: 38px;
  height: 38px;
  border-radius: 8px;
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.1;
}

.brand-text strong {
  font-size: 14px;
  color: var(--color-text-primary);
}

.brand-text span {
  font-size: 11px;
  color: var(--color-text-tertiary);
}

.search-box {
  width: min(760px, 100%);
  height: 42px;
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  background-color: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: 999px;
  padding: 0 14px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.search-box:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(var(--color-primary-rgb), 0.15);
}

.search-box svg {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  color: var(--color-text-tertiary);
  flex-shrink: 0;
}

.search-box input {
  width: 100%;
  border: none;
  outline: none;
  background: transparent;
  color: var(--color-text-primary);
}

.icon-btn {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  border: 1px solid transparent;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: var(--transition-base);
}

.icon-btn:hover {
  border-color: var(--color-border);
  background-color: var(--color-bg-tertiary);
  color: var(--color-text-primary);
}

.icon-btn svg {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
}

.profile-trigger {
  height: 38px;
  max-width: 180px;
  border-radius: 999px;
  border: 1px solid var(--color-border);
  background-color: var(--color-bg-primary);
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 0 12px 0 6px;
  cursor: pointer;
}

.profile-trigger .avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
}

.profile-trigger .name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--color-text-secondary);
}

.menu {
  width: 230px;
  padding: 8px;
  background-color: var(--color-bg-primary);
  border-radius: var(--border-radius-md);
}

.menu-header {
  padding: 8px 10px;
  margin-bottom: 6px;
  border-radius: var(--border-radius-sm);
  background-color: var(--color-bg-tertiary);
  display: flex;
  flex-direction: column;
}

.menu-header strong {
  font-size: 13px;
}

.menu-header small {
  color: var(--color-text-tertiary);
}

.menu-item {
  width: 100%;
  height: 36px;
  border-radius: var(--border-radius-sm);
  border: none;
  background: transparent;
  text-align: left;
  color: var(--color-text-secondary);
  padding: 0 10px;
  display: flex;
  align-items: center;
  cursor: pointer;
}

.menu-item:hover {
  background-color: var(--color-bg-tertiary);
}

.menu-item.danger {
  color: var(--color-danger);
}

@media (max-width: 980px) {
  .brand-text {
    display: none;
  }

  .search-box {
    max-width: 460px;
  }
}

@media (max-width: 760px) {
  .app-header {
    grid-template-columns: auto 1fr auto;
    gap: var(--spacing-sm);
    padding: 0 var(--spacing-sm);
  }

  .search-box {
    height: 38px;
  }

  .profile-trigger .name {
    display: none;
  }
}
</style>
