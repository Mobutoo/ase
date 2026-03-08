import type { FlowMode } from "../../types";
import { useTranslation } from "react-i18next";
import { useTimerStore } from "../../hooks/useTimer";
import { Sparkles, Timer, Gamepad2, Zap, Waves } from "lucide-react";

const MODES: FlowMode[] = ["deep_work", "pomodoro", "kids", "sprint", "free_flow"];

const MODE_CONFIG: Record<FlowMode, {
  icon: typeof Sparkles;
  color: string;
  bgColor: string;
  borderColor: string;
}> = {
  deep_work: {
    icon: Sparkles,
    color: "#8b5cf6",
    bgColor: "rgba(139, 92, 246, 0.1)",
    borderColor: "rgba(139, 92, 246, 0.3)",
  },
  pomodoro: {
    icon: Timer,
    color: "#ef4444",
    bgColor: "rgba(239, 68, 68, 0.1)",
    borderColor: "rgba(239, 68, 68, 0.3)",
  },
  kids: {
    icon: Gamepad2,
    color: "#22c55e",
    bgColor: "rgba(34, 197, 94, 0.1)",
    borderColor: "rgba(34, 197, 94, 0.3)",
  },
  sprint: {
    icon: Zap,
    color: "#eab308",
    bgColor: "rgba(234, 179, 8, 0.1)",
    borderColor: "rgba(234, 179, 8, 0.3)",
  },
  free_flow: {
    icon: Waves,
    color: "#3b82f6",
    bgColor: "rgba(59, 130, 246, 0.1)",
    borderColor: "rgba(59, 130, 246, 0.3)",
  },
};

export function ModeSelector() {
  const { t } = useTranslation();
  const mode = useTimerStore((s) => s.mode);
  const status = useTimerStore((s) => s.status);
  const setMode = useTimerStore((s) => s.setMode);
  const disabled = status !== "idle";

  return (
    <div className="flex gap-2 flex-wrap justify-center max-w-md">
      {MODES.map((m) => {
        const isActive = mode === m;
        const config = MODE_CONFIG[m];
        const Icon = config.icon;
        return (
          <button
            key={m}
            disabled={disabled}
            onClick={() => setMode(m)}
            className={`
              group flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium
              transition-all duration-200
              ${disabled ? "opacity-40 cursor-not-allowed" : "cursor-pointer hover:scale-[1.03] active:scale-[0.97]"}
            `}
            style={{
              background: isActive ? config.bgColor : "rgba(20, 20, 42, 0.6)",
              borderWidth: 1,
              borderStyle: "solid",
              borderColor: isActive ? config.borderColor : "rgba(30, 30, 63, 0.6)",
              color: isActive ? config.color : "#94a3b8",
              boxShadow: isActive ? `0 0 20px ${config.color}15` : "none",
            }}
          >
            <Icon className="w-4 h-4" />
            {t(`mode.${m}`)}
          </button>
        );
      })}
    </div>
  );
}
