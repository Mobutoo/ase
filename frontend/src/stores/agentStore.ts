import { create } from "zustand";
import type { AgentAction, MemberPreference, NotificationPreference } from "../types/agent";

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

import { request as apiRequest } from "../api/request";


/** Build the base URL for agent endpoints nested under a circle. */
function agentBase(circleId: string): string {
  return `/api/circles/${circleId}/agents`;
}

// ---------------------------------------------------------------------------
// State shape
// ---------------------------------------------------------------------------

interface AgentState {
  actions: AgentAction[];
  preferences: MemberPreference[];
  notificationPreference: NotificationPreference | null;
  loading: boolean;
  error: string | null;

  // Actions
  fetchActions: (circleId: string, status?: string) => Promise<void>;
  approveAction: (circleId: string, actionId: string) => Promise<void>;
  rejectAction: (circleId: string, actionId: string, reason?: string) => Promise<void>;
  fetchPreferences: (circleId: string) => Promise<void>;
  updatePreference: (circleId: string, payload: Partial<MemberPreference>) => Promise<void>;
  fetchNotificationPreference: (circleId: string) => Promise<void>;
  updateNotificationPreference: (circleId: string, payload: Partial<NotificationPreference>) => Promise<void>;
  clearError: () => void;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useAgentStore = create<AgentState>((set) => ({
  actions: [],
  preferences: [],
  notificationPreference: null,
  loading: false,
  error: null,

  fetchActions: async (circleId, status) => {
    set({ loading: true, error: null });
    try {
      const qs = status ? `?status=${status}` : "";
      const res = await apiRequest<{ results: AgentAction[] }>(
        `${agentBase(circleId)}/actions/${qs}`
      );
      set({ actions: res.results ?? [], loading: false });
    } catch (err) {
      set({
        loading: false,
        error: err instanceof Error ? err.message : "Failed to fetch agent actions",
      });
    }
  },

  approveAction: async (circleId, actionId) => {
    try {
      const updated = await apiRequest<AgentAction>(
        `${agentBase(circleId)}/actions/${actionId}/approve/`,
        { method: "POST", body: JSON.stringify({}) }
      );
      set((prev) => ({
        actions: prev.actions.map((a) => (a.id === actionId ? { ...a, ...updated } : a)),
      }));
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Failed to approve action" });
    }
  },

  rejectAction: async (circleId, actionId, reason) => {
    try {
      const updated = await apiRequest<AgentAction>(
        `${agentBase(circleId)}/actions/${actionId}/reject/`,
        { method: "POST", body: JSON.stringify({ reason }) }
      );
      set((prev) => ({
        actions: prev.actions.map((a) => (a.id === actionId ? { ...a, ...updated } : a)),
      }));
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Failed to reject action" });
    }
  },

  fetchPreferences: async (circleId) => {
    set({ loading: true, error: null });
    try {
      const res = await apiRequest<{ results: MemberPreference[] }>(
        `${agentBase(circleId)}/preferences/`
      );
      set({ preferences: res.results ?? [], loading: false });
    } catch (err) {
      set({
        loading: false,
        error: err instanceof Error ? err.message : "Failed to fetch preferences",
      });
    }
  },

  updatePreference: async (circleId, payload) => {
    set({ loading: true, error: null });
    try {
      const updated = await apiRequest<MemberPreference>(
        `${agentBase(circleId)}/preferences/`,
        { method: "PATCH", body: JSON.stringify(payload) }
      );
      set({ preferences: [updated], loading: false });
    } catch (err) {
      set({
        loading: false,
        error: err instanceof Error ? err.message : "Failed to update preference",
      });
    }
  },

  // Notification preference is a singleton per member — no id in URL
  fetchNotificationPreference: async (circleId) => {
    set({ loading: true, error: null });
    try {
      const pref = await apiRequest<NotificationPreference>(
        `${agentBase(circleId)}/notifications/`
      );
      set({ notificationPreference: pref, loading: false });
    } catch (err) {
      set({
        loading: false,
        error: err instanceof Error ? err.message : "Failed to fetch notification preference",
      });
    }
  },

  updateNotificationPreference: async (circleId, payload) => {
    try {
      const updated = await apiRequest<NotificationPreference>(
        `${agentBase(circleId)}/notifications/`,
        { method: "PATCH", body: JSON.stringify(payload) }
      );
      set({ notificationPreference: updated });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Failed to update notification preference" });
    }
  },

  clearError: () => set({ error: null }),
}));
