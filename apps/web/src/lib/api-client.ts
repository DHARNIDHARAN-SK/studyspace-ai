import type {
  HealthResponse,
  Project,
  ProjectCreateInput,
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
