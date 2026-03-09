import { create } from "zustand";
import type { Circle, CircleMember } from "../types/circle";

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

function getCsrfToken(): string {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : "";
}

async function apiRequest<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-CSRFToken": getCsrfToken(),
    ...(options.headers as Record<string, string> ?? {}),
  };
  const res = await fetch(url, { ...options, headers, credentials: "same-origin" });
  if (!res.ok) {
    const body = await res.text();
    console.error(`Circle API ${res.status}:`, body);
    if (res.status === 401 || res.status === 403) throw new Error("Please log in to continue");
    if (res.status === 404) throw new Error("Resource not found");
    if (res.status >= 500) throw new Error("Server error — please try again later");
    throw new Error(`Request failed (${res.status})`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ---------------------------------------------------------------------------
// Invite payload
// ---------------------------------------------------------------------------

export interface InviteMemberPayload {
  email: string;
  role: string;
  displayName?: string;
  membershipType?: 'local' | 'federated';
  federatedServer?: string;
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
  inviteMember: (circleId: string, payload: InviteMemberPayload) => Promise<void>;
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
      const newMember = await apiRequest<CircleMember>(
        `/api/circles/${circleId}/members/invite/`,
        { method: "POST", body: JSON.stringify(payload) }
      );
      set((prev) => ({ members: [...prev.members, newMember], loading: false }));
    } catch (err) {
      set({
        loading: false,
        error: err instanceof Error ? err.message : "Failed to send invitation",
      });
    }
  },

  updateRole: async (memberId, role) => {
    try {
      const updated = await apiRequest<CircleMember>(`/api/circles/members/${memberId}/`, {
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
      await apiRequest<void>(`/api/circles/members/${memberId}/`, { method: "DELETE" });
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
