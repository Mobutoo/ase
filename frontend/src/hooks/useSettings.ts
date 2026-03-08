import { create } from "zustand";
import type { UserSettings } from "../types";
import { settings as settingsApi } from "../api/client";

interface SettingsState {
  settings: UserSettings | null;
  isLoading: boolean;
  isSaving: boolean;
  error: string | null;
  savedAt: Date | null;

  // Actions
  fetchSettings: () => Promise<void>;
  updateSettings: (partial: Partial<UserSettings>) => Promise<void>;
  clearError: () => void;
}

export const useSettingsStore = create<SettingsState>((set, get) => ({
  settings: null,
  isLoading: false,
  isSaving: false,
  error: null,
  savedAt: null,

  fetchSettings: async () => {
    if (get().isLoading) return;
    set({ isLoading: true, error: null });
    try {
      const data = await settingsApi.get();
      set({ settings: data, isLoading: false });
    } catch (err) {
      set({
        isLoading: false,
        error: err instanceof Error ? err.message : "Failed to load settings",
      });
    }
  },

  updateSettings: async (partial) => {
    set({ isSaving: true, error: null });
    try {
      const updated = await settingsApi.update(partial);
      set({ settings: updated, isSaving: false, savedAt: new Date() });
    } catch (err) {
      set({
        isSaving: false,
        error: err instanceof Error ? err.message : "Failed to save settings",
      });
    }
  },

  clearError: () => set({ error: null }),
}));
