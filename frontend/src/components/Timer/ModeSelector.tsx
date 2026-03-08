import type { FlowMode } from "../../types";
import { MODE_LABELS } from "../../types";
import { useTimerStore } from "../../hooks/useTimer";

const MODES: FlowMode[] = ["deep_work", "pomodoro", "kids", "sprint", "free_flow"];

const MODE_ICONS: Record<FlowMode, string> = {
  deep_work: "\u2728", // sparkles
  pomodoro: "\u23f0", // alarm clock
  kids: "\u{1f3ae}", // video game controller
  sprint: "\u26a1", // lightning
  free_flow: "\u{1f30a}", // wave
};

export function ModeSelector() {
  const mode = useTimerStore((s) => s.mode);
  const status = useTimerStore((s) => s.status);
  const setMode = useTimerStore((s) => s.setMode);

  return (
    <div className="flex gap-2 flex-wrap justify-center">
      {MODES.map((m) => {
        const isActive = mode === m;
        const disabled = status !== "idle";
        return (
          <button
            key={m}
            disabled={disabled}
            onClick={() => setMode(m)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all
              ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
              ${
                isActive
                  ? "bg-ase-gold/20 border-ase-gold text-ase-gold border"
                  : "bg-ase-surface border border-ase-border text-ase-muted hover:text-ase-gold hover:border-ase-gold/50"
              }`}
          >
            <span className="mr-1.5">{MODE_ICONS[m]}</span>
            {MODE_LABELS[m]}
          </button>
        );
      })}
    </div>
  );
}
