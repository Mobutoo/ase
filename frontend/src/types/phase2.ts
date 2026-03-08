import type { TaskStatus, TaskPriority } from "./index";

// --- Task Sources ---
export type TaskSource = "local" | "plane" | "github";

// --- Unified Task ---
export interface UnifiedTask {
  id: string;
  externalId: string | null;
  source: TaskSource;
  title: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  labels: string[];
  dueDate: string | null;
  estimatedMinutes: number | null;
  projectName: string | null;
  url: string | null;
  createdAt: string;
  updatedAt: string;
}

// --- Task Source Config ---
export interface TaskSourceConfig {
  source: TaskSource;
  enabled: boolean;
  label: string;
  icon: string;
}

// --- Playlists ---
export type PlaylistMode = "deep_work" | "pomodoro" | "kids" | "sprint" | "free_flow" | "custom";

export interface Playlist {
  id: string;
  name: string;
  youtubeUrl: string;
  mode: PlaylistMode;
  isDefault: boolean;
  isCustom: boolean;
}

// --- Energy Heatmap ---
export interface EnergyHeatmapEntry {
  hour: number;        // 0–23
  dayOfWeek: number;   // 0=Mon … 6=Sun
  avgLevel: number;    // 1–5, NaN if no data
  count: number;
}

export interface EnergyPrediction {
  hour: number;
  dayOfWeek: number;
  predictedLevel: number;
  confidence: number;
}

// --- API response wrappers ---
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// --- Create payloads ---
export interface CreateTaskPayload {
  title: string;
  description?: string;
  priority?: TaskPriority;
  labels?: string[];
  dueDate?: string | null;
  estimatedMinutes?: number | null;
}

export interface CreatePlaylistPayload {
  name: string;
  youtubeUrl: string;
  mode: PlaylistMode;
}
