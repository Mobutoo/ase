import { useTranslation } from "react-i18next";
import { useTimerStore } from "../../hooks/useTimer";
import { Play, Pause, Square, RotateCcw } from "lucide-react";

export function Controls() {
  const { t } = useTranslation();
  const status = useTimerStore((s) => s.status);
  const phase = useTimerStore((s) => s.phase);
  const start = useTimerStore((s) => s.start);
  const pause = useTimerStore((s) => s.pause);
  const resume = useTimerStore((s) => s.resume);
  const stop = useTimerStore((s) => s.stop);

  if (phase === "idle" || status === "idle") {
    return (
      <button
        onClick={() => start()}
        className="
          group relative px-12 py-4 rounded-2xl font-semibold text-lg
          bg-gradient-to-r from-ase-gold to-ase-amber text-ase-bg
          hover:shadow-glow-lg transition-all duration-300
          active:scale-[0.97] overflow-hidden
        "
      >
        <span className="relative z-10 flex items-center gap-2.5">
          <Play className="w-5 h-5 fill-current" />
          {t("timer.start")}
        </span>
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
      </button>
    );
  }

  const isBreak = phase === "short_break" || phase === "long_break";

  return (
    <div className="flex gap-3 items-center">
      {status === "running" ? (
        <button
          onClick={pause}
          className="flex items-center gap-2 px-6 py-3 rounded-xl bg-ase-surface border border-ase-border text-ase-text font-medium hover:border-ase-gold/40 transition-all duration-200 active:scale-[0.97]"
        >
          <Pause className="w-4 h-4" />
          {t("timer.pause")}
        </button>
      ) : (
        <button
          onClick={resume}
          className="flex items-center gap-2 px-6 py-3 rounded-xl bg-ase-gold/15 border border-ase-gold/30 text-ase-gold font-medium hover:bg-ase-gold/25 hover:shadow-glow transition-all duration-200 active:scale-[0.97]"
        >
          <RotateCcw className="w-4 h-4" />
          {t("timer.resume")}
        </button>
      )}

      {!isBreak && (
        <button
          onClick={stop}
          className="flex items-center gap-2 px-6 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 font-medium hover:bg-red-500/15 hover:border-red-500/30 transition-all duration-200 active:scale-[0.97]"
        >
          <Square className="w-4 h-4" />
          {t("timer.stop")}
        </button>
      )}
    </div>
  );
}
