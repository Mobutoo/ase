import { useTimerStore } from "../../hooks/useTimer";

export function Controls() {
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
        className="px-10 py-3.5 rounded-xl bg-ase-gold text-ase-bg font-semibold text-lg
          hover:bg-ase-amber transition-colors active:scale-95"
      >
        Start Focus
      </button>
    );
  }

  const isBreak = phase === "short_break" || phase === "long_break";

  return (
    <div className="flex gap-3 items-center">
      {status === "running" ? (
        <button
          onClick={pause}
          className="px-6 py-3 rounded-xl bg-ase-surface border border-ase-border text-ase-text font-medium
            hover:border-ase-gold/50 transition-colors"
        >
          Pause
        </button>
      ) : (
        <button
          onClick={resume}
          className="px-6 py-3 rounded-xl bg-ase-gold/20 border border-ase-gold text-ase-gold font-medium
            hover:bg-ase-gold/30 transition-colors"
        >
          Resume
        </button>
      )}

      {!isBreak && (
        <button
          onClick={stop}
          className="px-6 py-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 font-medium
            hover:bg-red-500/20 transition-colors"
        >
          Stop
        </button>
      )}
    </div>
  );
}
