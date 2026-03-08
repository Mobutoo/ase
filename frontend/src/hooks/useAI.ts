import { create } from "zustand";
import type { AISuggestion, AISuggestionType, PlanRequestPayload, WebhookAckResponse } from "../types/phase5";
import { aiSuggestions } from "../api/ai";

/** Distinguishes a fully-created suggestion from a webhook acknowledgement. */
function isSuggestion(value: AISuggestion | WebhookAckResponse): value is AISuggestion {
  return typeof (value as AISuggestion).id === "number";
}

interface AIState {
  suggestions: AISuggestion[];
  isLoading: boolean;
  /** Set while an accept/dismiss action is in flight, keyed by suggestion id. */
  actioningIds: Set<number>;
  /** True while requestDailyPlan is in flight. */
  isRequestingPlan: boolean;
  /** True while requestReflection is in flight. */
  isRequestingReflection: boolean;
  error: string | null;

  // --- Actions ---
  fetchSuggestions: (params?: { type?: AISuggestionType; pending?: boolean }) => Promise<void>;
  acceptSuggestion: (id: number) => Promise<void>;
  dismissSuggestion: (id: number) => Promise<void>;
  requestDailyPlan: (payload?: PlanRequestPayload) => Promise<void>;
  requestReflection: () => Promise<void>;
  clearError: () => void;
}

export const useAIStore = create<AIState>((set) => ({
  suggestions: [],
  isLoading: false,
  actioningIds: new Set(),
  isRequestingPlan: false,
  isRequestingReflection: false,
  error: null,

  fetchSuggestions: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const apiParams = params
        ? {
            ...(params.type ? { type: params.type } : {}),
            ...(params.pending !== undefined ? { pending: params.pending ? "true" as const : "false" as const } : {}),
          }
        : undefined;
      const raw = await aiSuggestions.list(apiParams);
      // Handle both paginated { results: [...] } and raw array responses
      const list = Array.isArray(raw) ? raw : (raw as unknown as { results?: AISuggestion[] })?.results ?? [];
      set({ suggestions: list, isLoading: false });
    } catch (err) {
      set({
        isLoading: false,
        error: err instanceof Error ? err.message : "Failed to fetch AI suggestions",
      });
    }
  },

  acceptSuggestion: async (id) => {
    set((prev) => ({ actioningIds: new Set([...prev.actioningIds, id]) }));
    try {
      const updated = await aiSuggestions.accept(id);
      set((prev) => ({
        suggestions: prev.suggestions.map((s) => (s.id === id ? updated : s)),
        actioningIds: new Set([...prev.actioningIds].filter((x) => x !== id)),
      }));
    } catch (err) {
      set((prev) => ({
        actioningIds: new Set([...prev.actioningIds].filter((x) => x !== id)),
        error: err instanceof Error ? err.message : "Failed to accept suggestion",
      }));
    }
  },

  dismissSuggestion: async (id) => {
    set((prev) => ({ actioningIds: new Set([...prev.actioningIds, id]) }));
    try {
      const updated = await aiSuggestions.dismiss(id);
      set((prev) => ({
        suggestions: prev.suggestions.map((s) => (s.id === id ? updated : s)),
        actioningIds: new Set([...prev.actioningIds].filter((x) => x !== id)),
      }));
    } catch (err) {
      set((prev) => ({
        actioningIds: new Set([...prev.actioningIds].filter((x) => x !== id)),
        error: err instanceof Error ? err.message : "Failed to dismiss suggestion",
      }));
    }
  },

  requestDailyPlan: async (payload) => {
    set({ isRequestingPlan: true, error: null });
    try {
      const result = await aiSuggestions.requestPlan(payload);
      if (isSuggestion(result)) {
        // n8n responded synchronously — prepend the new suggestion
        set((prev) => ({
          suggestions: [result, ...prev.suggestions],
          isRequestingPlan: false,
        }));
      } else {
        // Async path — will arrive via webhook callback; just stop loading
        set({ isRequestingPlan: false });
      }
    } catch (err) {
      set({
        isRequestingPlan: false,
        error: err instanceof Error ? err.message : "Failed to request daily plan",
      });
    }
  },

  requestReflection: async () => {
    set({ isRequestingReflection: true, error: null });
    try {
      const result = await aiSuggestions.requestReflection();
      if (isSuggestion(result)) {
        set((prev) => ({
          suggestions: [result, ...prev.suggestions],
          isRequestingReflection: false,
        }));
      } else {
        set({ isRequestingReflection: false });
      }
    } catch (err) {
      set({
        isRequestingReflection: false,
        error: err instanceof Error ? err.message : "Failed to request reflection prompt",
      });
    }
  },

  clearError: () => set({ error: null }),
}));
