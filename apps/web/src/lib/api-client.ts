import type { HealthResponse } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export async function checkBackendHealth(): Promise<HealthResponse> {
  const url = `${API_BASE_URL}/api/v1/health`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Health check failed with status: ${response.status}`);
  }
  return response.json();
}
