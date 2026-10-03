export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
  timestamp: string;
}

export interface ApiError {
  code: string;
  message: string;
  action?: string;
  details?: Record<string, unknown>;
}
