/**
 * Phase 5 API client — AI Copilot (suggestions, daily plan, reflection).
 * Follows the same request pattern as phase2.ts and phase4.ts.
 */

import type {
  AISuggestion,
  PlanRequestPayload,
  AISuggestionListParams,
  WebhookAckResponse,
} from "../types/phase5";

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
    if (res.status === 409) {
      throw new Error("Suggestion has already been actioned");
    }
    if (res.status >= 500) {
      throw new Error("Server error — please try again later");
    }
    throw new Error(`Request failed (${res.status})`);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

function buildQs(params?: Record<string, string>): string {
  return params ? "?" + new URLSearchParams(params).toString() : "";
}

// --- AI Suggestions ---
export const aiSuggestions = {
  /**
   * List suggestions for the authenticated user.
   * Supports optional ?type= and ?pending=true filters.
   */
  list: (params?: AISuggestionListParams) => {
    const p = params
      ? (Object.fromEntries(
          Object.entries(params)
            .filter(([, v]) => v != null && v !== undefined)
            .map(([k, v]) => [k, String(v)])
        ) as Record<string, string>)
      : undefined;
    return request<AISuggestion[]>(`/api/v1/ai/suggestions/${buildQs(p)}`);
  },

  /** Accept a specific suggestion. */
  accept: (id: number) =>
    request<AISuggestion>(`/api/v1/ai/suggestions/${id}/accept/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),

  /** Dismiss a specific suggestion. */
  dismiss: (id: number) =>
    request<AISuggestion>(`/api/v1/ai/suggestions/${id}/dismiss/`, {
      method: "POST",
      body: JSON.stringify({}),
    }),

  /**
   * Trigger an AI daily plan request via n8n.
   * May return 201 (sync: suggestion created) or 202 (async: queued).
   */
  requestPlan: (payload?: PlanRequestPayload) =>
    request<AISuggestion | WebhookAckResponse>("/api/v1/ai/suggestions/request_plan/", {
      method: "POST",
      body: JSON.stringify(payload ?? {}),
    }),

  /**
   * Trigger an end-of-day reflection prompt via n8n.
   * May return 201 (sync) or 202 (async: queued).
   */
  requestReflection: () =>
    request<AISuggestion | WebhookAckResponse>("/api/v1/ai/suggestions/request_reflection/", {
      method: "POST",
      body: JSON.stringify({}),
    }),
};
