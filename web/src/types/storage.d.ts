// 存储统计已在user.d.ts中定义，此处无需重复
// 如需扩展，可添加

export interface StorageUsageTrend {
  // 根据文档添加，如果有具体结构
  trends: Array<{ date: string; used: number }>;
}

export interface GetUsageTrendRequest {
  days?: number;
} 