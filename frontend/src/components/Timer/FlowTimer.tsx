import { useTranslation } from "react-i18next";
import { useTimerStore } from "../../hooks/useTimer";
import { ProgressRing } from "./ProgressRing";
import { ModeSelector } from "./ModeSelector";
import { Controls } from "./Controls";

function formatTime(ms: number): string {
  const totalSeconds = Math.max(0, Math.ceil(ms / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

const PHASE_COLORS = {
  idle: "#f59e0b",
  focus: "#f59e0b",
  short_break: "#22c55e",
  long_break: "#3b82f6",
} as const;

export function FlowTimer() {
  const { t } = useTranslation();
  const mode = useTimerStore((s) => s.mode);
  const phase = useTimerStore((s) => s.phase);
  const status = useTimerStore((s) => s.status);
  const remainingMs = useTimerStore((s) => s.remainingMs);
  const totalDurationMs = useTimerStore((s) => s.totalDurationMs);
  const pomodoroCount = useTimerStore((s) => s.pomodoroCount);

  const progress = totalDurationMs > 0 ? 1 - remainingMs / totalDurationMs : 0;
  const ringColor = PHASE_COLORS[phase];
  const isFreeFlow = mode === "free_flow" && phase === "focus";
  const isActive = status !== "idle";

  return (
    <div className="flex flex-col items-center gap-8">
      {/* Mode badge */}
      <div className="text-center">
        <div className={`
          inline-flex items-center gap-2 px-4 py-1.5 rounded-full
          border transition-all duration-300
          ${isActive
            ? "bg-ase-gold/10 border-ase-gold/30 shadow-glow"
            : "bg-ase-surface border-ase-border"
          }
        `}>
          <span className="text-sm font-semibold text-ase-text">
            {t(`mode.${mode}`)}
          </span>
          {phase !== "idle" && (
            <>
              <span className="w-1 h-1 rounded-full bg-ase-muted/40" />
              <span className="text-sm font-medium" style={{ color: ringColor }}>
                {t(`phase.${phase}`)}
                {mode === "pomodoro" && phase === "focus" && (
                  <span className="text-ase-muted ml-1.5 font-mono text-xs">
                    #{pomodoroCount + 1}
                  </span>
                )}
              </span>
            </>
          )}
        </div>
      </div>

      {/* Timer ring */}
      <div className={isActive ? "animate-scale-in" : ""}>
        <ProgressRing
          progress={isFreeFlow ? 0 : progress}
          color={ringColor}
          bgColor={`${ringColor}15`}
        >
          <div className="flex flex-col items-center">
            <span
              className="text-6xl font-mono font-semibold tracking-tight"
              style={{ color: ringColor }}
            >
              {isFreeFlow
                ? formatTime(useTimerStore.getState().elapsedMs)
                : formatTime(remainingMs)}
            </span>
            {isFreeFlow && (
              <span className="text-xs text-ase-muted mt-1.5 uppercase tracking-widest">
                {t("timer.elapsed")}
              </span>
            )}
          </div>
        </ProgressRing>
      </div>

      {/* Mode selector (idle only) */}
      {status === "idle" && <ModeSelector />}

      {/* Controls */}
      <Controls />

      {/* Pomodoro session dots */}
      {mode === "pomodoro" && pomodoroCount > 0 && status === "idle" && (
        <div className="flex items-center gap-2">
          {Array.from({ length: Math.min(pomodoroCount, 8) }).map((_, i) => (
            <div key={i} className="w-2 h-2 rounded-full bg-ase-gold/60" />
          ))}
          <span className="text-xs text-ase-muted ml-1">{pomodoroCount} {t("timer.done")}</span>
        </div>
      )}
    </div>
  );
}
