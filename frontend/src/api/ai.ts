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

import { request } from "./request";


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
