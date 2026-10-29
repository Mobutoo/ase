import { create } from "zustand";
import type { Circle, CircleMember } from "../types/circle";

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

import { request as apiRequest } from "../api/request";


// ---------------------------------------------------------------------------
// Invite payload
// ---------------------------------------------------------------------------

export interface InviteMemberPayload {
  role: string;
  displayName: string;
}

export interface CircleInvitation {
  inviteToken: string;
  circleId: number;
  circleName: string;
  expiresInSeconds: number;
}

// ---------------------------------------------------------------------------
// State shape
// ---------------------------------------------------------------------------

interface CircleState {
  circles: Circle[];
  currentCircle: Circle | null;
  members: CircleMember[];
  loading: boolean;
  error: string | null;

  // Actions
  fetchCircles: () => Promise<void>;
  setCurrentCircle: (circle: Circle) => void;
  fetchMembers: (circleId: string) => Promise<void>;
  inviteMember: (circleId: string, payload: InviteMemberPayload) => Promise<CircleInvitation | null>;
  updateRole: (memberId: string, role: string) => Promise<void>;
  removeMember: (memberId: string) => Promise<void>;
  updateCircle: (circleId: string, payload: Partial<Circle>) => Promise<void>;
  clearError: () => void;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useCircleStore = create<CircleState>((set, get) => ({
  circles: [],
  currentCircle: null,
  members: [],
  loading: false,
  error: null,

  fetchCircles: async () => {
    set({ loading: true, error: null });
    try {
      const res = await apiRequest<{ results: Circle[] }>("/api/circles/");
      const circles = res.results ?? [];
      set({
        circles,
        loading: false,
        // Auto-select the primary circle if none selected
        currentCircle: get().currentCircle ?? circles.find((c) => c.isPrimary) ?? circles[0] ?? null,
      });
    } catch (err) {
      set({
        loading: false,
        error: err instanceof Error ? err.message : "Failed to fetch circles",
      });
    }
  },

  setCurrentCircle: (circle) => set({ currentCircle: circle }),

  fetchMembers: async (circleId) => {
    set({ loading: true, error: null });
    try {
      const res = await apiRequest<{ results: CircleMember[] }>(
        `/api/circles/${circleId}/members/`
      );
      set({ members: res.results ?? [], loading: false });
    } catch (err) {
      set({
        loading: false,
        error: err instanceof Error ? err.message : "Failed to fetch members",
      });
    }
  },

  inviteMember: async (circleId, payload) => {
    set({ loading: true, error: null });
    try {
      const invitation = await apiRequest<CircleInvitation>(
        `/api/circles/${circleId}/invite/`,
        { method: "POST", body: JSON.stringify(payload) }
      );
      set({ loading: false });
      return invitation;
    } catch (err) {
      set({
        loading: false,
        error: err instanceof Error ? err.message : "Failed to create invitation",
      });
      return null;
    }
  },

  updateRole: async (memberId, role) => {
    try {
      const circleId = get().currentCircle?.id;
      if (circleId == null) throw new Error("Select a circle first");
      const updated = await apiRequest<CircleMember>(`/api/circles/${circleId}/members/${memberId}/role/`, {
        method: "PATCH",
        body: JSON.stringify({ role }),
      });
      set((prev) => ({
        members: prev.members.map((m) => (m.id === memberId ? { ...m, ...updated } : m)),
      }));
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Failed to update role" });
    }
  },

  removeMember: async (memberId) => {
    try {
      const circleId = get().currentCircle?.id;
      if (circleId == null) throw new Error("Select a circle first");
      await apiRequest<void>(`/api/circles/${circleId}/members/${memberId}/`, { method: "DELETE" });
      set((prev) => ({ members: prev.members.filter((m) => m.id !== memberId) }));
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Failed to remove member" });
    }
  },

  updateCircle: async (circleId, payload) => {
    try {
      const updated = await apiRequest<Circle>(`/api/circles/${circleId}/`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      set((prev) => ({
        circles: prev.circles.map((c) => (c.id === circleId ? { ...c, ...updated } : c)),
        currentCircle: prev.currentCircle?.id === circleId
          ? { ...prev.currentCircle, ...updated }
          : prev.currentCircle,
      }));
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Failed to update circle" });
    }
  },

  clearError: () => set({ error: null }),
}));
