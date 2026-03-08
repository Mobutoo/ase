import { create } from "zustand";
import { leaderboard as leaderboardApi, analytics } from "../api/phase4";
import type { LeaderboardEntry, LeaderboardPeriod, Achievement, Reward } from "../types/phase4";

interface LeaderboardState {
  entries: LeaderboardEntry[];
  achievements: Achievement[];
  rewards: Reward[];
  period: LeaderboardPeriod;
  isLoading: boolean;
  error: string | null;

  fetchLeaderboard: (period?: LeaderboardPeriod) => Promise<void>;
  fetchAchievements: () => Promise<void>;
  fetchRewards: () => Promise<void>;
  setPeriod: (period: LeaderboardPeriod) => void;
}

export const useLeaderboardStore = create<LeaderboardState>((set, get) => ({
  entries: [],
  achievements: [],
  rewards: [],
  period: "week",
  isLoading: false,
  error: null,

  fetchLeaderboard: async (period) => {
    const activePeriod = period ?? get().period;
    set({ isLoading: true, error: null });
    try {
      const data = await leaderboardApi.list(activePeriod);
      set({ entries: Array.isArray(data) ? data : [], isLoading: false });
    } catch (e) {
      set({
        error: e instanceof Error ? e.message : "Failed to load leaderboard",
        isLoading: false,
      });
    }
  },

  fetchAchievements: async () => {
    set({ isLoading: true, error: null });
    try {
      const data = await analytics.achievements();
      set({ achievements: Array.isArray(data) ? data : [], isLoading: false });
    } catch (e) {
      set({
        error: e instanceof Error ? e.message : "Failed to load achievements",
        isLoading: false,
      });
    }
  },

  fetchRewards: async () => {
    set({ isLoading: true, error: null });
    try {
      const data = await leaderboardApi.rewards();
      set({ rewards: Array.isArray(data) ? data : [], isLoading: false });
    } catch (e) {
      set({
        error: e instanceof Error ? e.message : "Failed to load rewards",
        isLoading: false,
      });
    }
  },

  setPeriod: (period) => set({ period }),
}));
