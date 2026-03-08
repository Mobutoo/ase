/**
 * Phase 2 API client — tasks, playlists, energy heatmap.
 * Reuses the same request pattern as client.ts (session auth, CSRF).
 */

import type {
  UnifiedTask,
  Playlist,
  EnergyHeatmapEntry,
  EnergyPrediction,
  PaginatedResponse,
  CreateTaskPayload,
  CreatePlaylistPayload,
} from "../types/phase2";

function getCsrfToken(): string {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : "";
}

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-CSRFToken": getCsrfToken(),
    ...((options.headers as Record<string, string>) ?? {}),
  };

  const res = await fetch(url, {
    ...options,
    headers,
    credentials: "same-origin",
  });

  if (!res.ok) {
    const body = await res.text();
    console.error(`API Error ${res.status}:`, body);
    if (res.status === 401 || res.status === 403) {
      throw new Error("Please log in to continue");
    }
    if (res.status === 404) {
      throw new Error("Resource not found");
    }
    if (res.status >= 500) {
      throw new Error("Server error — please try again later");
    }
    throw new Error(`Request failed (${res.status})`);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// --- Unified Tasks ---
export const unifiedTasks = {
  list: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return request<PaginatedResponse<UnifiedTask>>(`/api/v1/unified-tasks/${qs}`);
  },

  create: (data: CreateTaskPayload) =>
    request<UnifiedTask>("/api/v1/unified-tasks/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: string, data: Partial<CreateTaskPayload>) =>
    request<UnifiedTask>(`/api/v1/unified-tasks/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    request<void>(`/api/v1/unified-tasks/${id}/`, { method: "DELETE" }),

  startWorking: (id: string) =>
    request<UnifiedTask>(`/api/v1/unified-tasks/${id}/start_working/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
};

// --- Playlists ---
export const playlists = {
  list: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return request<PaginatedResponse<Playlist>>(`/api/v1/playlists/${qs}`);
  },

  create: (data: CreatePlaylistPayload) =>
    request<Playlist>("/api/v1/playlists/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: string, data: Partial<CreatePlaylistPayload>) =>
    request<Playlist>(`/api/v1/playlists/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    request<void>(`/api/v1/playlists/${id}/`, { method: "DELETE" }),
};

// --- Energy Analytics ---
export const energyApi = {
  heatmap: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return request<EnergyHeatmapEntry[]>(`/api/v1/energy-analytics/heatmap/${qs}`);
  },

  predict: (params?: { hour?: number; dayOfWeek?: number }) => {
    const qs = params ? "?" + new URLSearchParams(
      Object.fromEntries(
        Object.entries(params)
          .filter(([, v]) => v !== undefined)
          .map(([k, v]) => [k, String(v)])
      )
    ).toString() : "";
    return request<EnergyPrediction>(`/api/v1/energy-analytics/predict/${qs}`);
  },
};
