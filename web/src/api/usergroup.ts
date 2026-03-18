import http from '../utils/http';
import type { UserGroupsList, CreateUserGroupRequest, UserGroup, AddGroupMemberRequest } from '../types/user';

/**
 * 创建用户组
 * @param data 用户组请求数据
 * @returns 创建的用户组信息
 */
export const createUserGroup = (data: CreateUserGroupRequest) => {
  return http.post<UserGroup>('/user-groups', data);
};

/**
 * 获取用户组列表
 * @param params 请求参数
 * @returns 用户组列表
 */
export const getUserGroups = (params: { search?: string; page?: number; perPage?: number }) => {
  return http.get<UserGroupsList>('/user-groups', params);
};

/**
 * 添加用户组成员
 * @param groupId 用户组ID
 * @param data 添加成员请求数据
 * @returns 添加成员后的用户组信息
 */
export const addGroupMember = (groupId: string, data: AddGroupMemberRequest) => {
  return http.post<{ groupId: string; groupName: string; addedUser: any; totalMembers: number }>(`/user-groups/${groupId}/members`, data);
};

/**
 * 移除用户组成员
 * @param groupId 用户组ID
 * @param userId 用户ID
 * @returns 移除成员后的用户组信息
 */
export const removeGroupMember = (groupId: string, userId: string) => {
  return http.delete<{ groupId: string; groupName: string; removedUser: any; remainingMembers: number }>(`/user-groups/${groupId}/members/${userId}`);
}; 