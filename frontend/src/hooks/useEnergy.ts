import { create } from "zustand";
import type { EnergyHeatmapEntry, EnergyPrediction } from "../types/phase2";
import type { EnergyContext, EnergyReading } from "../types";
import { energy } from "../api/client";
import { energyApi } from "../api/phase2";

interface EnergyState {
  readings: EnergyReading[];
  heatmap: EnergyHeatmapEntry[];
  prediction: EnergyPrediction | null;
  isLoading: boolean;
  isSubmitting: boolean;
  error: string | null;
  lastSubmittedLevel: number | null;

  // Actions
  fetchReadings: () => Promise<void>;
  submitReading: (level: number, context?: EnergyContext, sessionId?: number) => Promise<void>;
  fetchHeatmap: () => Promise<void>;
  fetchPrediction: (hour?: number, dayOfWeek?: number) => Promise<void>;
  clearError: () => void;
}

export const useEnergyStore = create<EnergyState>((set) => ({
  readings: [],
  heatmap: [],
  prediction: null,
  isLoading: false,
  isSubmitting: false,
  error: null,
  lastSubmittedLevel: null,

  fetchReadings: async () => {
    set({ isLoading: true, error: null });
    try {
      const res = await energy.list();
      set({ readings: res.results, isLoading: false });
    } catch (err) {
      set({
        isLoading: false,
        error:
          err instanceof Error ? err.message : "Failed to fetch energy readings",
      });
    }
  },

  submitReading: async (level, context = "check_in", sessionId) => {
    set({ isSubmitting: true, error: null });
    try {
      const newReading = await energy.create({
        level,
        context,
        session: sessionId,
      });
      set((prev) => ({
        readings: [newReading, ...prev.readings],
        isSubmitting: false,
        lastSubmittedLevel: level,
      }));
    } catch (err) {
      set({
        isSubmitting: false,
        error:
          err instanceof Error ? err.message : "Failed to submit energy reading",
      });
    }
  },

  fetchHeatmap: async () => {
    set({ isLoading: true, error: null });
    try {
      const entries = await energyApi.heatmap();
      set({ heatmap: entries, isLoading: false });
    } catch (err) {
      set({
        isLoading: false,
        error:
          err instanceof Error ? err.message : "Failed to fetch energy heatmap",
      });
    }
  },

  fetchPrediction: async (hour, dayOfWeek) => {
    try {
      const pred = await energyApi.predict({ hour, dayOfWeek });
      set({ prediction: pred });
    } catch {
      // Prediction is best-effort — ignore errors
    }
  },

  clearError: () => set({ error: null }),
}));
