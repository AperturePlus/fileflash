<script setup lang="ts">
import { ref, watch} from 'vue';
import type { ContentItem } from '../../types/file';
import type { Collaborator, CreateShareRequest } from '../../types/share';
import { createShare } from '../../api/share';

interface Props {
  isVisible: boolean;
  itemToShare: ContentItem | null;
}
const props = defineProps<Props>();
defineEmits(['close']);

// --- State for internal sharing (ACL) ---
const searchInput = ref('');
const searchResults = ref<Collaborator[]>([]);
const selectedCollaborators = ref<Collaborator[]>([]);

// --- State for public link sharing ---
const publicLinkEnabled = ref(false);
const publicLink = ref(''); 
const isCreatingShare = ref(false);

// --- Share creation function ---
const createPublicShare = async () => {
  if (!props.itemToShare) {
    console.error('No item to share provided');
    return;
  }
  
  isCreatingShare.value = true;
  try {
    const shareRequest: CreateShareRequest = {
      resourceType: props.itemToShare.itemType,
      resourceId: props.itemToShare.id,
    };

    const shareResponse = await createShare(shareRequest);
    
    if (shareResponse && shareResponse.shareLink) {
      publicLink.value = shareResponse.shareLink;
      console.log('Share created successfully');
    } else {
      throw new Error('No share link in response');
    }
    
  } catch (error) {
    console.error('Failed to create share:', error);
    alert('创建分享失败，请重试');
    publicLinkEnabled.value = false;
  } finally {
    isCreatingShare.value = false;
  }
};
// -------------------------

const fetchExistingCollaborators = async () => {
  // 暂时禁用权限获取，因为后端没有实现 permissions API
  console.log('fetchExistingCollaborators disabled for now');
  selectedCollaborators.value = [];
};

// Reset state when the dialog is closed/opened
watch(() => props.isVisible, async (newValue) => {
  if (newValue) {
    // Reset all fields to default when dialog opens
    searchInput.value = '';
    searchResults.value = [];
    publicLinkEnabled.value = false;
    publicLink.value = '';
    
    // 获取现有的协作者信息
    await fetchExistingCollaborators();
  }
});
// 分享组件 抽象版
//------------------
// Watch for public link toggle to create share automatically
watch(publicLinkEnabled, (newValue) => {
  console.log('Public link enabled changed:', newValue);
  if (newValue && props.itemToShare) {
    console.log('Creating public share automatically...');
    createPublicShare();
  }
});
// --------------
const copyLink = () => {
    navigator.clipboard.writeText(publicLink.value)
        .then(() => alert('Link copied to clipboard!'))
        .catch(err => console.error('Failed to copy link: ', err));
};
</script>

<template>
  <transition name="modal-fade">
    <div v-if="isVisible" class="modal-overlay" @click.self="$emit('close')">
      <div class="modal-dialog">
        <header class="modal-header">
          <div class="title-section">
            <span class="header-icon">🤝</span>
            <h3 class="modal-title">Share '{{ itemToShare?.name }}'</h3>
          </div>
          <button class="modal-close" @click="$emit('close')">&times;</button>
        </header>

        <div class="modal-body">
          <!-- 暂时隐藏内部分享功能
          <div class="share-section internal-sharing">
            Internal sharing content
          </div>
          <hr class="divider" />
          -->

          <!-- Public Link Sharing Section -->
          <div class="share-section public-sharing">
            <div class="public-link-header">
              <span class="header-icon">🔗</span>
              <div class="public-link-info">
                <h4>Get public link</h4>
                <p>Anyone with this link can view</p>
              </div>
              <label class="switch">
                <input type="checkbox" v-model="publicLinkEnabled" :disabled="isCreatingShare">
                <span class="slider round"></span>
              </label>
            </div>
            
            <transition name="slide-fade">
              <div v-if="publicLinkEnabled" class="public-link-settings">
                <div v-if="isCreatingShare" class="loading-indicator">
                  <span>Creating share link...</span>
                </div>
                <div v-else>
                  <div class="link-display">
                    <input type="text" :value="publicLink" readonly />
                    <button class="btn btn-secondary" @click="copyLink">Copy</button>
                  </div>
                </div>
              </div>
            </transition>
          </div>
        </div>

        <footer class="modal-footer">
          <button class="btn btn-primary" @click="$emit('close')">Done</button>
        </footer>
      </div>
    </div>
  </transition>
</template>

<style scoped>
/* Base Modal Styles */
.modal-overlay {
  position: fixed; inset: 0; background-color: rgba(0, 0, 0, 0.5);
  display: flex; justify-content: center; align-items: center; z-index: 2000;
}
.modal-dialog {
  background-color: var(--color-bg-secondary);
  border-radius: var(--border-radius-lg);
  box-shadow: var(--shadow-xl);
  width: 100%;
  max-width: 560px; /* Wider for share dialog */
  display: flex; flex-direction: column;
  border: 1px solid var(--color-border);
}
.modal-header {
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--color-border);
  display: flex; justify-content: space-between; align-items: center;
}
.title-section {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
}
.header-icon { font-size: 1.5rem; }
.modal-title { margin: 0; font-size: 1.125rem; font-weight: var(--font-weight-semibold); }
.modal-close {
  background: none; border: none; font-size: 1.75rem; line-height: 1;
  cursor: pointer; color: var(--color-text-secondary); padding: 0;
}
.modal-body { padding: 0; max-height: 70vh; overflow-y: auto; }
.modal-footer {
  padding: var(--spacing-lg);
  border-top: 1px solid var(--color-border);
  display: flex; justify-content: flex-end;
  background-color: var(--color-bg-tertiary);
  border-bottom-left-radius: var(--border-radius-lg);
  border-bottom-right-radius: var(--border-radius-lg);
}

/* Share Sections */
.share-section { padding: var(--spacing-lg); }
.divider { border: none; border-top: 1px solid var(--color-divider); margin: 0; }

/* Internal Sharing */
.search-and-add { position: relative; }
.search-input {
  width: 100%;
  padding: var(--spacing-md);
  border-radius: var(--border-radius-md);
  border: 1px solid var(--color-border);
  background-color: var(--color-bg-primary);
  font-size: 1rem;
}
.search-results-container {
  position: absolute;
  background: var(--color-bg-secondary);
  width: 100%;
  border: 1px solid var(--color-border);
  border-top: none;
  border-radius: 0 0 var(--border-radius-md) var(--border-radius-md);
  box-shadow: var(--shadow-md);
  z-index: 10;
  max-height: 200px;
  overflow-y: auto;
}
.search-result-item {
  padding: var(--spacing-sm) var(--spacing-md);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}
.search-result-item:hover { background: var(--color-bg-tertiary); }
.result-icon { font-size: 1.25rem; }
.result-info { display: flex; flex-direction: column; }
.result-name { font-weight: var(--font-weight-medium); }
.result-detail { color: var(--color-text-tertiary); font-size: 0.875rem; }

.collaborators-list {
  margin-top: var(--spacing-lg);
}
.collaborators-list > p {
    font-size: .875rem;
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-sm);
}
.collaborator-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-sm) 0;
}
.collab-icon { font-size: 1.5rem; }
.collab-info { flex-grow: 1; display: flex; flex-direction: column; }
.collab-name { font-weight: var(--font-weight-medium); }
.collab-detail { color: var(--color-text-tertiary); font-size: 0.875rem; }

.permission-select {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius-md);
  padding: var(--spacing-xs) var(--spacing-sm);
}
.remove-btn {
  background: none; border: none; color: var(--color-text-tertiary); cursor: pointer;
  font-size: 1.25rem;
}

/* Public Sharing */
.public-link-header {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
}
.public-link-info {
    flex-grow: 1;
}
.public-link-info h4, .public-link-info p {
    margin: 0;
}
.public-link-info p {
    font-size: .875rem;
    color: var(--color-text-secondary);
}

.public-link-settings {
  margin-top: var(--spacing-lg);
  padding: var(--spacing-lg);
  background-color: var(--color-bg-tertiary);
  border-radius: var(--border-radius-md);
}
.link-display {
  display: flex;
  gap: var(--spacing-sm);
}
.link-display input {
  flex-grow: 1;
  background-color: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius-md);
  padding: var(--spacing-sm);
  font-family: var(--font-family-mono);
}
.settings-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--spacing-lg);
    margin-top: var(--spacing-lg);
}
.settings-option {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
}
.checkbox-label {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    cursor: pointer;
}
.settings-input {
    width: 100%;
    padding: var(--spacing-sm);
    border-radius: var(--border-radius-md);
    border: 1px solid var(--color-border);
    background-color: var(--color-bg-primary);
}

.loading-indicator {
    text-align: center;
    padding: var(--spacing-lg);
    color: var(--color-text-secondary);
    font-style: italic;
}

/* Generic Button */
.btn {
  padding: var(--spacing-sm) var(--spacing-lg); 
  border-radius: var(--border-radius-md);
  border: 1px solid transparent; 
  cursor: pointer; 
  font-weight: var(--font-weight-medium);
  transition: all var(--transition-base);
}
.btn-primary {
  background-color: var(--color-primary); 
  color: var(--color-text-on-primary);
  border-color: var(--color-primary);
}
.btn-primary:hover:not(:disabled) { 
  background-color: var(--color-primary-hover); 
}
.btn-secondary {
  background-color: var(--color-bg-primary); 
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
}
.btn-secondary:hover:not(:disabled) { 
  border-color: var(--color-border-hover); 
}

/* Switch CSS */
.switch { position: relative; display: inline-block; width: 44px; height: 24px; }
.switch input { opacity: 0; width: 0; height: 0; }
.slider {
  position: absolute; cursor: pointer; inset: 0;
  background-color: var(--color-border); transition: .4s;
}
.slider:before {
  position: absolute; content: ""; height: 16px; width: 16px;
  left: 4px; bottom: 4px;
  background-color: white; transition: .4s;
}
input:checked + .slider { background-color: var(--color-primary); }
input:checked + .slider:before { transform: translateX(20px); }
.slider.round { border-radius: 24px; }
.slider.round:before { border-radius: 50%; }

/* Transitions */
.modal-fade-enter-active, .modal-fade-leave-active { transition: opacity 0.2s ease; }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0; }
.slide-fade-enter-active { transition: all .3s ease-out; }
.slide-fade-leave-active { transition: all .3s cubic-bezier(1.0, 0.5, 0.8, 1.0); }
.slide-fade-enter-from, .slide-fade-leave-to { transform: translateY(-10px); opacity: 0; }
</style>