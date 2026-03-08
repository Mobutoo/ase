/**
 * API client for Ase backend.
 * Uses Django session auth (cookies). CSRF token from cookie.
 */

function getCsrfToken(): string {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : "";
}

async function request<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-CSRFToken": getCsrfToken(),
    ...(options.headers as Record<string, string> ?? {}),
  };

  const res = await fetch(url, { ...options, headers, credentials: "same-origin" });

  if (!res.ok) {
    const body = await res.text();
    // Log details for debugging but show user-friendly messages
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
  return res.json();
}

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
  complete: (id: number, data: { energy_after?: number; notes?: string }) =>
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
