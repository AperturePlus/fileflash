<script setup lang="ts">
import { storeToRefs } from 'pinia';
import { computed, onMounted, ref, watch } from 'vue';
import { useLocaleStore } from '../../store/locale';
import { useSettingsStore } from '../../store/settings';
import { useThemeStore } from '../../store/theme';
import { useUserStore } from '../../store/user';
import type { AppLanguage } from '../../types/user';
import { ui } from '../../utils/ui';

const themeStore = useThemeStore();
const settingsStore = useSettingsStore();
const userStore = useUserStore();
const localeStore = useLocaleStore();

const { theme } = storeToRefs(themeStore);
const { settings } = storeToRefs(settingsStore);
const { user } = storeToRefs(userStore);
const t = localeStore.t;

const activeTab = ref('appearance');
const selectedLanguage = ref<AppLanguage>(localeStore.locale);
const isUpdatingLanguage = ref(false);

const tabs = computed(() => [
  { id: 'appearance', name: t('settings.tab.appearance'), icon: 'APP' },
  { id: 'uploads', name: t('settings.tab.uploads'), icon: 'UPL' },
  { id: 'files', name: t('settings.tab.files'), icon: 'FILE' },
  { id: 'notifications', name: t('settings.tab.notifications'), icon: 'NOTE' },
  { id: 'security', name: t('settings.tab.security'), icon: 'SAFE' },
  { id: 'advanced', name: t('settings.tab.advanced'), icon: 'ADV' },
]);

const syncLanguageSelection = (language?: AppLanguage) => {
  const nextLanguage = language || user.value?.preference?.language || localeStore.locale;
  selectedLanguage.value = nextLanguage;
  if (localeStore.locale !== nextLanguage) {
    localeStore.setLocale(nextLanguage);
  }
};

watch(
  () => user.value?.preference?.language,
  (nextLanguage) => {
    syncLanguageSelection(nextLanguage);
  },
  { immediate: true },
);

onMounted(async () => {
  if (!user.value?.preference) {
    await userStore.fetchUserProfile();
  }
  syncLanguageSelection(user.value?.preference?.language);
});

const updateLanguagePreference = async () => {
  const nextLanguage = selectedLanguage.value;
  const previousLanguage = localeStore.locale;
  if (nextLanguage === previousLanguage) {
    return;
  }
  localeStore.setLocale(nextLanguage);

  if (!user.value) {
    return;
  }

  isUpdatingLanguage.value = true;
  try {
    await userStore.updatePreference({ language: nextLanguage });
  } catch (error) {
    console.error('Failed to update language preference:', error);
    localeStore.setLocale(previousLanguage);
    selectedLanguage.value = previousLanguage;
    ui.toast({ type: 'error', message: t('settings.language.updateFailed') });
  } finally {
    isUpdatingLanguage.value = false;
  }
};

const resetSettings = async () => {
  const confirmed = await ui.confirm({
    title: t('settings.actions.reset'),
    message: t('settings.confirmReset'),
    confirmText: t('settings.actions.reset'),
    danger: true,
  });
  if (!confirmed) return;
  settingsStore.resetSettings();
  ui.toast({ type: 'success', message: t('settings.resetSuccess') });
};

const exportSettings = () => {
  const settingsJson = settingsStore.exportSettings();
  const blob = new Blob([settingsJson], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'fileflash-settings.json';
  a.click();
  URL.revokeObjectURL(url);
};

const importSettings = (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      const result = e.target?.result as string;
      if (settingsStore.importSettings(result)) {
        ui.toast({ type: 'success', message: t('settings.importSuccess') });
      } else {
        ui.toast({ type: 'error', message: t('settings.importFailed') });
      }
    };
    reader.readAsText(file);
  }
};
</script>

<template>
  <div class="settings-page">
    <header class="page-header">
      <h1>{{ t('settings.pageTitle') }}</h1>
      <p>{{ t('settings.pageDescription') }}</p>
    </header>

    <div class="settings-container">
      <!-- Settings Tabs -->
      <nav class="settings-nav">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="nav-item"
          :class="{ active: activeTab === tab.id }"
          @click="activeTab = tab.id"
        >
          <span class="nav-icon">{{ tab.icon }}</span>
          <span class="nav-text">{{ tab.name }}</span>
        </button>
      </nav>

      <!-- Settings Content -->
      <div class="settings-content">
        <!-- 外观设置 -->
        <div v-if="activeTab === 'appearance'" class="settings-section">
          <h2 class="section-title">{{ t('settings.section.appearance') }}</h2>
          
          <div class="setting-item">
            <div class="setting-label">
              <h3>{{ t('settings.appearance.theme.label') }}</h3>
              <p>{{ t('settings.appearance.theme.description') }}</p>
            </div>
            <div class="setting-control">
              <div class="theme-switcher">
                <button 
                  class="theme-option" 
                  :class="{ active: theme === 'light' }"
                  @click="themeStore.setTheme('light')"
                >
                  <div class="theme-preview light"></div>
                  <span>{{ t('settings.appearance.theme.light') }}</span>
                </button>
                <button 
                  class="theme-option" 
                  :class="{ active: theme === 'dark' }"
                  @click="themeStore.setTheme('dark')"
                >
                  <div class="theme-preview dark"></div>
                  <span>{{ t('settings.appearance.theme.dark') }}</span>
                </button>
              </div>
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-label">
              <h3>{{ t('settings.language.label') }}</h3>
              <p>{{ t('settings.language.description') }}</p>
            </div>
            <div class="setting-control">
              <select
                v-model="selectedLanguage"
                :disabled="isUpdatingLanguage"
                @change="updateLanguagePreference"
                class="select-input"
              >
                <option value="zh-CN">{{ t('common.language.zhCN') }}</option>
                <option value="en-US">{{ t('common.language.enUS') }}</option>
              </select>
              <p v-if="isUpdatingLanguage" class="setting-hint">{{ t('settings.language.saving') }}</p>
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-label">
              <h3>{{ t('settings.appearance.compactMode.label') }}</h3>
              <p>{{ t('settings.appearance.compactMode.description') }}</p>
            </div>
            <div class="setting-control">
              <label class="switch">
                <input 
                  type="checkbox" 
                  v-model="settings.compactMode"
                  @change="settingsStore.updateSetting('compactMode', settings.compactMode)"
                >
                <span class="slider"></span>
              </label>
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-label">
              <h3>{{ t('settings.appearance.defaultFileView.label') }}</h3>
              <p>{{ t('settings.appearance.defaultFileView.description') }}</p>
            </div>
            <div class="setting-control">
              <select 
                v-model="settings.defaultFileView"
                @change="settingsStore.updateSetting('defaultFileView', settings.defaultFileView)"
                class="select-input"
              >
                <option value="list">{{ t('settings.appearance.defaultFileView.option.list') }}</option>
                <option value="grid">{{ t('settings.appearance.defaultFileView.option.grid') }}</option>
                <option value="tiles">{{ t('settings.appearance.defaultFileView.option.tiles') }}</option>
              </select>
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-label">
              <h3>{{ t('settings.appearance.showFileExtensions.label') }}</h3>
              <p>{{ t('settings.appearance.showFileExtensions.description') }}</p>
            </div>
            <div class="setting-control">
              <label class="switch">
                <input 
                  type="checkbox" 
                  v-model="settings.showFileExtensions"
                  @change="settingsStore.updateSetting('showFileExtensions', settings.showFileExtensions)"
                >
                <span class="slider"></span>
              </label>
            </div>
          </div>
        </div>

        <!-- 上传设置 -->
        <div v-if="activeTab === 'uploads'" class="settings-section">
          <h2 class="section-title">{{ t('settings.section.uploads') }}</h2>
          
          <div class="setting-item">
            <div class="setting-label">
              <h3>{{ t('settings.uploads.maxConcurrentUploads.label') }}</h3>
              <p>{{ t('settings.uploads.maxConcurrentUploads.description') }}</p>
            </div>
            <div class="setting-control">
              <input 
                type="number" 
                min="1" 
                max="10"
                v-model.number="settings.maxConcurrentUploads"
                @change="settingsStore.updateSetting('maxConcurrentUploads', settings.maxConcurrentUploads)"
                class="number-input"
              >
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-label">
              <h3>{{ t('settings.uploads.chunkSize.label') }}</h3>
              <p>{{ t('settings.uploads.chunkSize.description') }}</p>
            </div>
            <div class="setting-control">
              <select 
                v-model.number="settings.chunkSize"
                @change="settingsStore.updateSetting('chunkSize', settings.chunkSize)"
                class="select-input"
              >
                <option :value="1">1 MB</option>
                <option :value="2">2 MB</option>
                <option :value="5">5 MB</option>
                <option :value="10">10 MB</option>
                <option :value="20">20 MB</option>
              </select>
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-label">
              <h3>{{ t('settings.uploads.autoRetryFailedUploads.label') }}</h3>
              <p>{{ t('settings.uploads.autoRetryFailedUploads.description') }}</p>
            </div>
            <div class="setting-control">
              <label class="switch">
                <input 
                  type="checkbox" 
                  v-model="settings.autoRetryFailedUploads"
                  @change="settingsStore.updateSetting('autoRetryFailedUploads', settings.autoRetryFailedUploads)"
                >
                <span class="slider"></span>
              </label>
            </div>
          </div>

          <div class="setting-item" v-if="settings.autoRetryFailedUploads">
            <div class="setting-label">
              <h3>{{ t('settings.uploads.retryAttempts.label') }}</h3>
              <p>{{ t('settings.uploads.retryAttempts.description') }}</p>
            </div>
            <div class="setting-control">
              <input 
                type="number" 
                min="1" 
                max="5"
                v-model.number="settings.retryAttempts"
                @change="settingsStore.updateSetting('retryAttempts', settings.retryAttempts)"
                class="number-input"
              >
            </div>
          </div>
        </div>

        <!-- 文件管理设置 -->
        <div v-if="activeTab === 'files'" class="settings-section">
          <h2 class="section-title">{{ t('settings.section.files') }}</h2>
          
          <div class="setting-item">
            <div class="setting-label">
              <h3>{{ t('settings.files.itemsPerPage.label') }}</h3>
              <p>{{ t('settings.files.itemsPerPage.description') }}</p>
            </div>
            <div class="setting-control">
              <select 
                v-model.number="settings.itemsPerPage"
                @change="settingsStore.updateSetting('itemsPerPage', settings.itemsPerPage)"
                class="select-input"
              >
                <option :value="25">25</option>
                <option :value="50">50</option>
                <option :value="100">100</option>
                <option :value="200">200</option>
              </select>
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-label">
              <h3>{{ t('settings.files.showHiddenFiles.label') }}</h3>
              <p>{{ t('settings.files.showHiddenFiles.description') }}</p>
            </div>
            <div class="setting-control">
              <label class="switch">
                <input 
                  type="checkbox" 
                  v-model="settings.showHiddenFiles"
                  @change="settingsStore.updateSetting('showHiddenFiles', settings.showHiddenFiles)"
                >
                <span class="slider"></span>
              </label>
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-label">
              <h3>{{ t('settings.files.autoRefreshInterval.label') }}</h3>
              <p>{{ t('settings.files.autoRefreshInterval.description') }}</p>
            </div>
            <div class="setting-control">
              <input 
                type="number" 
                min="0" 
                max="300"
                v-model.number="settings.autoRefreshInterval"
                @change="settingsStore.updateSetting('autoRefreshInterval', settings.autoRefreshInterval)"
                class="number-input"
              >
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-label">
              <h3>{{ t('settings.files.autoDeleteDays.label') }}</h3>
              <p>{{ t('settings.files.autoDeleteDays.description') }}</p>
            </div>
            <div class="setting-control">
              <select 
                v-model.number="settings.autoDeleteDays"
                @change="settingsStore.updateSetting('autoDeleteDays', settings.autoDeleteDays)"
                class="select-input"
              >
                <option :value="7">{{ t('settings.files.autoDeleteDays.option.7') }}</option>
                <option :value="14">{{ t('settings.files.autoDeleteDays.option.14') }}</option>
                <option :value="30">{{ t('settings.files.autoDeleteDays.option.30') }}</option>
                <option :value="60">{{ t('settings.files.autoDeleteDays.option.60') }}</option>
                <option :value="90">{{ t('settings.files.autoDeleteDays.option.90') }}</option>
              </select>
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-label">
              <h3>{{ t('settings.files.confirmDelete.label') }}</h3>
              <p>{{ t('settings.files.confirmDelete.description') }}</p>
            </div>
            <div class="setting-control">
              <label class="switch">
                <input 
                  type="checkbox" 
                  v-model="settings.confirmDelete"
                  @change="settingsStore.updateSetting('confirmDelete', settings.confirmDelete)"
                >
                <span class="slider"></span>
              </label>
            </div>
          </div>
        </div>

        <!-- 通知设置 -->
        <div v-if="activeTab === 'notifications'" class="settings-section">
          <h2 class="section-title">{{ t('settings.section.notifications') }}</h2>
          
          <div class="setting-item">
            <div class="setting-label">
              <h3>{{ t('settings.notifications.desktop.label') }}</h3>
              <p>{{ t('settings.notifications.desktop.description') }}</p>
            </div>
            <div class="setting-control">
              <label class="switch">
                <input 
                  type="checkbox" 
                  v-model="settings.desktopNotifications"
                  @change="settingsStore.updateSetting('desktopNotifications', settings.desktopNotifications)"
                >
                <span class="slider"></span>
              </label>
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-label">
              <h3>{{ t('settings.notifications.sound.label') }}</h3>
              <p>{{ t('settings.notifications.sound.description') }}</p>
            </div>
            <div class="setting-control">
              <label class="switch">
                <input 
                  type="checkbox" 
                  v-model="settings.soundNotifications"
                  @change="settingsStore.updateSetting('soundNotifications', settings.soundNotifications)"
                >
                <span class="slider"></span>
              </label>
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-label">
              <h3>{{ t('settings.notifications.uploadComplete.label') }}</h3>
              <p>{{ t('settings.notifications.uploadComplete.description') }}</p>
            </div>
            <div class="setting-control">
              <label class="switch">
                <input 
                  type="checkbox" 
                  v-model="settings.uploadCompleteNotification"
                  @change="settingsStore.updateSetting('uploadCompleteNotification', settings.uploadCompleteNotification)"
                >
                <span class="slider"></span>
              </label>
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-label">
              <h3>{{ t('settings.notifications.error.label') }}</h3>
              <p>{{ t('settings.notifications.error.description') }}</p>
            </div>
            <div class="setting-control">
              <label class="switch">
                <input 
                  type="checkbox" 
                  v-model="settings.errorNotifications"
                  @change="settingsStore.updateSetting('errorNotifications', settings.errorNotifications)"
                >
                <span class="slider"></span>
              </label>
            </div>
          </div>
        </div>

        <!-- 安全设置 -->
        <div v-if="activeTab === 'security'" class="settings-section">
          <h2 class="section-title">{{ t('settings.section.security') }}</h2>
          
          <div class="setting-item">
            <div class="setting-label">
              <h3>{{ t('settings.security.sessionTimeout.label') }}</h3>
              <p>{{ t('settings.security.sessionTimeout.description') }}</p>
            </div>
            <div class="setting-control">
              <select 
                v-model.number="settings.sessionTimeout"
                @change="settingsStore.updateSetting('sessionTimeout', settings.sessionTimeout)"
                class="select-input"
              >
                <option :value="0">{{ t('settings.security.sessionTimeout.option.disabled') }}</option>
                <option :value="30">{{ t('settings.security.sessionTimeout.option.30m') }}</option>
                <option :value="60">{{ t('settings.security.sessionTimeout.option.1h') }}</option>
                <option :value="120">{{ t('settings.security.sessionTimeout.option.2h') }}</option>
                <option :value="240">{{ t('settings.security.sessionTimeout.option.4h') }}</option>
                <option :value="480">{{ t('settings.security.sessionTimeout.option.8h') }}</option>
              </select>
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-label">
              <h3>{{ t('settings.security.requirePasswordForSensitiveActions.label') }}</h3>
              <p>{{ t('settings.security.requirePasswordForSensitiveActions.description') }}</p>
            </div>
            <div class="setting-control">
              <label class="switch">
                <input 
                  type="checkbox" 
                  v-model="settings.requirePasswordForSensitiveActions"
                  @change="settingsStore.updateSetting('requirePasswordForSensitiveActions', settings.requirePasswordForSensitiveActions)"
                >
                <span class="slider"></span>
              </label>
            </div>
          </div>
        </div>

        <!-- 高级设置 -->
        <div v-if="activeTab === 'advanced'" class="settings-section">
          <h2 class="section-title">{{ t('settings.section.advanced') }}</h2>
          
          <div class="setting-item">
            <div class="setting-label">
              <h3>{{ t('settings.advanced.debugMode.label') }}</h3>
              <p>{{ t('settings.advanced.debugMode.description') }}</p>
            </div>
            <div class="setting-control">
              <label class="switch">
                <input 
                  type="checkbox" 
                  v-model="settings.debugMode"
                  @change="settingsStore.updateSetting('debugMode', settings.debugMode)"
                >
                <span class="slider"></span>
              </label>
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-label">
              <h3>{{ t('settings.advanced.cacheDuration.label') }}</h3>
              <p>{{ t('settings.advanced.cacheDuration.description') }}</p>
            </div>
            <div class="setting-control">
              <select 
                v-model.number="settings.cacheDuration"
                @change="settingsStore.updateSetting('cacheDuration', settings.cacheDuration)"
                class="select-input"
              >
                <option :value="1">{{ t('settings.advanced.cacheDuration.option.1h') }}</option>
                <option :value="6">{{ t('settings.advanced.cacheDuration.option.6h') }}</option>
                <option :value="12">{{ t('settings.advanced.cacheDuration.option.12h') }}</option>
                <option :value="24">{{ t('settings.advanced.cacheDuration.option.24h') }}</option>
                <option :value="72">{{ t('settings.advanced.cacheDuration.option.72h') }}</option>
              </select>
            </div>
          </div>

          <div class="setting-actions">
            <h3>{{ t('settings.actions.title') }}</h3>
            <div class="action-buttons">
              <button @click="exportSettings" class="btn btn-secondary">
                {{ t('settings.actions.export') }}
              </button>
              <label class="btn btn-secondary">
                {{ t('settings.actions.import') }}
                <input type="file" accept=".json" @change="importSettings" style="display: none;">
              </label>
              <button @click="resetSettings" class="btn btn-danger">
                {{ t('settings.actions.reset') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-page {
  padding: var(--spacing-lg);
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: var(--spacing-xl);
}

.page-header h1 {
  font-size: 1.8rem;
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-xs);
}

.page-header p {
  color: var(--color-text-secondary);
  font-size: var(--font-size-base);
}

.settings-container {
  display: grid;
  grid-template-columns: 250px 1fr;
  gap: var(--spacing-xl);
  align-items: start;
}

.settings-nav {
  background-color: var(--color-bg-secondary);
  border-radius: var(--border-radius-lg);
  padding: var(--spacing-md);
  position: sticky;
  top: var(--spacing-lg);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  width: 100%;
  padding: var(--spacing-md);
  border: none;
  background: none;
  color: var(--color-text-secondary);
  border-radius: var(--border-radius-md);
  cursor: pointer;
  transition: all var(--transition-base);
  margin-bottom: var(--spacing-xs);
}

.nav-item:hover {
  background-color: var(--color-bg-tertiary);
  color: var(--color-text-primary);
}

.nav-item.active {
  background-color: var(--color-primary);
  color: var(--color-text-on-primary);
}

.nav-icon {
  font-size: 1.2rem;
}

.nav-text {
  font-weight: var(--font-weight-medium);
}

.settings-content {
  background-color: var(--color-bg-secondary);
  border-radius: var(--border-radius-lg);
  padding: var(--spacing-xl);
  min-height: 600px;
}

.section-title {
  font-size: 1.5rem;
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-lg);
  padding-bottom: var(--spacing-md);
  border-bottom: 1px solid var(--color-border);
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--spacing-xl);
  margin-bottom: var(--spacing-lg);
  padding-bottom: var(--spacing-lg);
  border-bottom: 1px solid var(--color-border);
}

.setting-item:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.setting-label h3 {
  font-size: 1.1rem;
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-xs);
}

.setting-label p {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  max-width: 400px;
  line-height: 1.4;
}

.setting-control {
  flex-shrink: 0;
}

.setting-hint {
  margin-top: var(--spacing-xs);
  font-size: 0.8rem;
  color: var(--color-text-tertiary);
}

/* Theme Switcher */
.theme-switcher {
  display: flex;
  gap: var(--spacing-md);
}

.theme-option {
  border: 2px solid transparent;
  border-radius: var(--border-radius-md);
  padding: var(--spacing-sm);
  cursor: pointer;
  background-color: var(--color-bg-tertiary);
  text-align: center;
  transition: all var(--transition-base);
}

.theme-option:hover {
  border-color: var(--color-border-hover);
}

.theme-option.active {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(var(--color-primary-rgb, 59, 130, 246), 0.2);
}

.theme-preview {
  width: 80px;
  height: 50px;
  border-radius: var(--border-radius-sm);
  margin-bottom: var(--spacing-sm);
  border: 1px solid var(--color-border);
}

.theme-preview.light {
  background-color: #ffffff;
}

.theme-preview.dark {
  background-color: #1a202c;
}

.theme-option span {
  font-weight: var(--font-weight-medium);
  font-size: 0.9rem;
}

/* Switch Component */
.switch {
  position: relative;
  display: inline-block;
  width: 50px;
  height: 24px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: var(--color-border);
  transition: var(--transition-base);
  border-radius: 24px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: var(--transition-base);
  border-radius: 50%;
}

input:checked + .slider {
  background-color: var(--color-primary);
}

input:checked + .slider:before {
  transform: translateX(26px);
}

/* Form Inputs */
.select-input, .number-input {
  padding: var(--spacing-sm) var(--spacing-md);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius-md);
  background-color: var(--color-bg-primary);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  min-width: 120px;
}

.select-input:focus, .number-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(var(--color-primary-rgb, 59, 130, 246), 0.1);
}

/* Setting Actions */
.setting-actions {
  margin-top: var(--spacing-xl);
  padding-top: var(--spacing-lg);
  border-top: 1px solid var(--color-border);
}

.setting-actions h3 {
  font-size: 1.1rem;
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-md);
}

.action-buttons {
  display: flex;
  gap: var(--spacing-md);
  flex-wrap: wrap;
}

.btn {
  padding: var(--spacing-sm) var(--spacing-md);
  border: none;
  border-radius: var(--border-radius-md);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: all var(--transition-base);
}

.btn-secondary {
  background-color: var(--color-bg-tertiary);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
}

.btn-secondary:hover {
  background-color: var(--color-bg-quaternary);
}

.btn-danger {
  background-color: var(--color-danger, #dc2626);
  color: white;
}

.btn-danger:hover {
  background-color: var(--color-danger-hover, #b91c1c);
}

/* Responsive Design */
@media (max-width: 768px) {
  .settings-container {
    grid-template-columns: 1fr;
    gap: var(--spacing-lg);
  }
  
  .settings-nav {
    position: static;
    display: flex;
    overflow-x: auto;
    padding: var(--spacing-sm);
  }
  
  .nav-item {
    flex-shrink: 0;
    margin-right: var(--spacing-sm);
    margin-bottom: 0;
  }
  
  .setting-item {
    flex-direction: column;
    gap: var(--spacing-md);
  }
  
  .setting-control {
    align-self: flex-start;
  }
  
  .action-buttons {
    flex-direction: column;
  }
  
  .btn {
    width: 100%;
  }
}
</style>

