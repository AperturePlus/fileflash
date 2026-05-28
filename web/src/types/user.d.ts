import type { PaginatedData } from './base';

export type UserRole = 'user' | 'admin';
export type UserStatus = 'active' | 'suspended';
export type AppLanguage = 'zh-CN' | 'en-US';

export interface UserPreference {
  language: AppLanguage;
}

export interface User {
  userId: string;
  username: string;
  email: string;
  storageLimit: number;
  storageUsed: number;
  emailVerified: boolean;
  emailVerifiedAt?: string | null;
  createdAt: string;
  role?: UserRole;
  status?: UserStatus;
  preference?: UserPreference;
  avatar?: string | null;
}

export interface AdminUserUsageStats {
  trafficBytes: number;
  agentTokens: number;
}

export interface AdminUserItem {
  userId: string;
  username: string;
  email: string;
  role: 'USER' | 'ADMIN';
  status: UserStatus | 'pending_verification';
  emailVerified: boolean;
  emailVerifiedAt?: string | null;
  storageLimit: number;
  storageUsed: number;
  usagePercentage: number;
  lastLoginAt?: string | null;
  lastActiveAt?: string | null;
  createdAt: string;
  usageStats: AdminUserUsageStats;
}

export interface GetAdminUsersParams {
  page?: number;
  perPage?: number;
  search?: string;
  status?: UserStatus;
  role?: 'USER' | 'ADMIN';
  usageFrom?: string;
  usageTo?: string;
}

export interface LoginResponse {
  token: string;
  tokenType: string;
  expiresIn: number;
  user: User;
}

export interface RefreshTokenResponse {
  token: string;
  tokenType: string;
  expiresIn: number;
  user: User;
}

export interface RegisterResponse {
  user: User;
  emailVerificationRequired: true;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export type UpdateProfileRequest = Partial<Pick<UserProfile, 'username' | 'email'>>;
export type UpdateUserPreferenceRequest = Partial<UserPreference>;

export interface ChangePasswordRequest {
  oldPassword?: string;
  newPassword?: string;
}

export interface UserGroupInfo {
  groupId: string;
  groupName: string;
  role: 'admin' | 'member';
}

export interface UserProfile extends User {
  groups: UserGroupInfo[];
  updatedAt: string;
  lastLogin: string | null;
}

export interface BreakdownDetail {
  size: number;
  count: number;
}

export interface StorageStats {
  storageLimit: number;
  storageUsed: number;
  storageAvailable: number;
  storagePercentage: number;
  fileCount: number;
  folderCount: number;
  breakdown: {
    [key: string]: BreakdownDetail;
  };
}

export interface ActivityItem {
  id: number;
  operation: string;
  details: {
    [key: string]: string | number;
  };
  ipAddress: string;
  performedAt: string;
}

export type ActivityLog = PaginatedData<ActivityItem>;

export interface GetActivityLogRequest {
  page?: number;
  perPage?: number;
  operation?: string;
}

export interface CreateUserGroupRequest {
  name: string;
  description?: string;
}

export interface UserGroup {
  groupId: string;
  name: string;
  description?: string;
  memberCount: number;
  createdAt: string;
}

export interface AddGroupMemberRequest {
  userId: string;
  role: 'member' | 'admin';
}

export type UserGroupsList = PaginatedData<UserGroup>;
