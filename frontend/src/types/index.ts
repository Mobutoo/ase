// --- Flow Modes ---
export type FlowMode = "deep_work" | "pomodoro" | "kids" | "sprint" | "free_flow";

export type TimerPhase = "focus" | "short_break" | "long_break" | "idle";

export type TimerStatus = "idle" | "running" | "paused";

// --- Mode defaults (minutes) ---
export const MODE_DEFAULTS: Record<
  FlowMode,
  { work: number; shortBreak: number; longBreak: number }
> = {
  deep_work: { work: 90, shortBreak: 20, longBreak: 20 },
  pomodoro: { work: 25, shortBreak: 5, longBreak: 15 },
  kids: { work: 15, shortBreak: 5, longBreak: 10 },
  sprint: { work: 45, shortBreak: 10, longBreak: 10 },
  free_flow: { work: 0, shortBreak: 0, longBreak: 0 },
};

export const MODE_LABELS: Record<FlowMode, string> = {
  deep_work: "Deep Work",
  pomodoro: "Pomodoro",
  kids: "Kids",
  sprint: "Sprint",
  free_flow: "Free Flow",
};

// --- Session ---
export interface Session {
  id: number;
  username: string;
  mode: FlowMode;
  startedAt: string;
  endedAt: string | null;
  plannedDuration: number;
  actualDuration: number | null;
  taskId: string | null;
  taskTitle: string | null;
  taskSource: string;
  energyBefore: number | null;
  energyAfter: number | null;
  playlistUrl: string | null;
  notes: string;
  completed: boolean;
  tag: number | null;
}

// --- Local Task ---
export type TaskStatus = "todo" | "in_progress" | "done";
export type TaskPriority = "urgent" | "high" | "medium" | "low" | "none";

export interface LocalTask {
  id: number;
  title: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  labels: string[];
  dueDate: string | null;
  estimatedMinutes: number | null;
  displayOrder: number;
  createdAt: string;
  updatedAt: string;
}

// --- Energy ---
export type EnergyContext = "session_start" | "session_end" | "check_in";

export interface EnergyReading {
  id: number;
  timestamp: string;
  level: number;
  context: EnergyContext;
  session: number | null;
}

// --- User Settings ---
export interface UserSettings {
  username: string;
  theme: string;
  startSound: string;
  stopSound: string;
  focusTime: number;
  shortBreak: number;
  longBreak: number;
  focusColor: string;
  breakColor: string;
  image: string;
  timezone: string;
  deepWorkDuration: number;
  sprintDuration: number;
  freeFlowEnabled: boolean;
  autoModeSelection: boolean;
  modeLabelMap: Record<string, string[]>;
  energyTrackingEnabled: boolean;
  youtubeDefaultPlaylists: Record<string, string>;
  profilePublic: boolean;
}

// --- Worker messages ---
export type WorkerCommand =
  | { type: "start"; durationMs: number }
  | { type: "pause" }
  | { type: "resume" }
  | { type: "stop" }
  | { type: "tick" };

export type WorkerMessage =
  | { type: "tick"; remainingMs: number; elapsedMs: number }
  | { type: "complete" }
  | { type: "stopped" };
