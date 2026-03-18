import { defineStore } from 'pinia';
import { ref, watch } from 'vue';

export interface AppSettings {
  // 上传设置
  maxConcurrentUploads: number;
  chunkSize: number; // MB
  autoRetryFailedUploads: boolean;
  retryAttempts: number;
  
  // 文件管理设置
  defaultFileView: 'list' | 'grid' | 'tiles';
  itemsPerPage: number;
  showHiddenFiles: boolean;
  autoRefreshInterval: number; // 秒，0 表示禁用
  
  // 回收站设置
  autoDeleteDays: number;
  confirmDelete: boolean;
  
  // 通知设置
  desktopNotifications: boolean;
  soundNotifications: boolean;
  uploadCompleteNotification: boolean;
  errorNotifications: boolean;
  
  // 界面设置
  compactMode: boolean;
  showFileExtensions: boolean;
  previewPanelPosition: 'right' | 'bottom' | 'hidden';
  
  // 安全设置
  sessionTimeout: number; // 分钟，0 表示禁用
  requirePasswordForSensitiveActions: boolean;
  
  // 高级设置
  debugMode: boolean;
  cacheDuration: number; // 小时
}

const DEFAULT_SETTINGS: AppSettings = {
  // 上传设置
  maxConcurrentUploads: 3,
  chunkSize: 5, // 5MB
  autoRetryFailedUploads: true,
  retryAttempts: 3,
  
  // 文件管理设置
  defaultFileView: 'list',
  itemsPerPage: 50,
  showHiddenFiles: false,
  autoRefreshInterval: 30, // 30秒
  
  // 回收站设置
  autoDeleteDays: 30,
  confirmDelete: true,
  
  // 通知设置
  desktopNotifications: true,
  soundNotifications: false,
  uploadCompleteNotification: true,
  errorNotifications: true,
  
  // 界面设置
  compactMode: false,
  showFileExtensions: true,
  previewPanelPosition: 'right',
  
  // 安全设置
  sessionTimeout: 120, // 2小时
  requirePasswordForSensitiveActions: true,
  
  // 高级设置
  debugMode: false,
  cacheDuration: 24, // 24小时
};

const SETTINGS_STORAGE_KEY = 'fileflash-app-settings';

export const useSettingsStore = defineStore('settings', () => {
  const settings = ref<AppSettings>({ ...DEFAULT_SETTINGS });
  
  // 从本地存储加载设置
  function loadSettings() {
    try {
      const stored = localStorage.getItem(SETTINGS_STORAGE_KEY);
      if (stored) {
        const parsedSettings = JSON.parse(stored);
        // 合并默认设置和存储的设置，确保新增的设置项有默认值
        settings.value = { ...DEFAULT_SETTINGS, ...parsedSettings };
      }
    } catch (error) {
      console.error('加载设置失败:', error);
      settings.value = { ...DEFAULT_SETTINGS };
    }
  }
  
  // 保存设置到本地存储
  function saveSettings() {
    try {
      localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings.value));
    } catch (error) {
      console.error('保存设置失败:', error);
    }
  }
  
  // 更新单个设置项
  function updateSetting<K extends keyof AppSettings>(key: K, value: AppSettings[K]) {
    settings.value[key] = value;
    saveSettings();
  }
  
  // 批量更新设置
  function updateSettings(newSettings: Partial<AppSettings>) {
    Object.assign(settings.value, newSettings);
    saveSettings();
  }
  
  // 重置为默认设置
  function resetSettings() {
    settings.value = { ...DEFAULT_SETTINGS };
    saveSettings();
  }
  
  // 导出设置
  function exportSettings(): string {
    return JSON.stringify(settings.value, null, 2);
  }
  
  // 导入设置
  function importSettings(settingsJson: string): boolean {
    try {
      const importedSettings = JSON.parse(settingsJson);
      // 验证导入的设置是否有效
      if (typeof importedSettings === 'object' && importedSettings !== null) {
        settings.value = { ...DEFAULT_SETTINGS, ...importedSettings };
        saveSettings();
        return true;
      }
      return false;
    } catch (error) {
      console.error('导入设置失败:', error);
      return false;
    }
  }
  
  // 监听设置变化并自动保存
  watch(
    settings,
    () => {
      saveSettings();
    },
    { deep: true }
  );
  
  // 初始化时加载设置
  loadSettings();
  
  return {
    settings,
    loadSettings,
    saveSettings,
    updateSetting,
    updateSettings,
    resetSettings,
    exportSettings,
    importSettings,
  };
}); 