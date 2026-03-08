import { TaskList } from "../components/Tasks/TaskList";
import { MusicPlayer } from "../components/Music/MusicPlayer";
import { MiniPlayer } from "../components/Music/MiniPlayer";
import { EnergyCheck } from "../components/Energy/EnergyCheck";
import { EnergyHeatmap } from "../components/Energy/EnergyHeatmap";
import { YouTubeEmbed } from "../components/Music/YouTubeEmbed";
import { Flame, Lightbulb } from "lucide-react";

export function TasksPage() {
  return (
    <>
      <YouTubeEmbed />

      <div className="min-h-screen bg-ase-bg pb-20">
        {/* Page header */}
        <div className="px-6 lg:px-10 pt-8 pb-6">
          <div className="max-w-6xl mx-auto">
            <div className="flex items-end justify-between gap-4 mb-1">
              <div className="animate-fade-in">
                <div className="flex items-center gap-3 mb-1">
                  <div className="w-8 h-8 rounded-lg bg-ase-gold/10 border border-ase-gold/20 flex items-center justify-center">
                    <Flame className="w-4 h-4 text-ase-gold" />
                  </div>
                  <h1 className="text-2xl font-bold text-white tracking-tight">
                    Mission Board
                  </h1>
                </div>
                <p className="text-sm text-ase-muted ml-11">
                  Your unified task list — Local, Plane, GitHub
                </p>
              </div>

              {/* Energy quick-check */}
              <div className="hidden md:block glass rounded-2xl px-5 py-3 animate-fade-in">
                <EnergyCheck label="Energy now?" context="check_in" />
              </div>
            </div>

            {/* Accent line */}
            <div className="mt-5 h-px bg-gradient-to-r from-ase-gold/30 via-ase-gold/10 to-transparent" />
          </div>
        </div>

        {/* Main grid */}
        <div className="px-6 lg:px-10 max-w-6xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Tasks column */}
            <div className="lg:col-span-2 animate-slide-up">
              <div className="card p-6 min-h-[600px] flex flex-col">
                <TaskList />
              </div>
            </div>

            {/* Right sidebar */}
            <div className="flex flex-col gap-4" style={{ animationDelay: "0.1s" }}>
              {/* Music player */}
              <div className="animate-slide-up" style={{ animationDelay: "0.15s" }}>
                <MusicPlayer />
              </div>

              {/* Energy check (mobile) */}
              <div className="md:hidden card p-4 animate-slide-up">
                <EnergyCheck label="Energy now?" context="check_in" />
              </div>

              {/* Energy heatmap */}
              <div className="card p-4 animate-slide-up" style={{ animationDelay: "0.2s" }}>
                <EnergyHeatmap />
              </div>

              {/* Tip card */}
              <div className="card p-4 relative overflow-hidden animate-slide-up" style={{ animationDelay: "0.25s" }}>
                <div className="absolute inset-0 bg-gradient-to-br from-ase-gold/[0.03] to-transparent pointer-events-none" />
                <div className="relative flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-ase-gold/10 border border-ase-gold/20 flex items-center justify-center flex-shrink-0">
                    <Lightbulb className="w-4 h-4 text-ase-gold" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-ase-gold mb-1 uppercase tracking-wider">
                      Pro Tip
                    </p>
                    <p className="text-xs text-ase-muted leading-relaxed">
                      Click{" "}
                      <span className="text-ase-gold font-medium">Start Working</span> on a
                      task to link it with your next focus session.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <MiniPlayer />
    </>
  );
}
