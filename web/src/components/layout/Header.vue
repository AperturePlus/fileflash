<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useThemeStore } from '../../store/theme';
import { useUserStore } from '../../store/user';
import DropdownMenu from '../common/DropdownMenu.vue';
import { eventBus } from '../../utils/eventBus';
import { useDebounceFn } from '@vueuse/core';

import icon_white from '../../assets/logo/icon_white.png';
import icon_dark from '../../assets/logo/icon_dark.png';

import light from '../../assets/theme/light.svg';
import dark from '../../assets/theme/dark.svg';

const themeStore = useThemeStore();
const userStore = useUserStore();
const router = useRouter();

const searchQuery = ref('');

defineProps<{
  leftSidebarCollapsed: boolean;
  rightSidebarVisible: boolean;
  
}>();

const emit = defineEmits([
  'toggle-left-sidebar',
  'toggle-right-sidebar',
]);

const handleLogout = () => {
  userStore.logout();
  router.push('/login');
};

const performSearch = (query: string) => {
  // 发送搜索事件到 MyFiles 页面
  eventBus.emit('search-files', { query });
};

const debouncedSearch = useDebounceFn(performSearch, 300);

const handleSearch = (event: Event) => {
  const target = event.target as HTMLInputElement;
  const query = target.value.trim();
  
  debouncedSearch(query);
};

const handleSearchKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Enter') {
    handleSearch(event);
  }
};
</script>

<template>
  <header class="app-header">
    <div class="header-left">
      <button 
        class="sidebar-toggle-btn"
        @click="$emit('toggle-left-sidebar')"
        :aria-label="leftSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
      >
        <!-- Icon placeholder -->
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><path fill="currentColor" d="M3 18v-2h18v2zm0-5v-2h18v2zm0-5V6h18v2z"/></svg>
      </button>

      <img v-if="themeStore.theme === 'light'" :src="icon_white" alt="fileflash Logo" class="logo-image" width="100" height="50">
      <img v-else :src="icon_dark" alt="fileflash Logo" class="logo-image" width="100" height="100">
    </div>
    
    <div class="header-center">
      <div class="search-bar">
        <!-- Search icon -->
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24"><path fill="currentColor" d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5A6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19zM9.5 14C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5S14 7.01 14 9.5S11.99 14 9.5 14"/></svg>
        <input 
          type="text" 
          v-model="searchQuery" 
          placeholder="Search files..."
          @input="handleSearch"
          @keydown="handleSearchKeydown"
        >
      </div>
    </div>

    <div class="header-right">
      <button class="icon-btn" @click="themeStore.toggleTheme" aria-label="Toggle theme">
        <!-- Sun/Moon icon placeholder -->
        <img v-if="themeStore.theme === 'light'" :src="light" alt="Theme" width="24" height="24">
        <img v-else :src="dark" alt="Theme" width="24" height="24">
      </button>

      <button 
        class="sidebar-toggle-btn"
        @click="$emit('toggle-right-sidebar')"
        :aria-label="rightSidebarVisible ? 'Hide details' : 'Show details'"
      >
        <!-- Right sidebar icon placeholder -->
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><path fill="currentColor" d="M19 18h2v-2h-2zm0-5h2v-2h-2zm0-5h2V6h-2zM3 18v-2h14v2zm0-5v-2h14v2zm0-5V6h14v2z"/></svg>
      </button>

      <DropdownMenu>
        <template #trigger>
          <div class="user-profile">
            <img src="../../assets/generic/user.svg" alt="User avatar" class="avatar">
          </div>
        </template>
        <template #content>
          <div class="dropdown-content">
            <div class="user-info">
              <p class="username">{{ userStore.user?.username || 'User' }}</p>
              <p class="email">{{ userStore.user?.email || 'email@example.com' }}</p>
            </div>
            <hr class="divider">
            <router-link to="/profile" class="dropdown-item">
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24"><path fill="currentColor" d="M12 12q-1.65 0-2.825-1.175T8 8q0-1.65 1.175-2.825T12 4q1.65 0 2.825 1.175T16 8q0 1.65-1.175 2.825T12 12m-8 8v-2.8q0-.85.438-1.563T5.6 14.55q1.55-.775 3.15-1.163T12 13q1.65 0 3.25.388t3.15 1.162q.725.375 1.163 1.088T20 17.2V20z"/></svg>
              个人资料
            </router-link>
            <router-link to="/settings" class="dropdown-item">
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24"><path fill="currentColor" d="M19.14,12.94c0.04-0.3,0.06-0.61,0.06-0.94c0-0.32-0.02-0.64-0.07-0.94l2.03-1.58c0.18-0.14,0.23-0.41,0.12-0.61 l-1.92-3.32c-0.12-0.22-0.37-0.29-0.59-0.22l-2.39,0.96c-0.5-0.38-1.03-0.7-1.62-0.94L14.4,2.81c-0.04-0.24-0.24-0.41-0.48-0.41 h-3.84c-0.24,0-0.43,0.17-0.47,0.41L9.25,5.35C8.66,5.59,8.12,5.92,7.63,6.29L5.24,5.33c-0.22-0.08-0.47,0-0.59,0.22L2.74,8.87 C2.62,9.08,2.66,9.34,2.86,9.48l2.03,1.58C4.84,11.36,4.82,11.69,4.82,12s0.02,0.64,0.07,0.94l-2.03,1.58 c-0.18,0.14-0.23,0.41-0.12,0.61l1.92,3.32c0.12,0.22,0.37,0.29,0.59,0.22l2.39-0.96c0.5,0.38,1.03,0.7,1.62,0.94l0.36,2.54 c0.05,0.24,0.24,0.41,0.48,0.41h3.84c0.24,0,0.44-0.17,0.47-0.41l0.36-2.54c0.59-0.24,1.13-0.56,1.62-0.94l2.39,0.96 c0.22,0.08,0.47,0,0.59-0.22l1.92-3.32c0.12-0.22,0.07-0.47-0.12-0.61L19.14,12.94z M12,15.6c-1.98,0-3.6-1.62-3.6-3.6 s1.62-3.6,3.6-3.6s3.6,1.62,3.6,3.6S13.98,15.6,12,15.6z"/></svg>
              设置
            </router-link>
            <hr class="divider">
            <button @click="handleLogout" class="dropdown-item logout-item">
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24"><path fill="currentColor" d="M5 21q-.825 0-1.413-.587T3 19V5q0-.825.588-1.413T5 3h7v2H5v14h7v2zm11-4l-1.375-1.45l2.55-2.55H9v-2h8.175l-2.55-2.55L16 7l5 5z"/></svg>
              退出登录
            </button>
          </div>
        </template>
      </DropdownMenu>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: var(--layout-header-height);
  padding: 0 var(--spacing-lg);
  background-color: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border);
  transition: background-color var(--transition-base), border-color var(--transition-base);
  flex-shrink: 0;
}

.header-left, .header-center, .header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.logo {
  font-size: 1.5rem;
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.search-bar {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  background-color: var(--color-bg-tertiary);
  border-radius: var(--border-radius-md);
  padding: var(--spacing-sm) var(--spacing-md);
  width: 400px;
}

.search-bar svg {
  color: var(--color-text-tertiary);
}

.search-bar input {
  border: none;
  outline: none;
  background: transparent;
  width: 100%;
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
}

.sidebar-toggle-btn, .icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: none;
  background-color: transparent;
  color: var(--color-text-secondary);
  border-radius: var(--border-radius-md);
  cursor: pointer;
  transition: var(--transition-base);
}

.sidebar-toggle-btn:hover, .icon-btn:hover {
  background-color: var(--color-bg-tertiary);
  color: var(--color-text-primary);
}

.user-profile {
  display: flex;
  align-items: center;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  object-fit: cover;
}
.dropdown-content {
  padding: var(--spacing-sm) 0;
}

.user-info {
  padding: var(--spacing-sm) var(--spacing-md);
  margin-bottom: var(--spacing-sm);
}

.user-info .username {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.user-info .email {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin: 0;
}

.divider {
  border: none;
  border-top: 1px solid var(--color-divider);
  margin: var(--spacing-sm) 0;
}

.dropdown-item {
  display: block;
  width: 100%;
  text-align: left;
  padding: var(--spacing-sm) var(--spacing-md);
  color: var(--color-text-secondary);
  background: none;
  border: none;
  font-size: var(--font-size-base);
  cursor: pointer;
  text-decoration: none;
  border-radius: var(--border-radius-sm);
  transition: all var(--transition-base);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.dropdown-item:hover {
  background-color: var(--color-bg-tertiary);
  color: var(--color-text-primary);
}

.dropdown-item svg {
  flex-shrink: 0;
}

.logout-item {
  color: var(--color-danger, #dc2626);
}

.logout-item:hover {
  background-color: rgba(220, 38, 38, 0.1);
  color: var(--color-danger, #dc2626);
}
</style> 