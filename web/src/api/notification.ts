import http from '../utils/http';
import type { NotificationsList, GetNotificationsRequest } from '../types/notification';

export const getNotifications = (params: GetNotificationsRequest) => {
  return http.get<NotificationsList>('/notifications', params);
};

export const markAsRead = (notificationId: string | number) => {
  return http.put<{ notificationId: string; updatedAt: string }>(`/notifications/${notificationId}/read`);
};

export const markAllAsRead = () => {
  return http.put<{ updatedCount: number }>('/notifications/read-all');
};

export const deleteNotification = (notificationId: string | number) => {
  return http.delete<{ notificationId: string }>(`/notifications/${notificationId}`);
};

export const broadcastNotification = (message: string, title?: string) => {
  return http.post<{ broadcastId: string; recipientCount: number; sentAt: string }>(
    '/admin/notifications/broadcast',
    { message, title, type: 'system' },
  );
};

export const getAdminNotifications = (params: {
  page?: number;
  perPage?: number;
  status?: string;
  type?: string;
}) => {
  return http.get<NotificationsList>('/admin/notifications', params);
};

export const archiveAdminNotification = (notificationId: string | number) => {
  return http.delete<{ notificationId: string; status: string }>(
    `/admin/notifications/${notificationId}`,
  );
};

