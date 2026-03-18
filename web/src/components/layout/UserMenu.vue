<script setup lang="ts">
import { useRouter } from 'vue-router';
import { useUserStore } from '../../store/user';
import { storeToRefs } from 'pinia';
import DropdownMenu from '../common/DropdownMenu.vue';

const userStore = useUserStore();
const { user } = storeToRefs(userStore);
const router = useRouter();

const getInitials = (name: string) => {
  if (!name) return '';
  const names = name.split(' ');
  return names.map(n => n[0]).join('').toUpperCase();
};

const goToProfile = () => {
  router.push('/profile');
};

const goToSettings = () => {
  router.push('/settings');
};

const handleLogout = () => {
  userStore.logout();
  router.push('/login');
};
</script>

<template>
  <DropdownMenu v-if="user">
    <template #trigger>
      <button class="avatar-btn">
        <span>{{ getInitials(user.username) }}</span>
      </button>
    </template>
    <template #content>
      <div class="dropdown-content">
        <div class="user-info">
          <p class="username">{{ user.username }}</p>
          <p class="email">{{ user.email }}</p>
        </div>
        <hr class="divider" />
        <button @click="goToProfile" class="dropdown-item">
          <span>👤</span>
          <span>My Profile</span>
        </button>
        <button @click="goToSettings" class="dropdown-item">
          <span>⚙️</span>
          <span>Settings</span>
        </button>
        <hr class="divider" />
        <button @click="handleLogout" class="dropdown-item danger">
          <span>🚪</span>
          <span>Logout</span>
        </button>
      </div>
    </template>
  </DropdownMenu>
</template>

<style scoped>
.avatar-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: var(--color-primary);
  color: var(--color-text-on-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  font-weight: var(--font-weight-bold);
  border: none;
  cursor: pointer;
  transition: opacity var(--transition-base);
}
.avatar-btn:hover {
  opacity: 0.9;
}

.dropdown-content {
  padding: var(--spacing-xs);
  min-width: 220px;
  background-color: var(--color-bg-primary);
  border-radius: var(--border-radius-md);
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border);
}

.user-info {
  padding: var(--spacing-sm) var(--spacing-md);
}
.user-info .username {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}
.user-info .email {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.divider {
  border: none;
  border-top: 1px solid var(--color-border);
  margin: var(--spacing-xs) 0;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  width: 100%;
  text-align: left;
  padding: var(--spacing-sm) var(--spacing-md);
  color: var(--color-text-primary);
  background: none;
  border: none;
  font-size: var(--font-size-base);
  cursor: pointer;
  white-space: nowrap;
  border-radius: var(--border-radius-sm);
  transition: background-color 0.2s, color 0.2s;
}
.dropdown-item:hover {
  background-color: var(--color-bg-tertiary);
}
.dropdown-item.danger {
  color: var(--color-danger);
}
.dropdown-item.danger:hover {
  background-color: #fee2e2;
  color: #b91c1c;
}
.dark-theme .dropdown-item.danger:hover {
    background-color: #3f1a1a;
    color: #fca5a5;
}
</style> 