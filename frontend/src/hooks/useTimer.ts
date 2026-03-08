import { create } from "zustand";
import type {
  FlowMode,
  TimerPhase,
  TimerStatus,
  WorkerMessage,
} from "../types";
import { MODE_DEFAULTS } from "../types";
import { sessions } from "../api/client";
import { playStartSound, playCompleteSound, playBreakOverSound } from "./useSound";

interface TimerState {
  // Timer core
  mode: FlowMode;
  phase: TimerPhase;
  status: TimerStatus;
  remainingMs: number;
  elapsedMs: number;
  totalDurationMs: number;

  // Pomodoro cycle counter (resets each session group)
  pomodoroCount: number;

  // Active session ID from backend
  activeSessionId: number | null;

  // Energy
  energyBefore: number | null;

  // Worker ref (not serialized)
  _worker: Worker | null;

  // Actions
  setMode: (mode: FlowMode) => void;
  start: (energyBefore?: number) => Promise<void>;
  pause: () => void;
  resume: () => void;
  stop: () => Promise<void>;
  complete: (energyAfter?: number, notes?: string) => Promise<void>;

  // Internal
  _onWorkerMessage: (msg: WorkerMessage) => void;
  _initWorker: () => void;
  _startBreak: () => void;
}

function getDurationMs(mode: FlowMode): number {
  return MODE_DEFAULTS[mode].work * 60 * 1000;
}

function getLongBreakInterval(mode: FlowMode): number {
  if (mode === "kids") return 3;
  return 4;
}

function getBreakMs(mode: FlowMode, pomodoroCount: number): number {
  const defaults = MODE_DEFAULTS[mode];
  const interval = getLongBreakInterval(mode);
  if (
    (mode === "pomodoro" || mode === "kids") &&
    pomodoroCount > 0 &&
    pomodoroCount % interval === 0
  ) {
    return defaults.longBreak * 60 * 1000;
  }
  return defaults.shortBreak * 60 * 1000;
}

export const useTimerStore = create<TimerState>((set, get) => ({
  mode: "pomodoro",
  phase: "idle",
  status: "idle",
  remainingMs: MODE_DEFAULTS.pomodoro.work * 60 * 1000,
  elapsedMs: 0,
  totalDurationMs: MODE_DEFAULTS.pomodoro.work * 60 * 1000,
  pomodoroCount: 0,
  activeSessionId: null,
  energyBefore: null,
  _worker: null,

  setMode: (mode) => {
    const state = get();
    if (state.status !== "idle") return; // Can't change mode while running
    const durationMs = getDurationMs(mode);
    set({
      mode,
      remainingMs: durationMs,
      totalDurationMs: durationMs,
      pomodoroCount: 0,
    });
  },

  _initWorker: () => {
    const state = get();
    if (state._worker) return;

    const worker = new Worker(
      new URL("../workers/timer.worker.ts", import.meta.url),
      { type: "module" }
    );
    worker.onmessage = (e: MessageEvent<WorkerMessage>) => {
      get()._onWorkerMessage(e.data);
    };
    set({ _worker: worker });
  },

  _onWorkerMessage: (msg) => {
    switch (msg.type) {
      case "tick":
        set({ remainingMs: msg.remainingMs, elapsedMs: msg.elapsedMs });
        break;
      case "complete": {
        const state = get();
        if (state.phase === "focus") {
          playCompleteSound();
          // Focus period done — auto-complete session + start break
          state.complete().then(() => state._startBreak());
        } else {
          playBreakOverSound();
          // Break done — return to idle
          set({
            phase: "idle",
            status: "idle",
            remainingMs: getDurationMs(state.mode),
            elapsedMs: 0,
            totalDurationMs: getDurationMs(state.mode),
          });
          // Notification
          if (Notification.permission === "granted") {
            new Notification("Break over!", {
              body: "Ready for another focus session?",
              icon: "/favicon.ico",
            });
          }
        }
        break;
      }
      case "stopped":
        set({ status: "idle", phase: "idle" });
        break;
    }
  },

  _startBreak: () => {
    const state = get();
    const { mode, pomodoroCount, _worker } = state;

    if (mode === "free_flow") {
      // Free flow: break = 20% of elapsed work time
      const breakMs = Math.round(state.elapsedMs * 0.2);
      if (breakMs < 60000) {
        // Less than 1 min — skip break
        set({
          phase: "idle",
          status: "idle",
          remainingMs: 0,
          elapsedMs: 0,
          totalDurationMs: 0,
        });
        return;
      }
      set({
        phase: "short_break",
        status: "running",
        remainingMs: breakMs,
        elapsedMs: 0,
        totalDurationMs: breakMs,
      });
      _worker?.postMessage({ type: "start", durationMs: breakMs });
      return;
    }

    const interval = getLongBreakInterval(mode);
    const isLongBreak =
      (mode === "pomodoro" || mode === "kids") &&
      pomodoroCount > 0 &&
      pomodoroCount % interval === 0;
    const breakMs = getBreakMs(mode, pomodoroCount);
    const breakPhase = isLongBreak ? "long_break" : "short_break";

    set({
      phase: breakPhase,
      status: "running",
      remainingMs: breakMs,
      elapsedMs: 0,
      totalDurationMs: breakMs,
    });
    _worker?.postMessage({ type: "start", durationMs: breakMs });

    // Notification
    if (Notification.permission === "granted") {
      new Notification("Focus complete!", {
        body: `Take a ${Math.round(breakMs / 60000)} min break.`,
        icon: "/favicon.ico",
      });
    }
  },

  start: async (energyBefore) => {
    const state = get();
    state._initWorker();

    const { mode } = get();
    const durationMs = getDurationMs(mode);

    // Create session on backend
    let sessionId: number | null = null;
    try {
      const session = await sessions.create({
        mode,
        planned_duration: Math.round(durationMs / 60000),
        energy_before: energyBefore ?? undefined,
      });
      sessionId = session.id;
    } catch {
      // Offline mode — continue without backend session
    }

    playStartSound();

    set({
      phase: "focus",
      status: "running",
      remainingMs: durationMs,
      elapsedMs: 0,
      totalDurationMs: durationMs,
      activeSessionId: sessionId,
      energyBefore: energyBefore ?? null,
    });

    get()._worker?.postMessage({ type: "start", durationMs });
  },

  pause: () => {
    get()._worker?.postMessage({ type: "pause" });
    set({ status: "paused" });
  },

  resume: () => {
    get()._worker?.postMessage({ type: "resume" });
    set({ status: "running" });
  },

  stop: async () => {
    const state = get();
    state._worker?.postMessage({ type: "stop" });

    // Cancel session on backend
    if (state.activeSessionId) {
      try {
        await sessions.cancel(state.activeSessionId);
      } catch {
        // Ignore — session might not exist
      }
    }

    set({
      phase: "idle",
      status: "idle",
      remainingMs: getDurationMs(state.mode),
      elapsedMs: 0,
      totalDurationMs: getDurationMs(state.mode),
      activeSessionId: null,
      energyBefore: null,
    });
  },

  complete: async (energyAfter, notes) => {
    const state = get();
    state._worker?.postMessage({ type: "stop" });

    // Complete session on backend
    if (state.activeSessionId) {
      try {
        await sessions.complete(state.activeSessionId, {
          energy_after: energyAfter,
          notes,
        });
      } catch {
        // Ignore
      }
    }

    set((prev) => ({
      activeSessionId: null,
      energyBefore: null,
      pomodoroCount: prev.pomodoroCount + 1,
    }));
  },
}));
