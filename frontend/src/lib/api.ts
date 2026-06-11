/** API client for AgentForge backend. */

import axios from "axios";
import type {
  TokenResponse,
  User,
  ValidationResult,
  Workflow,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: { "Content-Type": "application/json" },
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Handle 401 responses
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// ─── Auth ──────────────────────────────────────────────────────

export const authApi = {
  register: (email: string, password: string, full_name: string) =>
    api.post<User>("/auth/register", { email, password, full_name }),

  login: (email: string, password: string) =>
    api.post<TokenResponse>("/auth/login", { email, password }),

  me: () => api.get<User>("/auth/me"),
};

// ─── Workflows ─────────────────────────────────────────────────

export const workflowApi = {
  list: (workspace_id?: string) =>
    api.get<Workflow[]>("/workflows", { params: workspace_id ? { workspace_id } : {} }),

  get: (id: string) => api.get<Workflow>(`/workflows/${id}`),

  create: (data: { workspace_id: string; name: string; description?: string; dag_json?: object }) =>
    api.post<Workflow>("/workflows", data),

  update: (id: string, data: { name?: string; description?: string; dag_json?: object }) =>
    api.put<Workflow>(`/workflows/${id}`, data),

  delete: (id: string) => api.delete(`/workflows/${id}`),

  validate: (id: string) => api.post<ValidationResult>(`/workflows/${id}/validate`),

  export: (id: string, format: "json" | "yaml" = "json") =>
    api.get(`/workflows/${id}/export`, { params: { format } }),

  import: (data: { workspace_id: string; name?: string; dag: object }) =>
    api.post<Workflow>("/workflows/import", data),
};

// ─── Executions ────────────────────────────────────────────────

export const executionApi = {
  trigger: (workflow_id: string, input_data: object = {}) =>
    api.post(`/executions/workflows/${workflow_id}/execute`, { input_data }),

  list: (workflow_id: string) =>
    api.get(`/executions/workflows/${workflow_id}/executions`),

  get: (run_id: string) => api.get(`/executions/${run_id}`),

  trace: (run_id: string) => api.get(`/executions/${run_id}/trace`),

  cancel: (run_id: string) => api.post(`/executions/${run_id}/cancel`),
};

// ─── Workspaces ────────────────────────────────────────────────

export const workspaceApi = {
  list: () => api.get("/workspaces"),

  create: (name: string) => api.post("/workspaces", { name }),

  get: (id: string) => api.get(`/workspaces/${id}`),
};

export default api;
