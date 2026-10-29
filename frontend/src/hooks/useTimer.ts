import { create } from "zustand";
import type { FlowMode, TimerPhase, TimerStatus, WorkerMessage } from "../types";
import { MODE_DEFAULTS } from "../types";
import { sessions } from "../api/client";
import { playStartSound, playCompleteSound, playBreakOverSound } from "./useSound";

interface TimerState {
  mode: FlowMode;
  phase: TimerPhase;
  status: TimerStatus;
  remainingMs: number;
  elapsedMs: number;
  totalDurationMs: number;
  pomodoroCount: number;
  activeSessionId: number | null;
  energyBefore: number | null;
  _worker: Worker | null;
  _workerRunId: number;
  _pendingSession: Promise<number | null> | null;
  setMode: (mode: FlowMode) => void;
  start: (energyBefore?: number) => Promise<void>;
  pause: () => void;
  resume: () => void;
  stop: () => Promise<void>;
  complete: (energyAfter?: number, notes?: string) => Promise<void>;
  _onWorkerMessage: (msg: WorkerMessage & { runId?: number }) => void;
  _initWorker: () => void;
  _startBreak: () => void;
}

function getDurationMs(mode: FlowMode): number {
  return MODE_DEFAULTS[mode].work * 60 * 1000;
}

function getLongBreakInterval(mode: FlowMode): number {
  return mode === "kids" ? 3 : 4;
}

// Optional browser capabilities must never interrupt timer transitions.
function playSound(play: () => void) {
  try { play(); } catch { /* Web Audio may be unavailable or blocked. */ }
}

function notify(title: string, body: string) {
  if (typeof Notification === "undefined" || Notification.permission !== "granted") return;
  try { new Notification(title, { body, icon: "/favicon.ico" }); }
  catch { /* Some browsers require service-worker notifications. */ }
}

export const useTimerStore = create<TimerState>((set, get) => ({
  mode: "pomodoro",
  phase: "idle",
  status: "idle",
  remainingMs: getDurationMs("pomodoro"),
  elapsedMs: 0,
  totalDurationMs: getDurationMs("pomodoro"),
  pomodoroCount: 0,
  activeSessionId: null,
  energyBefore: null,
  _worker: null,
  _workerRunId: 0,
  _pendingSession: null,

  setMode: (mode) => {
    if (get().status !== "idle") return;
    const durationMs = getDurationMs(mode);
    set({ mode, remainingMs: durationMs, elapsedMs: 0, totalDurationMs: durationMs, pomodoroCount: 0 });
  },

  _initWorker: () => {
    if (get()._worker) return;
    const worker = new Worker(new URL("../workers/timer.worker.ts", import.meta.url), { type: "module" });
    worker.onmessage = (e: MessageEvent<WorkerMessage & { runId?: number }>) => {
      get()._onWorkerMessage(e.data);
    };
    set({ _worker: worker });
  },

  _onWorkerMessage: (msg) => {
    const state = get();
    if (msg.runId !== undefined && msg.runId !== state._workerRunId) return;
    if (state.status !== "running") return;
    switch (msg.type) {
      case "tick":
        set({ remainingMs: msg.remainingMs, elapsedMs: msg.elapsedMs });
        break;
      case "complete":
        if (state.phase === "focus") {
          void state.complete();
        } else if (state.phase !== "idle") {
          set({
            phase: "idle", status: "idle", remainingMs: getDurationMs(state.mode),
            elapsedMs: 0, totalDurationMs: getDurationMs(state.mode),
          });
          playSound(playBreakOverSound);
          notify("Break over!", "Ready for another focus session?");
        }
        break;
      // Stop acknowledgements can arrive after a new timer has already started.
      // State transitions are owned by stop()/complete(), never by acknowledgements.
      case "stopped":
        break;
    }
  },

  _startBreak: () => {
    const state = get();
    const { mode, pomodoroCount, _worker } = state;
    const isLongBreak = (mode === "pomodoro" || mode === "kids") &&
      pomodoroCount > 0 && pomodoroCount % getLongBreakInterval(mode) === 0;
    const defaults = MODE_DEFAULTS[mode];
    const breakMs = mode === "free_flow"
      ? Math.round(state.elapsedMs * 0.2)
      : (isLongBreak ? defaults.longBreak : defaults.shortBreak) * 60 * 1000;
    if (breakMs < 60000) {
      set({ phase: "idle", status: "idle", remainingMs: getDurationMs(mode), elapsedMs: 0, totalDurationMs: getDurationMs(mode) });
      return;
    }
    const runId = state._workerRunId + 1;
    set({
      phase: isLongBreak ? "long_break" : "short_break", status: "running",
      remainingMs: breakMs, elapsedMs: 0, totalDurationMs: breakMs, _workerRunId: runId,
    });
    _worker?.postMessage({ type: "start", durationMs: breakMs, runId });
    notify("Focus complete!", `Take a ${Math.round(breakMs / 60000)} min break.`);
  },

  start: async (energyBefore) => {
    if (get().status !== "idle") return;
    get()._initWorker();
    const { mode, _worker, _workerRunId } = get();
    const durationMs = getDurationMs(mode);
    const runId = _workerRunId + 1;
    // Start locally immediately; slow API requests must not block or duplicate a timer.
    set({
      phase: "focus", status: "running", remainingMs: durationMs, elapsedMs: 0,
      totalDurationMs: durationMs, activeSessionId: null, energyBefore: energyBefore ?? null,
      _workerRunId: runId,
    });
    const pendingSession = sessions.create({
      mode, plannedDuration: Math.round(durationMs / 60000), energyBefore: energyBefore ?? undefined,
    }).then((session) => session.id).catch(() => null);
    set({ _pendingSession: pendingSession });
    _worker?.postMessage({ type: "start", durationMs, runId });
    playSound(playStartSound);
    const sessionId = await pendingSession;
    if (get()._workerRunId === runId && get().phase === "focus") {
      set({ activeSessionId: sessionId });
    }
  },

  pause: () => {
    if (get().status !== "running") return;
    get()._worker?.postMessage({ type: "pause" });
    set({ status: "paused" });
  },

  resume: () => {
    if (get().status !== "paused") return;
    get()._worker?.postMessage({ type: "resume" });
    set({ status: "running" });
  },

  stop: async () => {
    const state = get();
    if (state.status === "idle") return;
    state._worker?.postMessage({ type: "stop" });
    set({
      phase: "idle", status: "idle", remainingMs: getDurationMs(state.mode), elapsedMs: 0,
      totalDurationMs: getDurationMs(state.mode), activeSessionId: null, energyBefore: null,
      _pendingSession: null, _workerRunId: state._workerRunId + 1,
    });
    const sessionId = state.activeSessionId ?? await state._pendingSession;
    if (sessionId !== null) {
      try { await sessions.cancel(sessionId); } catch { /* Continue locally when offline. */ }
    }
  },

  complete: async (energyAfter, notes) => {
    const state = get();
    if (state.phase !== "focus" || state.status === "idle") return;
    state._worker?.postMessage({ type: "stop" });
    set({
      activeSessionId: null, energyBefore: null, _pendingSession: null,
      pomodoroCount: state.pomodoroCount + 1,
      _workerRunId: state._workerRunId + 1,
    });
    // Enter the break synchronously so stale messages or a slow request cannot
    // complete the same focus twice or reset a newer session.
    get()._startBreak();
    playSound(playCompleteSound);
    const sessionId = state.activeSessionId ?? await state._pendingSession;
    if (sessionId !== null) {
      try { await sessions.complete(sessionId, { energyAfter: energyAfter, notes }); }
      catch { /* Continue locally when offline. */ }
    }
  },
}));
