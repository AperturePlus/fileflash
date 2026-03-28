import http from '../utils/http';
import type { 
    RegisterRequest, 
    LoginRequest, 
    LoginResponse, 
    RefreshTokenResponse,
    UserProfile, 
    UpdateProfileRequest, 
    UpdateUserPreferenceRequest,
    UserPreference,
    ChangePasswordRequest, 
    StorageStats, 
    ActivityLog,
    GetActivityLogRequest,
    User
} from '../types/user';
import type { PaginatedData } from '../types/base';

// 转换后端下划线命名为前端驼峰命名的数据转换函数
function convertStorageStatsFields(data: any): StorageStats {
  return {
    storageLimit: data.storage_limit,
    storageUsed: data.storage_used,
    storageAvailable: data.storage_available,
    storagePercentage: data.storage_percentage,
    fileCount: data.file_count,
    folderCount: data.folder_count,
    breakdown: data.breakdown || {}
  };
}

// 转换活动日志数据格式
function convertActivityLogData(data: any): ActivityLog {
  // 转换分页信息
  const pagination = {
    totalItems: data.pagination.total_items,
    totalPages: data.pagination.total_pages,
    perPage: data.pagination.per_page,
    currentPage: data.pagination.current_page,
    hasPrev: data.pagination.has_prev,
    hasNext: data.pagination.has_next,
  };

  // 转换活动日志项
  const items = data.items.map((item: any) => ({
    id: item.id,
    operation: item.operation,
    details: item.details,
    ipAddress: item.ip_address,
    performedAt: convertArrayToDateString(item.performed_at)
  }));

  return {
    items,
    pagination
  };
}

// 将后端返回的日期数组转换为标准日期字符串
function convertArrayToDateString(dateArray: number[]): string {
  if (Array.isArray(dateArray) && dateArray.length >= 6) {
    // dateArray格式: [年, 月, 日, 时, 分, 秒]
    // 注意：月份需要减1，因为JavaScript的月份是0-11
    const [year, month, day, hour, minute, second] = dateArray;
    const date = new Date(year, month - 1, day, hour, minute, second);
    return date.toISOString();
  }
  return new Date().toISOString(); // fallback
}

/**
 * 用户注册
 * @param data 注册信息
 */
export const register = (data: RegisterRequest) => {
  return http.post<UserProfile>('/auth/register', data);
};

/**
 * 找回密码 - 发送重置邮件
 * @param email 邮箱地址
 */
export const forgotPassword = (email: string) => {
  return http.post<{ requestId: string; expiresInMinutes: number }>('/auth/forgot-password', { email });
};

/**
 * 重置密码
 * @param token 重置令牌
 * @param newPassword 新密码
 */
export const resetPassword = (token: string, newPassword: string) => {
  return http.post<void>('/auth/reset-password', { token, newPassword });
};

/**
 * 用户登录
 * @param data 登录凭据
 * @returns 登录响应数据
 */
export const login = (data: LoginRequest) => {
  return http.post<LoginResponse>('/auth/login', data);
};

/**
 * 用户登出
 * @returns 登出响应数据
 */
export const logout = () => {
  return http.post<void>('/auth/logout');
};

/**
 * 刷新访问令牌
 * @returns 新的令牌信息
 */
export const refreshToken = () => {
  return http.post<RefreshTokenResponse>('/auth/refresh');
};

/**
 * 获取当前用户的完整个人信息
 * @returns 用户个人信息
 */
export const getProfile = () => {
  return http.get<UserProfile>('/me/profile');
};

/**
 * 更新当前用户的个人信息
 * @param data 要更新的信息
 * @returns 更新后的个人信息
 */
export const updateProfile = (data: UpdateProfileRequest) => {
  return http.put<UserProfile>('/me/update-profile', data);
};

/**
 * 获取当前用户偏好
 * @returns 用户偏好
 */
export const getPreference = () => {
  return http.get<UserPreference>('/me/preferences');
};

/**
 * 更新当前用户偏好
 * @param data 偏好变更
 * @returns 更新后的用户偏好
 */
export const updatePreference = (data: UpdateUserPreferenceRequest) => {
  return http.put<UserPreference>('/me/preferences', data);
};

/**
 * 修改当前用户的密码
 * @param data 新旧密码
 * @returns 更新后的密码
 */
export const changePassword = (data: ChangePasswordRequest) => {
  return http.put<void>('/me/password', data);
};

/**
 * 获取用户的存储空间统计信息
 * @returns 存储空间统计信息
 */
export const getStorageStats = async () => {
  const rawData = await http.get<any>('/storage/statistics');
  return convertStorageStatsFields(rawData);
};

/**
 * 获取用户的活动日志
 * @param params 查询参数 (分页、操作类型等)
 * @returns 活动日志
 */
export const getActivityLog = async (params: GetActivityLogRequest) => {
  const rawData = await http.get<any>('/me/activity-log', params);
  return convertActivityLogData(rawData);
};

/**
 * 获取用户列表 (可用于搜索)
 * @param params 查询参数 (搜索关键词、分页等)
 * @returns 用户列表
 */
export const getUsers = (params: { search?: string; page?: number; perPage?: number }) => {
  return http.get<PaginatedData<User>>('/users', params);
};

export const getAdminUsers = (params: { page?: number; perPage?: number }) => {
  return http.get<PaginatedData<any>>('/admin/users', params);
};

export const updateUserStatus = (userId: string, status: 'active' | 'suspended') => {
  return http.patch<{ userId: string; status: string; updatedAt: string }>(`/admin/users/${userId}/status`, { status });
};

export const getViolations = () => {
  return http.get<PaginatedData<any>>('/admin/violations');
};

export const resolveViolation = (violationId: string) => {
  return http.post<{ violationId: string; resolvedAt: string }>(`/admin/violations/${violationId}/resolve`);
};
