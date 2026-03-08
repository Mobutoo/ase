import { useEffect } from "react";
import { FlowTimer } from "../components/Timer/FlowTimer";
import { useTimerStore } from "../hooks/useTimer";

export function Home() {
  useEffect(() => {
    if ("Notification" in window && Notification.permission === "default") {
      Notification.requestPermission();
    }
  }, []);

  const phase = useTimerStore((s) => s.phase);
  const isActive = phase !== "idle";

  return (
    <div className="min-h-screen flex flex-col items-center justify-center relative overflow-hidden px-6">
      {/* Background ambient glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div
          className={`
            absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2
            w-[600px] h-[600px] rounded-full
            transition-all duration-1000
            ${isActive
              ? "bg-ase-gold/[0.04] blur-[120px]"
              : "bg-ase-gold/[0.02] blur-[100px]"
            }
          `}
        />
        <div className="absolute top-20 left-20 w-32 h-32 border border-ase-border/20 rounded-full opacity-30" />
        <div className="absolute bottom-32 right-24 w-48 h-48 border border-ase-gold/10 rotate-45 opacity-20" />
        <div className="absolute top-40 right-40 w-2 h-2 bg-ase-gold/30 rounded-full animate-float" />
        <div className="absolute bottom-60 left-40 w-1.5 h-1.5 bg-ase-gold/20 rounded-full animate-float" style={{ animationDelay: "1s" }} />
      </div>

      <div className="relative z-10 flex flex-col items-center gap-6 animate-fade-in">
        {!isActive && (
          <div className="text-center mb-4 animate-slide-up">
            <h2 className="text-5xl font-extrabold bg-gradient-to-r from-ase-gold via-ase-accent to-ase-amber bg-clip-text text-transparent">
              Asé
            </h2>
            <p className="text-ase-muted text-sm mt-2 tracking-wide">
              The power to make things happen
            </p>
          </div>
        )}
        <FlowTimer />
      </div>
    </div>
  );
}
