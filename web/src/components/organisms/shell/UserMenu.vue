<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useUserStore } from '../../../store/user';
import { useLocaleStore } from '../../../store/locale';
import Avatar from '../../molecules/Avatar.vue';
import MenuItem from '../../molecules/MenuItem.vue';
import Divider from '../../atoms/Divider.vue';
import Icon from '../../atoms/Icon.vue';

const router = useRouter();
const userStore = useUserStore();
const localeStore = useLocaleStore();
const t = localeStore.t;

const open = ref(false);
const isAdmin = userStore.user?.role === 'admin';

function handleLogout() {
  userStore.logout();
  router.push('/login');
}

function close() { open.value = false; }
</script>

<template>
  <div class="user-menu">
    <button class="user-trigger" @click="open = !open" :aria-expanded="open">
      <Avatar :name="userStore.user?.username || '?'" size="sm" />
      <span class="user-name">{{ userStore.user?.username || t('header.menu.defaultUserName') }}</span>
      <Icon name="chevronDown" :size="12" />
    </button>
    <div v-if="open" class="user-dropdown">
      <div class="user-dropdown-inner" @click.self="close">
        <div class="user-info">
          <strong>{{ userStore.user?.username || t('header.menu.defaultUserName') }}</strong>
          <span v-if="isAdmin" class="user-role">{{ t('header.menu.admin') }}</span>
          <small>{{ userStore.user?.email || t('header.menu.defaultEmail') }}</small>
        </div>
        <Divider />
        <MenuItem icon="folder" @click="router.push('/profile'); close()">{{ t('header.menu.profile') }}</MenuItem>
        <MenuItem icon="more" @click="router.push('/settings'); close()">{{ t('header.menu.settings') }}</MenuItem>
        <MenuItem v-if="isAdmin" icon="search" @click="router.push('/dashboard'); close()">{{ t('header.menu.dashboard') }}</MenuItem>
        <Divider />
        <MenuItem variant="danger" icon="trash" @click="handleLogout(); close()">{{ t('header.menu.logout') }}</MenuItem>
      </div>
    </div>
  </div>
</template>

<style scoped>
.user-menu { position: relative; }
.user-trigger {
  display: inline-flex; align-items: center; gap: 8px;
  height: 32px; padding: 0 10px 0 6px;
  background: var(--surface-raised); border: 1px solid var(--border-default); border-radius: var(--radius-sm);
  color: var(--text-secondary); font-family: var(--font-sans); font-size: var(--text-body);
  cursor: pointer; transition: border-color var(--mo-duration-fast) var(--mo-easing), background-color var(--mo-duration-fast) var(--mo-easing);
}
.user-trigger:hover { background: var(--surface-inset); border-color: var(--border-strong); color: var(--text-primary); }
.user-name { max-width: 120px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.user-dropdown { position: absolute; top: calc(100% + 6px); right: 0; z-index: 50; }
.user-dropdown-inner {
  width: 220px; padding: 6px;
  background: var(--surface-raised); border: 1px solid var(--border-default);
  box-shadow: var(--shadow-overlay);
}
.user-info { padding: 8px 10px; display: flex; flex-direction: column; gap: 2px; }
.user-info strong { font-size: var(--text-body); color: var(--text-primary); }
.user-info small { font-size: var(--text-small); color: var(--text-dim); }
.user-role {
  display: inline-flex; align-self: flex-start;
  font-size: var(--text-label); font-family: var(--font-mono); letter-spacing: var(--tracking-wide); text-transform: uppercase;
  padding: 1px 6px; border: 1px solid rgba(var(--ac-rgb), 0.35); color: var(--ac); background: rgba(var(--ac-rgb), 0.1);
  border-radius: var(--radius-md);
}
</style>
