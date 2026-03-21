<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useDebounceFn } from '@vueuse/core';
import type { ContentItem } from '../../types/file';
import type { Collaborator } from '../../types/share';
import type { PermissionItem } from '../../types/permission';
import type { User, UserGroup } from '../../types/user';
import { createShare } from '../../api/share';
import { getUsers } from '../../api/user';
import { getUserGroups } from '../../api/usergroup';
import { createPermission, deletePermission, getPermissions, updatePermission } from '../../api/permission';

interface Props {
  isVisible: boolean;
  itemToShare: ContentItem | null;
}

const props = defineProps<Props>();
const emit = defineEmits(['close']);

const searchKeyword = ref('');
const searchResults = ref<Collaborator[]>([]);
const collaborators = ref<Collaborator[]>([]);
const isSearching = ref(false);

const publicLinkEnabled = ref(false);
const publicLink = ref('');
const isCreatingShare = ref(false);

const currentItemPayload = computed(() => {
  if (!props.itemToShare) return null;

  if (props.itemToShare.itemType === 'file') {
    return { fileId: props.itemToShare.id };
  }

  return { folderId: props.itemToShare.id };
});

const fetchPermissions = async () => {
  if (!currentItemPayload.value) return;

  try {
    const response = await getPermissions({ ...currentItemPayload.value, page: 1, perPage: 50 });
    collaborators.value = response.items.map((permission: PermissionItem) => ({
      id: permission.grantedTo.id,
      name: permission.grantedTo.name,
      type: permission.grantedTo.type,
      permission: permission.permission,
      permissionId: permission.permissionId,
    }));
  } catch (error) {
    console.error('Failed to fetch permissions', error);
    collaborators.value = [];
  }
};

const searchCollaborators = async (keyword: string) => {
  const query = keyword.trim();
  if (!query) {
    searchResults.value = [];
    return;
  }

  isSearching.value = true;
  try {
    const [users, groups] = await Promise.all([
      getUsers({ search: query, page: 1, perPage: 8 }),
      getUserGroups({ search: query, page: 1, perPage: 8 }),
    ]);

    const userResults: Collaborator[] = users.items.map((user: User) => ({
      id: user.userId,
      name: user.username,
      type: 'user',
      email: user.email,
    }));

    const groupResults: Collaborator[] = groups.items.map((group: UserGroup) => ({
      id: group.groupId,
      name: group.name,
      type: 'group',
    }));

    const existingIds = new Set(collaborators.value.map((item) => `${item.type}:${item.id}`));
    searchResults.value = [...userResults, ...groupResults].filter((item) => !existingIds.has(`${item.type}:${item.id}`));
  } finally {
    isSearching.value = false;
  }
};

const debouncedSearch = useDebounceFn(searchCollaborators, 260);

const addCollaborator = async (target: Collaborator) => {
  if (!currentItemPayload.value) return;

  try {
    const created = await createPermission({
      ...currentItemPayload.value,
      userId: target.type === 'user' ? target.id : undefined,
      groupId: target.type === 'group' ? target.id : undefined,
      permission: 'read',
    });

    collaborators.value.push({
      ...target,
      permission: created.permission,
      permissionId: created.permissionId,
    });

    searchKeyword.value = '';
    searchResults.value = [];
  } catch (error) {
    console.error('Failed to add collaborator', error);
  }
};

const changePermission = async (collaborator: Collaborator, permission: 'read' | 'write' | 'admin') => {
  if (!collaborator.permissionId) return;

  try {
    await updatePermission(collaborator.permissionId, { permission });
    collaborator.permission = permission;
  } catch (error) {
    console.error('Failed to update permission', error);
  }
};

const removeCollaborator = async (collaborator: Collaborator) => {
  if (!collaborator.permissionId) return;

  try {
    await deletePermission(collaborator.permissionId);
    collaborators.value = collaborators.value.filter((item) => item.permissionId !== collaborator.permissionId);
  } catch (error) {
    console.error('Failed to remove permission', error);
  }
};

const createPublicShare = async () => {
  if (!props.itemToShare) return;

  isCreatingShare.value = true;
  try {
    const share = await createShare({
      resourceType: props.itemToShare.itemType,
      resourceId: props.itemToShare.id,
    });

    publicLink.value = `${window.location.origin}/share/${share.shareLink}`;
  } catch (error) {
    console.error('Failed to create share link', error);
    publicLinkEnabled.value = false;
  } finally {
    isCreatingShare.value = false;
  }
};

const copyLink = async () => {
  if (!publicLink.value) return;

  try {
    await navigator.clipboard.writeText(publicLink.value);
  } catch {
    window.prompt('Copy this link', publicLink.value);
  }
};

watch(
  () => props.isVisible,
  async (visible) => {
    if (!visible) return;

    searchKeyword.value = '';
    searchResults.value = [];
    publicLinkEnabled.value = false;
    publicLink.value = '';

    await fetchPermissions();
  },
);

watch(publicLinkEnabled, (enabled) => {
  if (enabled && !publicLink.value) {
    createPublicShare();
  }
});
</script>

<template>
  <transition name="modal-fade">
    <div v-if="isVisible" class="modal-overlay" @click.self="$emit('close')">
      <div class="modal-dialog">
        <header class="modal-header">
          <div>
            <h3 class="modal-title">Share: {{ itemToShare?.name }}</h3>
            <p class="subtitle">Manage access and generate a public link.</p>
          </div>
          <button class="modal-close" @click="$emit('close')" aria-label="Close dialog">×</button>
        </header>

        <div class="modal-body">
          <section class="section">
            <h4>Collaborator Permissions</h4>

            <div class="search-box">
              <input
                v-model="searchKeyword"
                type="text"
                placeholder="Search users or groups"
                @input="debouncedSearch(searchKeyword)"
              />
              <div v-if="isSearching" class="hint">Searching...</div>
            </div>

            <div v-if="searchResults.length" class="search-list">
              <button v-for="result in searchResults" :key="`${result.type}-${result.id}`" class="search-item" @click="addCollaborator(result)">
                <span>{{ result.name }}</span>
                <small>{{ result.type === 'user' ? result.email : 'User group' }}</small>
              </button>
            </div>

            <div v-if="!collaborators.length" class="empty-hint">No collaborators configured.</div>

            <div v-else class="collaborator-list">
              <div v-for="collaborator in collaborators" :key="collaborator.permissionId || `${collaborator.type}-${collaborator.id}`" class="collaborator-item">
                <div class="collaborator-meta">
                  <strong>{{ collaborator.name }}</strong>
                  <small>{{ collaborator.type === 'user' ? collaborator.email || 'User' : 'Group' }}</small>
                </div>

                <select
                  :value="collaborator.permission"
                  @change="changePermission(collaborator, ($event.target as HTMLSelectElement).value as 'read' | 'write' | 'admin')"
                >
                  <option value="read">Read</option>
                  <option value="write">Write</option>
                  <option value="admin">Admin</option>
                </select>

                <button class="remove-btn" @click="removeCollaborator(collaborator)">Remove</button>
              </div>
            </div>
          </section>

          <section class="section public-share">
            <div class="public-head">
              <div>
                <h4>Public Link</h4>
                <p>Anyone with the link can access according to permission rules.</p>
              </div>

              <label class="switch">
                <input v-model="publicLinkEnabled" type="checkbox" :disabled="isCreatingShare" />
                <span class="slider" />
              </label>
            </div>

            <div v-if="publicLinkEnabled" class="public-content">
              <div v-if="isCreatingShare" class="hint">Generating link...</div>
              <div v-else class="link-row">
                <input type="text" :value="publicLink" readonly />
                <button @click="copyLink">Copy</button>
              </div>
            </div>
          </section>
        </div>

        <footer class="modal-footer">
          <button class="done-btn" @click="$emit('close')">Done</button>
        </footer>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.modal-dialog {
  width: min(700px, calc(100vw - 24px));
  max-height: calc(100vh - 40px);
  display: flex;
  flex-direction: column;
  border: 1px solid var(--color-border);
  border-radius: 14px;
  background-color: var(--color-bg-primary);
  box-shadow: var(--shadow-xl);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--color-divider);
}

.modal-title {
  margin: 0;
  font-size: 17px;
}

.subtitle {
  margin: 4px 0 0;
  color: var(--color-text-tertiary);
  font-size: 12px;
}

.modal-close {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  background-color: var(--color-bg-primary);
  cursor: pointer;
}

.modal-body {
  overflow: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.section {
  border: 1px solid var(--color-border);
  border-radius: 10px;
  background-color: var(--color-bg-secondary);
  padding: 12px;
}

.section h4 {
  margin: 0 0 10px;
}

.search-box input {
  width: 100%;
  height: 36px;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  background-color: var(--color-bg-primary);
  padding: 0 10px;
}

.search-list {
  margin-top: 8px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  max-height: 160px;
  overflow: auto;
}

.search-item {
  width: 100%;
  border: none;
  background: transparent;
  text-align: left;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  cursor: pointer;
}

.search-item:hover {
  background-color: var(--color-bg-tertiary);
}

.search-item small {
  color: var(--color-text-tertiary);
}

.empty-hint,
.hint {
  color: var(--color-text-tertiary);
  font-size: 13px;
}

.collaborator-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 10px;
}

.collaborator-item {
  display: grid;
  grid-template-columns: 1fr 120px auto;
  gap: 8px;
  align-items: center;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 8px;
  background-color: var(--color-bg-primary);
}

.collaborator-meta {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.collaborator-meta strong,
.collaborator-meta small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.collaborator-meta small {
  color: var(--color-text-tertiary);
}

.collaborator-item select {
  height: 34px;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  padding: 0 8px;
}

.remove-btn {
  height: 34px;
  border-radius: 8px;
  border: 1px solid #fca5a5;
  background-color: var(--color-danger-light);
  color: var(--color-danger-dark);
  cursor: pointer;
}

.public-share .public-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.public-share .public-head p {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.public-content {
  margin-top: 10px;
}

.link-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
}

.link-row input {
  height: 36px;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  background-color: var(--color-bg-primary);
  padding: 0 10px;
  font-family: var(--font-family-mono);
  font-size: 12px;
}

.link-row button {
  height: 36px;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  background-color: var(--color-bg-primary);
  cursor: pointer;
  padding: 0 12px;
}

.modal-footer {
  padding: 12px 16px;
  border-top: 1px solid var(--color-divider);
  display: flex;
  justify-content: flex-end;
}

.done-btn {
  height: 36px;
  border-radius: 8px;
  border: none;
  padding: 0 14px;
  color: var(--color-text-on-primary);
  background-color: var(--color-primary);
  cursor: pointer;
}

.switch {
  width: 44px;
  height: 24px;
  position: relative;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  inset: 0;
  border-radius: 999px;
  background-color: var(--color-border);
  transition: 0.2s;
}

.slider::before {
  content: '';
  position: absolute;
  width: 18px;
  height: 18px;
  left: 3px;
  top: 3px;
  border-radius: 50%;
  background-color: #fff;
  transition: 0.2s;
}

.switch input:checked + .slider {
  background-color: var(--color-primary);
}

.switch input:checked + .slider::before {
  transform: translateX(20px);
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
</style>
