export interface NotificationItem {
  id: number;
  message: string;
  isRead: boolean;
  createdAt: string;
}

export type NotificationsList = PaginatedData<NotificationItem> & {
  unreadCount: number;
  totalCount: number;
};

export interface GetNotificationsRequest {
  page?: number;
  perPage?: number;
  isRead?: boolean;
} 