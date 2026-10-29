/**
 * API client for Ase backend.
 * Uses Django session auth (cookies). CSRF token from cookie.
 */

import { request } from "./request";


// --- Sessions ---
export const sessions = {
  list: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return request<{ results: import("../types").Session[] }>(
      `/api/v1/sessions/${qs}`
    );
  },
  create: (data: Partial<import("../types").Session>) =>
    request<import("../types").Session>("/api/v1/sessions/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  complete: (id: number, data: { energyAfter?: number; notes?: string }) =>
    request<import("../types").Session>(`/api/v1/sessions/${id}/complete/`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  cancel: (id: number) =>
    request<import("../types").Session>(`/api/v1/sessions/${id}/cancel/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
};

// --- Local Tasks ---
export const tasks = {
  list: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return request<{ results: import("../types").LocalTask[] }>(
      `/api/v1/tasks/${qs}`
    );
  },
  create: (data: Partial<import("../types").LocalTask>) =>
    request<import("../types").LocalTask>("/api/v1/tasks/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (id: number, data: Partial<import("../types").LocalTask>) =>
    request<import("../types").LocalTask>(`/api/v1/tasks/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  delete: (id: number) =>
    request<void>(`/api/v1/tasks/${id}/`, { method: "DELETE" }),
};

// --- Energy ---
export const energy = {
  list: () =>
    request<{ results: import("../types").EnergyReading[] }>(
      "/api/v1/energy/"
    ),
  create: (data: { level: number; context: string; session?: number }) =>
    request<import("../types").EnergyReading>("/api/v1/energy/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

// --- Settings ---
export const settings = {
  get: () =>
    request<import("../types").UserSettings>("/api/v1/settings/"),
  update: (data: Partial<import("../types").UserSettings>) =>
    request<import("../types").UserSettings>("/api/v1/settings/", {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
};
