import { create } from "zustand";
import { analytics } from "../api/phase4";
import type { DailyStats, DensityEntry, StreakInfo } from "../types/phase4";

interface AnalyticsState {
  daily: DailyStats[];
  density: DensityEntry[];
  streak: StreakInfo | null;
  isLoading: boolean;
  error: string | null;

  fetchDaily: (from: string, to?: string) => Promise<void>;
  fetchDensity: (weeks?: number) => Promise<void>;
  fetchStreak: () => Promise<void>;
  fetchAll: (from?: string) => Promise<void>;
}

export const useAnalyticsStore = create<AnalyticsState>((set) => ({
  daily: [],
  density: [],
  streak: null,
  isLoading: false,
  error: null,

  fetchDaily: async (from, to) => {
    set({ isLoading: true, error: null });
    try {
      const params: { from?: string; to?: string } = {};
      if (from) params.from = from;
      if (to) params.to = to;
      const data = await analytics.daily(params);
      set({ daily: Array.isArray(data) ? data : [], isLoading: false });
    } catch (e) {
      set({
        error: e instanceof Error ? e.message : "Failed to load daily stats",
        isLoading: false,
      });
    }
  },

  fetchDensity: async (weeks = 52) => {
    set({ isLoading: true, error: null });
    try {
      const data = await analytics.density({ weeks: String(weeks) });
      set({ density: Array.isArray(data) ? data : [], isLoading: false });
    } catch (e) {
      set({
        error: e instanceof Error ? e.message : "Failed to load density data",
        isLoading: false,
      });
    }
  },

  fetchStreak: async () => {
    set({ isLoading: true, error: null });
    try {
      const data = await analytics.streak();
      set({ streak: data ?? null, isLoading: false });
    } catch (e) {
      set({
        error: e instanceof Error ? e.message : "Failed to load streak",
        isLoading: false,
      });
    }
  },

  fetchAll: async (from) => {
    set({ isLoading: true, error: null });
    try {
      const params: { from?: string } = {};
      if (from) params.from = from;
      const [dailyData, densityData, streakData] = await Promise.all([
        analytics.daily(params),
        analytics.density({ weeks: "52" }),
        analytics.streak(),
      ]);
      set({
        daily: Array.isArray(dailyData) ? dailyData : [],
        density: Array.isArray(densityData) ? densityData : [],
        streak: streakData ?? null,
        isLoading: false,
        error: null,
      });
    } catch (e) {
      set({
        error: e instanceof Error ? e.message : "Failed to load analytics",
        isLoading: false,
      });
    }
  },
}));
