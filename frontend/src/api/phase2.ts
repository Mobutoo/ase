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

import { request } from "./request";


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
interface ApiPlaylist {
  id: number | string;
  name: string;
  url: string;
  mode: Playlist["mode"] | "";
  isDefault: boolean;
}

function readPlaylist(data: ApiPlaylist): Playlist {
  return { id: String(data.id), name: data.name, youtubeUrl: data.url,
    mode: data.mode || "custom", isDefault: data.isDefault, isCustom: true };
}

function writePlaylist(data: Partial<CreatePlaylistPayload>) {
  const { youtubeUrl, mode, ...rest } = data;
  return { ...rest, ...(youtubeUrl !== undefined ? { url: youtubeUrl } : {}),
    ...(mode !== undefined ? { mode: mode === "custom" ? "" : mode } : {}) };
}

export const playlists = {
  list: async (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    const page = await request<PaginatedResponse<ApiPlaylist>>(`/api/v1/playlists/${qs}`);
    return { ...page, results: page.results.map(readPlaylist) };
  },

  create: async (data: CreatePlaylistPayload) =>
    readPlaylist(await request<ApiPlaylist>("/api/v1/playlists/", {
      method: "POST",
      body: JSON.stringify({ ...writePlaylist(data), source: "youtube" }),
    })),

  update: async (id: string, data: Partial<CreatePlaylistPayload>) =>
    readPlaylist(await request<ApiPlaylist>(`/api/v1/playlists/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(writePlaylist(data)),
    })),

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
