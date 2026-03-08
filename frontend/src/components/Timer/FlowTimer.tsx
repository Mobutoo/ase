import { useTimerStore } from "../../hooks/useTimer";
import { MODE_LABELS } from "../../types";
import { ProgressRing } from "./ProgressRing";
import { ModeSelector } from "./ModeSelector";
import { Controls } from "./Controls";

function formatTime(ms: number): string {
  const totalSeconds = Math.max(0, Math.ceil(ms / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

const PHASE_LABELS = {
  idle: "",
  focus: "Focus",
  short_break: "Short Break",
  long_break: "Long Break",
} as const;

const PHASE_COLORS = {
  idle: "#f59e0b",
  focus: "#f59e0b",
  short_break: "#22c55e",
  long_break: "#3b82f6",
} as const;

export function FlowTimer() {
  const mode = useTimerStore((s) => s.mode);
  const phase = useTimerStore((s) => s.phase);
  const status = useTimerStore((s) => s.status);
  const remainingMs = useTimerStore((s) => s.remainingMs);
  const totalDurationMs = useTimerStore((s) => s.totalDurationMs);
  const pomodoroCount = useTimerStore((s) => s.pomodoroCount);

  const progress =
    totalDurationMs > 0 ? 1 - remainingMs / totalDurationMs : 0;

  const ringColor = PHASE_COLORS[phase];
  const isFreeFlow = mode === "free_flow" && phase === "focus";

  return (
    <div className="flex flex-col items-center gap-8">
      {/* Mode info */}
      <div className="text-center">
        <h2 className="text-2xl font-semibold text-ase-text">
          {MODE_LABELS[mode]}
        </h2>
        {phase !== "idle" && (
          <p
            className="text-sm font-medium mt-1"
            style={{ color: ringColor }}
          >
            {PHASE_LABELS[phase]}
            {mode === "pomodoro" && phase === "focus" && (
              <span className="text-ase-muted ml-2">
                #{pomodoroCount + 1}
              </span>
            )}
          </p>
        )}
      </div>

      {/* Timer ring */}
      <ProgressRing
        progress={isFreeFlow ? 0 : progress}
        color={ringColor}
        bgColor={`${ringColor}22`}
      >
        <div className="flex flex-col items-center">
          <span
            className="text-5xl font-mono font-medium"
            style={{ color: ringColor }}
          >
            {isFreeFlow
              ? formatTime(
                  useTimerStore.getState().elapsedMs
                )
              : formatTime(remainingMs)}
          </span>
          {isFreeFlow && (
            <span className="text-xs text-ase-muted mt-1">elapsed</span>
          )}
        </div>
      </ProgressRing>

      {/* Mode selector (only when idle) */}
      {status === "idle" && <ModeSelector />}

      {/* Controls */}
      <Controls />

      {/* Session counter for pomodoro mode */}
      {mode === "pomodoro" && pomodoroCount > 0 && status === "idle" && (
        <p className="text-ase-muted text-sm">
          {pomodoroCount} session{pomodoroCount !== 1 ? "s" : ""} completed
        </p>
      )}
    </div>
  );
}
