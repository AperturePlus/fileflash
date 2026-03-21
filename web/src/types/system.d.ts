export interface SystemHealth {
  platformTargets: string[];
  maxConcurrentUploads: number;
  activeUploadSessions: number;
  virusScanEnabled: boolean;
  thumbnailGenerationEnabled: boolean;
  registrationMailEnabled: boolean;
  hashComputationEnabled: boolean;
  lastUpdatedAt: string;
}

export interface RateLimitRule {
  ruleId: string;
  scope: string;
  windowSeconds: number;
  limit: number;
  currentUsage: number;
  blockedRequests: number;
}

export interface RateLimitStatus {
  rules: RateLimitRule[];
  evaluatedAt: string;
}
