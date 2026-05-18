<script setup lang="ts">
import { useUserStore } from '../../store/user';
import { storeToRefs } from 'pinia';
import { ref, onMounted, watch } from 'vue';
import StorageStatus from '../../components/layout/StorageStatus.vue';
import { changePassword, getActivityLog, updateProfile } from '../../api/user';
import type { ActivityItem } from '../../types/user';
import { ui } from '../../utils/ui';

const userStore = useUserStore();
const { user, storageStats } = storeToRefs(userStore);

const activityLog = ref<ActivityItem[]>([]);
const isLoadingActivity = ref(false);
const isSavingProfile = ref(false);
const profileError = ref('');
const isChangingPassword = ref(false);
const passwordError = ref('');

const profileForm = ref({
  username: '',
  email: '',
});

const passwordForm = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
});

// Fetch data on mount
onMounted(async () => {
  await Promise.all([
    userStore.fetchUserProfile(),
    userStore.fetchStorageStats(),
    fetchActivityLog()
  ]);
});

watch(
  () => user.value,
  (nextUser) => {
    if (!nextUser) return;
    profileForm.value.username = nextUser.username || '';
    profileForm.value.email = nextUser.email || '';
  },
  { immediate: true },
);

const fetchActivityLog = async () => {
  try {
    isLoadingActivity.value = true;
    const response = await getActivityLog({ page: 1, perPage: 10 });
    activityLog.value = response.items;
  } catch (error) {
    console.error('Failed to fetch activity log:', error);
  } finally {
    isLoadingActivity.value = false;
  }
};

const getInitials = (name: string) => {
  if (!name) return '';
  const names = name.split(' ');
  return names.map(n => n[0]).join('').toUpperCase();
};

const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

const getActivityIcon = (operation: string) => {
  const iconMap: Record<string, string> = {
    file_upload: 'UP',
    file_download: 'DL',
    file_delete: 'DEL',
    folder_create: 'DIR',
    file_share: 'SHR',
    user_login: 'LOG',
    login: 'LOG'
  };
  return iconMap[operation] || 'EVT';
};

const getActivityText = (activity: ActivityItem) => {
  const actionMap: Record<string, string> = {
    file_upload: '上传了文件',
    file_download: '下载了文件',
    file_delete: '删除了文件',
    folder_create: '创建了文件夹',
    file_share: '分享了文件',
    user_login: '登录系统',
    login: '登录系统'
  };
  
  // 如果有详细信息中的 message，优先使用它
  if (activity.details.message) {
    return activity.details.message;
  }
  
  return actionMap[activity.operation] || '执行了操作';
};

const getBrowserName = (userAgent: string) => {
  if (userAgent.includes('Chrome')) return 'Chrome';
  if (userAgent.includes('Firefox')) return 'Firefox';
  if (userAgent.includes('Safari')) return 'Safari';
  if (userAgent.includes('Edge')) return 'Edge';
  if (userAgent.includes('Opera')) return 'Opera';
  if (userAgent.includes('MSIE') || userAgent.includes('Trident')) return 'Internet Explorer';
  return '未知浏览器';
};

const getActivityUserAgent = (activity: ActivityItem) => {
  const value = activity.details.user_agent;
  return typeof value === 'string' ? value : '';
};

const saveProfile = async () => {
  if (!profileForm.value.username.trim() || !profileForm.value.email.trim()) {
    profileError.value = '用户名和邮箱不能为空';
    return;
  }

  profileError.value = '';
  isSavingProfile.value = true;
  try {
    const updated = await updateProfile({
      username: profileForm.value.username.trim(),
      email: profileForm.value.email.trim(),
    });
    userStore.setUser(updated);
    ui.toast({ type: 'success', message: '个人资料已更新' });
  } catch (error) {
    profileError.value = error instanceof Error ? error.message : '个人资料更新失败';
  } finally {
    isSavingProfile.value = false;
  }
};

const submitPassword = async () => {
  if (!passwordForm.value.oldPassword || !passwordForm.value.newPassword) {
    passwordError.value = '请填写旧密码和新密码';
    return;
  }
  if (passwordForm.value.newPassword.length < 6) {
    passwordError.value = '新密码至少 6 位';
    return;
  }
  if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
    passwordError.value = '两次输入的新密码不一致';
    return;
  }

  passwordError.value = '';
  isChangingPassword.value = true;
  try {
    await changePassword({
      oldPassword: passwordForm.value.oldPassword,
      newPassword: passwordForm.value.newPassword,
    });
    passwordForm.value.oldPassword = '';
    passwordForm.value.newPassword = '';
    passwordForm.value.confirmPassword = '';
    ui.toast({ type: 'success', message: '密码已修改' });
  } catch (error) {
    passwordError.value = error instanceof Error ? error.message : '密码修改失败';
  } finally {
    isChangingPassword.value = false;
  }
};
</script>

<template>
  <div class="profile-page">
    <header class="page-header">
      <h1>个人资料</h1>
      <p>查看和管理您的账户信息</p>
    </header>

    <div class="profile-content">
      <!-- 用户信息卡片 -->
      <div class="profile-card card">
        <div class="card-header">
          <div class="avatar-container">
            <div class="avatar">
              <span>{{ getInitials(user?.username || 'U') }}</span>
            </div>
            <div class="avatar-badge">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24"><path fill="currentColor" d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5z"/></svg>
            </div>
          </div>
          <div class="user-info">
            <h2 class="username">{{ user?.username }}</h2>
            <p class="email">{{ user?.email }}</p>
            <div class="user-meta">
              <span class="meta-item">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24"><path fill="currentColor" d="M9 11H7v6h2zm4 0h-2v6h2zm4 0h-2v6h2zm2-7h-3V2a1 1 0 0 0-1-1H9a1 1 0 0 0-1 1v2H5a1 1 0 0 0 0 2h1v11a3 3 0 0 0 3 3h6a3 3 0 0 0 3-3V6h1a1 1 0 0 0 0-2M10 4h4v1h-4z"/></svg>
                加入于 {{ user ? new Date(user.createdAt).toLocaleDateString('zh-CN') : 'N/A' }}
              </span>
              <span class="meta-item">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24"><path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2M7 13.5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5m5 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5m5 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5"/></svg>
                                 上次登录 {{ (user && 'lastLogin' in user && user.lastLogin) ? new Date(user.lastLogin).toLocaleString('zh-CN') : 'N/A' }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div class="profile-edit-card card">
        <div class="card-header">
          <h3 class="card-title">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24"><path fill="currentColor" d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75zM20.71 7.04a1 1 0 0 0 0-1.41L18.37 3.29a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75z"/></svg>
            编辑资料
          </h3>
        </div>
        <div class="card-body profile-form">
          <label>
            <span>用户名</span>
            <input v-model="profileForm.username" type="text" autocomplete="username">
          </label>
          <label>
            <span>邮箱</span>
            <input v-model="profileForm.email" type="email" autocomplete="email">
          </label>
          <p v-if="profileError" class="error-text">{{ profileError }}</p>
          <button class="primary-btn" :disabled="isSavingProfile" @click="saveProfile">
            {{ isSavingProfile ? '保存中...' : '保存资料' }}
          </button>
        </div>
      </div>

      <div class="password-card card">
        <div class="card-header">
          <h3 class="card-title">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24"><path fill="currentColor" d="M12 17a2 2 0 0 0 2-2v-3a2 2 0 0 0-4 0v3a2 2 0 0 0 2 2m6-7h-1V8a5 5 0 1 0-10 0v2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8a2 2 0 0 0-2-2m-9-2a3 3 0 0 1 6 0v2H9z"/></svg>
            修改密码
          </h3>
        </div>
        <div class="card-body profile-form">
          <label>
            <span>旧密码</span>
            <input v-model="passwordForm.oldPassword" type="password" autocomplete="current-password">
          </label>
          <label>
            <span>新密码</span>
            <input v-model="passwordForm.newPassword" type="password" autocomplete="new-password">
          </label>
          <label>
            <span>确认新密码</span>
            <input v-model="passwordForm.confirmPassword" type="password" autocomplete="new-password">
          </label>
          <p v-if="passwordError" class="error-text">{{ passwordError }}</p>
          <button class="primary-btn" :disabled="isChangingPassword" @click="submitPassword">
            {{ isChangingPassword ? '提交中...' : '更新密码' }}
          </button>
        </div>
      </div>

      <!-- 存储使用情况 -->
      <div class="storage-card card">
        <div class="card-header">
          <h3 class="card-title">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24"><path fill="currentColor" d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2m-1 9H9V9h10zm-4 4H9v-2h6zm4-8H9V5h10z"/></svg>
            存储使用情况
          </h3>
        </div>
        <div class="card-body">
          <StorageStatus v-if="storageStats" :stats="storageStats" />
          <div v-else class="loading-indicator">
            <div class="loading-spinner"></div>
            正在加载存储数据...
          </div>
        </div>
      </div>

             <!-- 用户组信息 -->
       <div v-if="user && 'groups' in user && user.groups && user.groups.length > 0" class="groups-card card">
        <div class="card-header">
          <h3 class="card-title">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24"><path fill="currentColor" d="M16 4c0-1.11.89-2 2-2s2 .89 2 2-.89 2-2 2-2-.89-2-2M4 18v-6h3v-2c0-1.1.9-2 2-2h2c1.1 0 2 .9 2 2v2h3v6c0 1.1-.9 2-2 2H6c-1.1 0-2-.9-2-2m12.5-11.5c.83 0 1.5-.67 1.5-1.5s-.67-1.5-1.5-1.5-1.5.67-1.5 1.5.67 1.5 1.5 1.5M11 16.5h2.5l.9 2.1c.2.4.6.4 1 .4s.8-.2 1-.6L18 14h-1.5l-1.3 3.1L13.5 15H10l1 1.5m7.5-9.5c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2M12.5 11.5c.83 0 1.5-.67 1.5-1.5s-.67-1.5-1.5-1.5-1.5.67-1.5 1.5.67 1.5 1.5 1.5"/></svg>
            用户组
          </h3>
        </div>
        <div class="card-body">
                     <div class="groups-list">
             <div v-for="group in (user && 'groups' in user ? user.groups : [])" :key="group.groupId" class="group-item">
              <div class="group-info">
                <h4 class="group-name">{{ group.groupName }}</h4>
                <span class="group-role" :class="'role-' + group.role">
                  {{ group.role === 'admin' ? '管理员' : '成员' }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 最近活动 -->
      <div class="activity-card card">
        <div class="card-header">
          <h3 class="card-title">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24"><path fill="currentColor" d="M14 12c0 1.1-.9 2-2 2s-2-.9-2-2 .9-2 2-2 2 .9 2 2M12 3c-4.97 0-9 4.03-9 9s4.03 9 9 9 9-4.03 9-9-4.03-9-9-9m0 16c-3.86 0-7-3.14-7-7s3.14-7 7-7 7 3.14 7 7-3.14 7-7 7"/></svg>
            最近活动
          </h3>
        </div>
        <div class="card-body">
          <div v-if="isLoadingActivity" class="loading-indicator">
            <div class="loading-spinner"></div>
            正在加载活动记录...
          </div>
          <div v-else-if="activityLog.length === 0" class="empty-state">
            <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24"><path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2M7 13.5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5m5 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5m5 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5"/></svg>
            <p>暂无活动记录</p>
          </div>
          <div v-else class="activity-list">
            <div v-for="activity in activityLog" :key="activity.id" class="activity-item">
              <div class="activity-icon">
                {{ getActivityIcon(activity.operation) }}
              </div>
              <div class="activity-content">
                <div class="activity-text">
                  {{ getActivityText(activity) }}
                  <span v-if="activity.details.fileName" class="activity-target">
                    {{ activity.details.fileName }}
                  </span>
                </div>
                <div class="activity-meta">
                  <span class="activity-time">{{ new Date(activity.performedAt).toLocaleString('zh-CN') }}</span>
                  <span class="activity-ip">{{ activity.ipAddress }}</span>
                  <span v-if="getActivityUserAgent(activity)" class="activity-browser" :title="getActivityUserAgent(activity)">
                    {{ getBrowserName(getActivityUserAgent(activity)) }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 账户统计 -->
      <div v-if="storageStats" class="stats-card card">
        <div class="card-header">
          <h3 class="card-title">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24"><path fill="currentColor" d="M3 13h8V3H3zm0 8h8v-6H3zm10 0h8V11h-8zm0-18v6h8V3z"/></svg>
            账户统计
          </h3>
        </div>
        <div class="card-body">
          <div class="stats-grid">
            <div class="stat-item">
              <div class="stat-value">{{ storageStats.fileCount.toLocaleString() }}</div>
              <div class="stat-label">文件总数</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ storageStats.folderCount.toLocaleString() }}</div>
              <div class="stat-label">文件夹数</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ formatFileSize(storageStats.storageUsed) }}</div>
              <div class="stat-label">已用空间</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ Math.round(storageStats.storagePercentage) }}%</div>
              <div class="stat-label">使用率</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.profile-page {
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

.profile-content {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: var(--spacing-lg);
}

.card {
  background-color: var(--color-bg-secondary);
  border-radius: var(--border-radius-lg);
  padding: var(--spacing-xl);
  box-shadow: var(--shadow-sm);
  transition: box-shadow var(--transition-base);
}

.card:hover {
  box-shadow: var(--shadow-md);
}

.profile-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.profile-form label {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.profile-form input {
  height: 38px;
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius-md);
  background-color: var(--color-bg-primary);
  color: var(--color-text-primary);
  padding: 0 var(--spacing-md);
}

.profile-form input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.primary-btn {
  height: 36px;
  border: none;
  border-radius: var(--border-radius-md);
  background-color: var(--color-primary);
  color: var(--color-text-on-primary);
  cursor: pointer;
}

.primary-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-text {
  color: var(--color-danger, #dc2626);
  font-size: 0.875rem;
}

.card-header {
  margin-bottom: var(--spacing-lg);
}

.card-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: 1.2rem;
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.card-title svg {
  color: var(--color-primary);
}

/* Profile Card */
.profile-card .card-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
  border-bottom: 1px solid var(--color-border);
  padding-bottom: var(--spacing-lg);
}

.avatar-container {
  position: relative;
}

.avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary), var(--color-secondary, #10b981));
  color: var(--color-text-on-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  font-weight: var(--font-weight-bold);
  box-shadow: var(--shadow-md);
}

.avatar-badge {
  position: absolute;
  bottom: -2px;
  right: -2px;
  width: 28px;
  height: 28px;
  background-color: var(--color-success, #10b981);
  border: 3px solid var(--color-bg-secondary);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.username {
  font-size: 1.5rem;
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-xs) 0;
}

.email {
  font-size: 1rem;
  color: var(--color-text-secondary);
  margin: 0 0 var(--spacing-md) 0;
}

.user-meta {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: 0.875rem;
  color: var(--color-text-tertiary);
}

.meta-item svg {
  color: var(--color-text-quaternary);
}

/* Groups Card */
.groups-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.group-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md);
  background-color: var(--color-bg-tertiary);
  border-radius: var(--border-radius-md);
  border: 1px solid var(--color-border);
}

.group-name {
  font-size: 1rem;
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  margin: 0;
}

.group-role {
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--border-radius-sm);
  font-size: 0.75rem;
  font-weight: var(--font-weight-medium);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.role-admin {
  background-color: rgba(239, 68, 68, 0.1);
  color: #dc2626;
}

.role-member {
  background-color: rgba(59, 130, 246, 0.1);
  color: #2563eb;
}

/* Activity Card */
.activity-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  max-height: 400px;
  overflow-y: auto;
}

.activity-item {
  display: flex;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  background-color: var(--color-bg-tertiary);
  border-radius: var(--border-radius-md);
  border: 1px solid var(--color-border);
  transition: background-color var(--transition-base);
}

.activity-item:hover {
  background-color: var(--color-bg-quaternary);
}

.activity-icon {
  font-size: 1.5rem;
  line-height: 1;
  flex-shrink: 0;
}

.activity-content {
  flex: 1;
  min-width: 0;
}

.activity-text {
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-xs);
}

.activity-target {
  font-weight: var(--font-weight-medium);
  color: var(--color-primary);
}

.activity-meta {
  display: flex;
  gap: var(--spacing-md);
  font-size: 0.75rem;
  color: var(--color-text-tertiary);
  flex-wrap: wrap;
}

.activity-browser {
  cursor: help;
}

/* Stats Card */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-lg);
}

.stat-item {
  text-align: center;
  padding: var(--spacing-md);
  background-color: var(--color-bg-tertiary);
  border-radius: var(--border-radius-md);
  border: 1px solid var(--color-border);
}

.stat-value {
  font-size: 1.5rem;
  font-weight: var(--font-weight-bold);
  color: var(--color-primary);
  margin-bottom: var(--spacing-xs);
}

.stat-label {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

/* Loading and Empty States */
.loading-indicator, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-md);
  padding: var(--spacing-xl);
  text-align: center;
  color: var(--color-text-secondary);
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.empty-state svg {
  color: var(--color-text-quaternary);
}

/* Responsive Design */
@media (max-width: 768px) {
  .profile-content {
    grid-template-columns: 1fr;
  }
  
  .profile-card .card-header {
    flex-direction: column;
    text-align: center;
    gap: var(--spacing-md);
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .activity-meta {
    flex-direction: column;
    gap: var(--spacing-xs);
  }
  
  .user-meta {
    align-items: center;
  }
}

@media (max-width: 480px) {
  .profile-page {
    padding: var(--spacing-md);
  }
  
  .card {
    padding: var(--spacing-lg);
  }
  
  .avatar {
    width: 60px;
    height: 60px;
    font-size: 1.5rem;
  }
  
  .username {
    font-size: 1.25rem;
  }
  
  .activity-list {
    max-height: 300px;
  }
}
</style> 
