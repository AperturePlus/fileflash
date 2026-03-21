import http from '../utils/http';
import type { NotificationsList, GetNotificationsRequest, NotificationItem } from '../types/notification';

export const getNotifications = (params: GetNotificationsRequest) => {
  return http.get<NotificationsList>('/notifications', params);
};

export const markAsRead = (notificationId: string) => {
  return http.put<{ notificationId: string; updatedAt: string }>(`/notifications/${notificationId}/read`);
};

export const markAllAsRead = () => {
  return http.put<{ updatedCount: number }>('/notifications/read-all');
};

export const deleteNotification = (notificationId: string) => {
  return http.delete<{ notificationId: string }>(`/notifications/${notificationId}`);
};

export const broadcastNotification = (message: string) => {
  return http.post<NotificationItem>('/notifications/broadcast', { message });
};
