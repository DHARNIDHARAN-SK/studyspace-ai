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

// Conversation and Messages (Section 10)
export interface Citation {
  id: string;
  document_id: string;
  document_title: string;
  page_start?: number;
  page_end?: number;
  slide_number?: number;
  section_path?: string;
  snippet: string;
  similarity_score?: number;
  citation_label?: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  original_user_query?: string;
  rewritten_query?: string;
  citations?: Citation[];
  created_at: string;
  latency_ms?: number;
  model?: string;
}

export interface Conversation {
  id: string;
  project_id: string;
  workspace_id: string;
  title: string;
  is_pinned: boolean;
  status: "active" | "archived";
  created_at: string;
  updated_at: string;
}

// Sources / Documents (Section 6 & 10)
export type IngestionStatus = "uploaded" | "queued" | "extracting" | "chunking" | "processing" | "indexed" | "failed";

export interface ProjectDocument {
  id: string;
  project_id: string;
  workspace_id: string;
  original_filename: string;
  extension: string;
  mime_type: string;
  byte_size: number;
  page_count?: number;
  chunk_count?: number;
  ingestion_status: IngestionStatus;
  ingestion_error_code?: string;
  ingestion_error_message?: string;
  created_at: string;
  indexed_at?: string;
}

// Student Learning Tools (Section 4.4 & 10)
export type RevisionStatus = "not_started" | "learning" | "revised";

export interface RevisionItem {
  id: string;
  project_id: string;
  workspace_id: string;
  title: string;
  description?: string;
  status: RevisionStatus;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface QuizQuestion {
  id: string;
  quiz_id: string;
  question_type: "multiple_choice" | "short_answer" | "challenge";
  difficulty: "easy" | "medium" | "hard";
  prompt: string;
  options?: string[];
  expected_answer?: string; // Hidden on client prior to attempt
  explanation?: string;     // Hidden on client prior to attempt
  position: number;
}

export interface Quiz {
  id: string;
  project_id: string;
  workspace_id: string;
  title: string;
  question_count: number;
  status: "draft" | "ready";
  created_at: string;
  questions?: QuizQuestion[];
}

export interface StudyGuide {
  id: string;
  project_id: string;
  workspace_id: string;
  title: string;
  guide_type: "summary" | "exam_prep" | "definitions";
  content: string;
  created_at: string;
}

// Developer Platform API Keys (Section 4.3 Page 7)
export interface ApiKey {
  id: string;
  workspace_id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  status: "active" | "revoked";
  last_used_at?: string;
  created_at: string;
}
