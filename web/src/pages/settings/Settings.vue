<script setup lang="ts">
import { useThemeStore } from '../../store/theme';
import { useSettingsStore } from '../../store/settings';
import { storeToRefs } from 'pinia';
import { ref } from 'vue';

const themeStore = useThemeStore();
const settingsStore = useSettingsStore();
const { theme } = storeToRefs(themeStore);
const { settings } = storeToRefs(settingsStore);

const activeTab = ref('appearance');

const tabs = [
  { id: 'appearance', name: '外观', icon: 'APP' },
  { id: 'uploads', name: '上传', icon: 'UPL' },
  { id: 'files', name: '文件管理', icon: 'FILE' },
  { id: 'notifications', name: '通知', icon: 'NOTE' },
  { id: 'security', name: '安全', icon: 'SAFE' },
  { id: 'advanced', name: '高级', icon: 'ADV' }
];

const resetSettings = () => {
  if (confirm('确定要重置所有设置到默认值吗？此操作无法撤销。')) {
    settingsStore.resetSettings();
  }
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
        alert('设置导入成功！');
      } else {
        alert('设置导入失败，请检查文件格式。');
      }
    };
    reader.readAsText(file);
  }
};
</script>

<template>
  <div class="settings-page">
    <header class="page-header">
      <h1>设置</h1>
      <p>个性化您的 fileflash 体验，管理应用行为和偏好。</p>
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
          <h2 class="section-title">外观设置</h2>
          
          <div class="setting-item">
            <div class="setting-label">
              <h3>主题</h3>
              <p>选择您喜欢的应用主题</p>
            </div>
            <div class="setting-control">
              <div class="theme-switcher">
                <button 
                  class="theme-option" 
                  :class="{ active: theme === 'light' }"
                  @click="themeStore.setTheme('light')"
                >
                  <div class="theme-preview light"></div>
                  <span>浅色</span>
                </button>
                <button 
                  class="theme-option" 
                  :class="{ active: theme === 'dark' }"
                  @click="themeStore.setTheme('dark')"
                >
                  <div class="theme-preview dark"></div>
                  <span>深色</span>
                </button>
              </div>
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-label">
              <h3>紧凑模式</h3>
              <p>减少界面间距，显示更多内容</p>
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
              <h3>默认文件视图</h3>
              <p>选择文件列表的默认显示方式</p>
            </div>
            <div class="setting-control">
              <select 
                v-model="settings.defaultFileView"
                @change="settingsStore.updateSetting('defaultFileView', settings.defaultFileView)"
                class="select-input"
              >
                <option value="list">列表视图</option>
                <option value="grid">网格视图</option>
                <option value="tiles">瓦片视图</option>
              </select>
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-label">
              <h3>显示文件扩展名</h3>
              <p>在文件名中显示文件扩展名</p>
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
          <h2 class="section-title">上传设置</h2>
          
          <div class="setting-item">
            <div class="setting-label">
              <h3>最大并发上传数</h3>
              <p>同时上传的最大文件数量</p>
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
              <h3>分块大小</h3>
              <p>大文件分块上传的块大小 (MB)</p>
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
              <h3>自动重试失败的上传</h3>
              <p>网络错误时自动重试上传</p>
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
              <h3>重试次数</h3>
              <p>上传失败时的最大重试次数</p>
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
          <h2 class="section-title">文件管理设置</h2>
          
          <div class="setting-item">
            <div class="setting-label">
              <h3>每页显示项目数</h3>
              <p>文件列表每页显示的项目数量</p>
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
              <h3>显示隐藏文件</h3>
              <p>显示以点(.)开头的隐藏文件</p>
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
              <h3>自动刷新间隔</h3>
              <p>文件列表自动刷新的时间间隔 (秒，0 表示禁用)</p>
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
              <h3>回收站自动清理</h3>
              <p>回收站中文件的自动删除天数</p>
            </div>
            <div class="setting-control">
              <select 
                v-model.number="settings.autoDeleteDays"
                @change="settingsStore.updateSetting('autoDeleteDays', settings.autoDeleteDays)"
                class="select-input"
              >
                <option :value="7">7 天</option>
                <option :value="14">14 天</option>
                <option :value="30">30 天</option>
                <option :value="60">60 天</option>
                <option :value="90">90 天</option>
              </select>
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-label">
              <h3>删除确认</h3>
              <p>删除文件时显示确认对话框</p>
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
          <h2 class="section-title">通知设置</h2>
          
          <div class="setting-item">
            <div class="setting-label">
              <h3>桌面通知</h3>
              <p>启用系统桌面通知</p>
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
              <h3>声音通知</h3>
              <p>操作完成时播放提示音</p>
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
              <h3>上传完成通知</h3>
              <p>文件上传完成时显示通知</p>
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
              <h3>错误通知</h3>
              <p>发生错误时显示通知</p>
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
          <h2 class="section-title">安全设置</h2>
          
          <div class="setting-item">
            <div class="setting-label">
              <h3>会话超时时间</h3>
              <p>自动登出的空闲时间 (分钟，0 表示禁用)</p>
            </div>
            <div class="setting-control">
              <select 
                v-model.number="settings.sessionTimeout"
                @change="settingsStore.updateSetting('sessionTimeout', settings.sessionTimeout)"
                class="select-input"
              >
                <option :value="0">禁用</option>
                <option :value="30">30 分钟</option>
                <option :value="60">1 小时</option>
                <option :value="120">2 小时</option>
                <option :value="240">4 小时</option>
                <option :value="480">8 小时</option>
              </select>
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-label">
              <h3>敏感操作密码确认</h3>
              <p>执行删除、分享等敏感操作时要求密码确认</p>
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
          <h2 class="section-title">高级设置</h2>
          
          <div class="setting-item">
            <div class="setting-label">
              <h3>调试模式</h3>
              <p>启用详细的调试信息输出</p>
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
              <h3>缓存持续时间</h3>
              <p>本地缓存的保持时间 (小时)</p>
            </div>
            <div class="setting-control">
              <select 
                v-model.number="settings.cacheDuration"
                @change="settingsStore.updateSetting('cacheDuration', settings.cacheDuration)"
                class="select-input"
              >
                <option :value="1">1 小时</option>
                <option :value="6">6 小时</option>
                <option :value="12">12 小时</option>
                <option :value="24">24 小时</option>
                <option :value="72">72 小时</option>
              </select>
            </div>
          </div>

          <div class="setting-actions">
            <h3>设置管理</h3>
            <div class="action-buttons">
              <button @click="exportSettings" class="btn btn-secondary">
                导出设置
              </button>
              <label class="btn btn-secondary">
                导入设置
                <input type="file" accept=".json" @change="importSettings" style="display: none;">
              </label>
              <button @click="resetSettings" class="btn btn-danger">
                重置所有设置
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
