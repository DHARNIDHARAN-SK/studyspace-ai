import type {
  ApiKey,
  ApiKeyCreateInput,
  ApiKeyCreatedResult,
  ContactInquiryInput,
  Conversation,
  DeveloperAccessRequestInput,
  EmailDeliveryResponse,
  HealthResponse,
  Message,
  Project,
  ProjectCreateInput,
  ProjectDocument,
  ProjectUpdateInput,
  RevisionItem,
  RevisionStatus,
  StudyGuide,
  UserProfile,
} from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

async function fetchWithAuth<T>(
  path: string,
  token: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Authorization", `Bearer ${token}`);
  if (options.body && typeof options.body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorMsg = `Request failed (${response.status})`;
    try {
      const errorData = await response.json();
      if (errorData.error?.message) {
        errorMsg = errorData.error.message;
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(errorMsg);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export async function checkBackendHealth(): Promise<HealthResponse> {
  const url = `${API_BASE_URL}/api/v1/health`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Health check failed with status: ${response.status}`);
  }
  return response.json();
}

export async function getProfile(token: string): Promise<UserProfile> {
  return fetchWithAuth<UserProfile>("/api/v1/me", token);
}

export async function listProjects(token: string): Promise<Project[]> {
  const res = await fetchWithAuth<{ projects: Project[]; total: number }>(
    "/api/v1/projects",
    token
  );
  return res.projects;
}

export async function getProject(token: string, projectId: string): Promise<Project> {
  return fetchWithAuth<Project>(`/api/v1/projects/${projectId}`, token);
}

export async function createProject(
  token: string,
  input: ProjectCreateInput
): Promise<Project> {
  return fetchWithAuth<Project>("/api/v1/projects", token, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function updateProject(
  token: string,
  projectId: string,
  input: ProjectUpdateInput
): Promise<Project> {
  return fetchWithAuth<Project>(`/api/v1/projects/${projectId}`, token, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export async function deleteProject(token: string, projectId: string): Promise<void> {
  await fetchWithAuth<void>(`/api/v1/projects/${projectId}`, token, {
    method: "DELETE",
  });
}

// -----------------------------------------------------------------------------
// Document Ingestion API (Phase 5)
// -----------------------------------------------------------------------------
export async function listDocuments(token: string, projectId: string): Promise<ProjectDocument[]> {
  const res = await fetchWithAuth<{ documents: ProjectDocument[]; total: number }>(
    `/api/v1/projects/${projectId}/documents`,
    token
  );
  return res.documents;
}

export async function uploadDocument(
  token: string,
  projectId: string,
  file: File
): Promise<{ document: ProjectDocument; job_id: string; status: string; message: string }> {
  const formData = new FormData();
  formData.append("file", file);

  const headers = new Headers();
  headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_BASE_URL}/api/v1/projects/${projectId}/documents`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!response.ok) {
    let errorMsg = `Upload failed (${response.status})`;
    try {
      const errorData = await response.json();
      if (errorData.error?.message) {
        errorMsg = errorData.error.message;
      }
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }

  return response.json();
}

export async function getDocument(
  token: string,
  projectId: string,
  documentId: string
): Promise<ProjectDocument> {
  return fetchWithAuth<ProjectDocument>(
    `/api/v1/projects/${projectId}/documents/${documentId}`,
    token
  );
}

export async function retryDocument(
  token: string,
  projectId: string,
  documentId: string
): Promise<ProjectDocument> {
  return fetchWithAuth<ProjectDocument>(
    `/api/v1/projects/${projectId}/documents/${documentId}/retry`,
    token,
    { method: "POST" }
  );
}

export async function deleteDocument(
  token: string,
  projectId: string,
  documentId: string
): Promise<void> {
  await fetchWithAuth<void>(
    `/api/v1/projects/${projectId}/documents/${documentId}`,
    token,
    { method: "DELETE" }
  );
}

// -----------------------------------------------------------------------------
// Baseline RAG & Chat API (Phase 6)
// -----------------------------------------------------------------------------
export interface ChatQueryPayload {
  query: string;
  conversation_id?: string;
  top_k?: number;
  document_ids?: string[];
  effort?: "simple" | "medium" | "hard";
  mode?: "baseline" | "advanced" | "conversational";
  rewrite_enabled?: boolean;
  selected_query?: string;
  rewrite_accepted?: boolean;
  multi_query_enabled?: boolean;
  decomposition_enabled?: boolean;
}

export interface RewritePreviewPayload {
  query: string;
  conversation_id?: string;
}

export interface RewritePreviewResponse {
  original_query: string;
  rewritten_query: string;
  was_rewritten: boolean;
  latency_ms: number;
  reason?: string;
}

export interface ChatQueryResponse {
  conversation_id: string;
  message: Message;
  metrics: {
    total_latency_ms: number;
    retrieval_latency_ms: number;
    generation_latency_ms: number;
    retrieved_chunks: number;
    model: string;
    embedding_model: string;
    retrieval_mode?: string;
    dense_latency_ms?: number;
    lexical_latency_ms?: number;
    fusion_latency_ms?: number;
    rerank_latency_ms?: number;
    dense_candidates?: number;
    lexical_candidates?: number;
    fused_candidates?: number;
    cache_hit?: boolean;
    cached_query?: string;
    cache_latency_ms?: number;
    rewrite_latency_ms?: number;
    rewrite_enabled?: boolean;
    rewrite_accepted?: boolean;
    rewritten_query?: string;
    selected_query?: string;
    multi_query_enabled?: boolean;
    generated_queries?: string[];
  };
}

export async function previewQueryRewrite(
  token: string,
  projectId: string,
  payload: RewritePreviewPayload
): Promise<RewritePreviewResponse> {
  return fetchWithAuth<RewritePreviewResponse>(
    `/api/v1/projects/${projectId}/chat/rewrite`,
    token,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function sendChatMessage(
  token: string,
  projectId: string,
  payload: ChatQueryPayload
): Promise<ChatQueryResponse> {
  return fetchWithAuth<ChatQueryResponse>(
    `/api/v1/projects/${projectId}/chat`,
    token,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function listConversations(
  token: string,
  projectId: string
): Promise<Conversation[]> {
  const res = await fetchWithAuth<{ conversations: Conversation[]; total: number }>(
    `/api/v1/projects/${projectId}/conversations`,
    token
  );
  return res.conversations;
}

export async function getConversationMessages(
  token: string,
  projectId: string,
  conversationId: string
): Promise<Message[]> {
  const res = await fetchWithAuth<{ messages: Message[]; total: number }>(
    `/api/v1/projects/${projectId}/conversations/${conversationId}/messages`,
    token
  );
  return res.messages;
}

// -----------------------------------------------------------------------------
// Student Study Features API (Phase 10)
// -----------------------------------------------------------------------------

export interface RevisionProgressStats {
  total_items: number;
  not_started: number;
  learning: number;
  revised: number;
  completion_percentage: number;
}

export interface RevisionListResponse {
  items: RevisionItem[];
  stats: RevisionProgressStats;
}

export async function listRevisionItems(
  token: string,
  projectId: string,
  status?: string
): Promise<RevisionListResponse> {
  const query = status && status !== "all" ? `?status=${encodeURIComponent(status)}` : "";
  return fetchWithAuth<RevisionListResponse>(
    `/api/v1/projects/${projectId}/revision${query}`,
    token
  );
}

export async function createRevisionItem(
  token: string,
  projectId: string,
  payload: { title: string; description?: string; status?: RevisionStatus; notes?: string }
): Promise<RevisionItem> {
  return fetchWithAuth<RevisionItem>(
    `/api/v1/projects/${projectId}/revision`,
    token,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function updateRevisionItem(
  token: string,
  projectId: string,
  itemId: string,
  payload: { title?: string; description?: string; status?: RevisionStatus; notes?: string }
): Promise<RevisionItem> {
  return fetchWithAuth<RevisionItem>(
    `/api/v1/projects/${projectId}/revision/${itemId}`,
    token,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    }
  );
}

export async function deleteRevisionItem(
  token: string,
  projectId: string,
  itemId: string
): Promise<void> {
  await fetchWithAuth<void>(
    `/api/v1/projects/${projectId}/revision/${itemId}`,
    token,
    { method: "DELETE" }
  );
}

// Study Guides
export async function listStudyGuides(
  token: string,
  projectId: string
): Promise<{ guides: StudyGuide[]; total: number }> {
  return fetchWithAuth<{ guides: StudyGuide[]; total: number }>(
    `/api/v1/projects/${projectId}/guides`,
    token
  );
}

export async function generateStudyGuide(
  token: string,
  projectId: string,
  payload: { topic: string; guide_type?: string; focus_areas?: string[] }
): Promise<StudyGuide> {
  return fetchWithAuth<StudyGuide>(
    `/api/v1/projects/${projectId}/guides/generate`,
    token,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

// Quizzes
export interface QuizPublicQuestion {
  id: string;
  quiz_id: string;
  question_type: string;
  difficulty: string;
  prompt: string;
  options?: string[];
  position: number;
}

export interface QuizPublic {
  id: string;
  workspace_id: string;
  project_id: string;
  title: string;
  status: string;
  created_at: string;
  questions: QuizPublicQuestion[];
}

export interface QuestionResult {
  question_id: string;
  prompt: string;
  question_type: string;
  submitted_answer: string;
  expected_answer: string;
  is_correct: boolean;
  explanation: string;
  feedback: string;
  source_citations: any[];
}

export interface QuizAttemptResult {
  attempt_id: string;
  quiz_id: string;
  score: number;
  total_questions: number;
  correct_count: number;
  percentage: number;
  started_at: string;
  completed_at: string;
  results: QuestionResult[];
}

export async function listQuizzes(
  token: string,
  projectId: string
): Promise<{ quizzes: QuizPublic[]; total: number }> {
  return fetchWithAuth<{ quizzes: QuizPublic[]; total: number }>(
    `/api/v1/projects/${projectId}/quizzes`,
    token
  );
}

export async function generateQuiz(
  token: string,
  projectId: string,
  payload: { title?: string; topic?: string; num_questions?: number; difficulty?: string }
): Promise<QuizPublic> {
  return fetchWithAuth<QuizPublic>(
    `/api/v1/projects/${projectId}/quizzes/generate`,
    token,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function submitQuizAttempt(
  token: string,
  projectId: string,
  quizId: string,
  answers: { question_id: string; submitted_answer: string }[]
): Promise<QuizAttemptResult> {
  return fetchWithAuth<QuizAttemptResult>(
    `/api/v1/projects/${projectId}/quizzes/${quizId}/attempts`,
    token,
    {
      method: "POST",
      body: JSON.stringify({ responses: answers }),
    }
  );
}

// Export
export interface ExportResult {
  id: string;
  source_type: string;
  source_id: string;
  format: string;
  status: string;
  content?: string;
  filename: string;
  created_at: string;
}

export async function exportContent(
  token: string,
  projectId: string,
  payload: { source_type: "study_guide" | "quiz" | "revision"; source_id: string; format?: "markdown" | "txt" | "pdf" | "docx" }
): Promise<ExportResult> {
  return fetchWithAuth<ExportResult>(
    `/api/v1/projects/${projectId}/export`,
    token,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

// -----------------------------------------------------------------------------
// Developer Platform API (Phase 11)
// -----------------------------------------------------------------------------
export async function listApiKeys(token: string): Promise<ApiKey[]> {
  const res = await fetchWithAuth<{ keys: ApiKey[]; total: number }>(
    "/api/v1/developer/keys",
    token
  );
  return res.keys;
}

export async function submitDeveloperAccessRequest(
  token: string,
  payload: DeveloperAccessRequestInput
): Promise<EmailDeliveryResponse> {
  return fetchWithAuth<EmailDeliveryResponse>(
    "/api/v1/developer/requests",
    token,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function createApiKey(
  token: string,
  payload: ApiKeyCreateInput
): Promise<ApiKeyCreatedResult> {
  return fetchWithAuth<ApiKeyCreatedResult>(
    "/api/v1/developer/keys",
    token,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function revokeApiKey(token: string, keyId: string): Promise<void> {
  await fetchWithAuth<void>(
    `/api/v1/developer/keys/${keyId}`,
    token,
    {
      method: "DELETE",
    }
  );
}

export async function getUsageSummary(
  token: string
): Promise<{ total_events: number; events: any[] }> {
  return fetchWithAuth<{ total_events: number; events: any[] }>(
    "/api/v1/developer/usage",
    token
  );
}

// -----------------------------------------------------------------------------
// Contact Inquiries API
// -----------------------------------------------------------------------------
export async function submitContactInquiry(
  payload: ContactInquiryInput
): Promise<EmailDeliveryResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/contact`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let errorMsg = `Contact submission failed (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson.error?.message) {
        errorMsg = errJson.error.message;
      }
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }

  return response.json();
}



