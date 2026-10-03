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

export interface UserProfile {
  id: string;
  email: string | null;
  display_name: string | null;
  avatar_url: string | null;
  workspace_id: string;
  workspace_name: string;
  created_at?: string;
  updated_at?: string;
}

export interface Project {
  id: string;
  workspace_id: string;
  name: string;
  description: string | null;
  subject: string | null;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

export interface ProjectCreateInput {
  name: string;
  description?: string;
  subject?: string;
}

export interface ProjectUpdateInput {
  name?: string;
  description?: string;
  subject?: string;
  is_archived?: boolean;
}
