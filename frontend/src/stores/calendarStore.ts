import { create } from "zustand";
import type { CalendarEvent, Calendar, CalendarView } from "../types/calendar";

// ---------------------------------------------------------------------------
// API helpers — thin wrappers over fetch; mirrors client.ts pattern
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
    console.error(`Calendar API ${res.status}:`, body);
    if (res.status === 401 || res.status === 403) throw new Error("Please log in to continue");
    if (res.status === 404) throw new Error("Resource not found");
    if (res.status >= 500) throw new Error("Server error — please try again later");
    throw new Error(`Request failed (${res.status})`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ---------------------------------------------------------------------------
// State shape
// ---------------------------------------------------------------------------

interface CalendarState {
  events: CalendarEvent[];
  calendars: Calendar[];
  currentView: CalendarView;
  selectedDate: string; // ISO date string YYYY-MM-DD
  loading: boolean;
  error: string | null;

  // Actions
  fetchEvents: (params?: { start?: string; end?: string; calendarId?: string }) => Promise<void>;
  fetchCalendars: () => Promise<void>;
  createEvent: (payload: Partial<CalendarEvent>) => Promise<CalendarEvent | null>;
  updateEvent: (id: string, payload: Partial<CalendarEvent>) => Promise<void>;
  deleteEvent: (id: string) => Promise<void>;
  setView: (view: CalendarView) => void;
  navigateDate: (date: string) => void;
  clearError: () => void;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useCalendarStore = create<CalendarState>((set, _get) => ({
  events: [],
  calendars: [],
  currentView: "week",
  selectedDate: new Date().toISOString().slice(0, 10),
  loading: false,
  error: null,

  fetchEvents: async (params) => {
    set({ loading: true, error: null });
    try {
      const qs = params ? "?" + new URLSearchParams(params as Record<string, string>).toString() : "";
      const res = await apiRequest<{ results: CalendarEvent[] }>(`/api/calendar/events/${qs}`);
      set({ events: res.results ?? [], loading: false });
    } catch (err) {
      set({
        loading: false,
        error: err instanceof Error ? err.message : "Failed to fetch events",
      });
    }
  },

  fetchCalendars: async () => {
    set({ loading: true, error: null });
    try {
      const res = await apiRequest<{ results: Calendar[] }>("/api/calendar/calendars/");
      set({ calendars: res.results ?? [], loading: false });
    } catch (err) {
      set({
        loading: false,
        error: err instanceof Error ? err.message : "Failed to fetch calendars",
      });
    }
  },

  createEvent: async (payload) => {
    set({ loading: true, error: null });
    try {
      const created = await apiRequest<CalendarEvent>("/api/calendar/events/", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      set((prev) => ({ events: [created, ...prev.events], loading: false }));
      return created;
    } catch (err) {
      set({
        loading: false,
        error: err instanceof Error ? err.message : "Failed to create event",
      });
      return null;
    }
  },

  updateEvent: async (id, payload) => {
    try {
      const updated = await apiRequest<CalendarEvent>(`/api/calendar/events/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      set((prev) => ({
        events: prev.events.map((e) => (e.id === id ? { ...e, ...updated } : e)),
      }));
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Failed to update event" });
    }
  },

  deleteEvent: async (id) => {
    try {
      await apiRequest<void>(`/api/calendar/events/${id}/`, { method: "DELETE" });
      set((prev) => ({ events: prev.events.filter((e) => e.id !== id) }));
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Failed to delete event" });
    }
  },

  setView: (view) => set({ currentView: view }),

  navigateDate: (date) => set({ selectedDate: date }),

  clearError: () => set({ error: null }),
}));
