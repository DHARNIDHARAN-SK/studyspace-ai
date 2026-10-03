import type {
  Conversation,
  HealthResponse,
  Message,
  Project,
  ProjectCreateInput,
  ProjectDocument,
  ProjectUpdateInput,
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
  };
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


