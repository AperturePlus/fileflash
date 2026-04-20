import http from '../utils/http';
import type { PermissionsList, CreatePermissionRequest, PermissionItem, UpdatePermissionRequest, GetPermissionsRequest } from '../types/permission';

/**
 * 创建权限
 * @param data 权限请求数据
 * @returns 创建的权限信息
 */
export const createPermission = (data: CreatePermissionRequest) => {
  return http.post<PermissionItem>('/permissions', data);
};

/**
 * 获取权限列表
 * @param params 请求参数
 * @returns 权限列表
 */
export const getPermissions = (params: GetPermissionsRequest) => {
  return http.get<PermissionsList>('/permissions', params);
};

/**
 * 更新权限
 * @param permissionId 权限ID
 * @param data 更新请求数据
 * @returns 更新后的权限信息
 */
export const updatePermission = (permissionId: string, data: UpdatePermissionRequest) => {
  return http.put<PermissionItem>(`/permissions/${permissionId}`, data);
};

/**
 * 删除权限
 * @param permissionId 权限ID
 * @returns 删除后的权限信息
 */
export const deletePermission = (permissionId: string) => {
  return http.delete<{ permissionId: string; revokedPermission: string; deletedAt: string }>(`/permissions/${permissionId}`);
}; 
