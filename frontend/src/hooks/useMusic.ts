import { create } from "zustand";
import type { Playlist, PlaylistMode } from "../types/phase2";
import { playlists } from "../api/phase2";

// Default playlists keyed by mode (YouTube playlist URLs)
const DEFAULT_PLAYLISTS: Record<PlaylistMode, Omit<Playlist, "id" | "isCustom">> = {
  deep_work: {
    name: "Deep Work — Lo-Fi Chill",
    youtubeUrl: "https://www.youtube.com/watch?v=jfKfPfyJRdk",
    mode: "deep_work",
    isDefault: true,
  },
  pomodoro: {
    name: "Pomodoro — Ambient Focus",
    youtubeUrl: "https://www.youtube.com/watch?v=5qap5aO4i9A",
    mode: "pomodoro",
    isDefault: true,
  },
  kids: {
    name: "Kids — Calm Study",
    youtubeUrl: "https://www.youtube.com/watch?v=rkZl2gsLUp4",
    mode: "kids",
    isDefault: true,
  },
  sprint: {
    name: "Sprint — Upbeat Energy",
    youtubeUrl: "https://www.youtube.com/watch?v=5yx6BWlEVcY",
    mode: "sprint",
    isDefault: true,
  },
  free_flow: {
    name: "Free Flow — Jazz Beats",
    youtubeUrl: "https://www.youtube.com/watch?v=Dx5qFachd3A",
    mode: "free_flow",
    isDefault: true,
  },
  custom: {
    name: "Custom",
    youtubeUrl: "",
    mode: "custom",
    isDefault: false,
  },
};

interface MusicState {
  isPlaying: boolean;
  currentTrack: Playlist | null;
  volume: number;          // 0–100
  availablePlaylists: Playlist[];
  isLoading: boolean;
  error: string | null;

  // YouTube player ref (not serialized — managed externally)
  _playerReady: boolean;

  // Actions
  fetchPlaylists: () => Promise<void>;
  play: () => void;
  pause: () => void;
  setVolume: (volume: number) => void;
  setPlaylist: (playlist: Playlist) => void;
  setPlaylistByMode: (mode: PlaylistMode) => void;
  setPlayerReady: (ready: boolean) => void;
  clearError: () => void;
}

export const useMusicStore = create<MusicState>((set, get) => ({
  isPlaying: false,
  currentTrack: null,
  volume: 60,
  availablePlaylists: [],
  isLoading: false,
  error: null,
  _playerReady: false,

  fetchPlaylists: async () => {
    set({ isLoading: true, error: null });
    try {
      const res = await playlists.list();
      set({ availablePlaylists: res.results ?? [], isLoading: false });
    } catch {
      // Fallback to built-in defaults — API may not exist yet
      const builtIn: Playlist[] = Object.entries(DEFAULT_PLAYLISTS).map(
        ([, v], i) => ({ ...v, id: `default-${i}`, isCustom: false })
      );
      set({ availablePlaylists: builtIn, isLoading: false });
    }
  },

  play: () => set({ isPlaying: true }),

  pause: () => set({ isPlaying: false }),

  setVolume: (volume) => set({ volume: Math.min(100, Math.max(0, volume)) }),

  setPlaylist: (playlist) =>
    set({ currentTrack: playlist, isPlaying: false }),

  setPlaylistByMode: (mode) => {
    const { availablePlaylists } = get();
    const found =
      availablePlaylists.find((p) => p.mode === mode && p.isDefault) ?? null;
    if (found) {
      set({ currentTrack: found, isPlaying: false });
    } else {
      // Build a transient playlist from defaults
      const def = DEFAULT_PLAYLISTS[mode];
      const transient: Playlist = { ...def, id: `default-${mode}`, isCustom: false };
      set({ currentTrack: transient, isPlaying: false });
    }
  },

  setPlayerReady: (ready) => set({ _playerReady: ready }),

  clearError: () => set({ error: null }),
}));
