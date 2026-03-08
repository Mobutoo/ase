import { TaskList } from "../components/Tasks/TaskList";
import { MusicPlayer } from "../components/Music/MusicPlayer";
import { MiniPlayer } from "../components/Music/MiniPlayer";
import { EnergyCheck } from "../components/Energy/EnergyCheck";
import { EnergyHeatmap } from "../components/Energy/EnergyHeatmap";
import { YouTubeEmbed } from "../components/Music/YouTubeEmbed";

/**
 * TasksPage — Phase 2 full task management UI.
 * Layout: 3-column grid on desktop, stacked on mobile.
 *   Left col (2/3): Task list with filter tabs
 *   Right col (1/3): Music + Energy widgets
 * MiniPlayer: fixed bottom bar
 */
export function TasksPage() {
  return (
    <>
      {/* Hidden YouTube player — mounted once at page level */}
      <YouTubeEmbed />

      <div className="min-h-screen bg-[#0f0f0f] pb-16">
        {/* Page header */}
        <div className="px-6 pt-8 pb-6">
          <div className="max-w-6xl mx-auto">
            <div className="flex items-end justify-between gap-4 mb-1">
              <div>
                <h1 className="text-3xl font-bold text-white tracking-tight">
                  Mission Board
                </h1>
                <p className="text-sm text-[#8a8aae] mt-1">
                  Your unified task list — Local, Plane, GitHub
                </p>
              </div>

              {/* Energy quick-check in header */}
              <div className="hidden md:block bg-[#1a1a2e] border border-[#2a2a3e] rounded-xl px-4 py-3">
                <EnergyCheck label="Energy now?" context="check_in" />
              </div>
            </div>

            {/* Geometric accent line */}
            <div className="mt-4 h-px bg-gradient-to-r from-[#f59e0b]/40 via-[#f59e0b]/10 to-transparent" />
          </div>
        </div>

        {/* Main grid */}
        <div className="px-6 max-w-6xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Tasks column — spans 2/3 */}
            <div className="lg:col-span-2">
              <div className="bg-[#1a1a2e] border border-[#2a2a3e] rounded-2xl p-6 min-h-[600px] flex flex-col">
                <TaskList />
              </div>
            </div>

            {/* Right sidebar */}
            <div className="flex flex-col gap-4">
              {/* Music player */}
              <MusicPlayer />

              {/* Energy check (mobile) */}
              <div className="md:hidden bg-[#1a1a2e] border border-[#2a2a3e] rounded-xl p-4">
                <EnergyCheck label="Energy now?" context="check_in" />
              </div>

              {/* Energy heatmap */}
              <div className="bg-[#1a1a2e] border border-[#2a2a3e] rounded-xl p-4">
                <EnergyHeatmap />
              </div>

              {/* Decorative geometric panel */}
              <div className="bg-[#1a1a2e] border border-[#2a2a3e] rounded-xl p-4 relative overflow-hidden">
                {/* Geometric pattern background */}
                <svg
                  className="absolute inset-0 w-full h-full opacity-5"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <defs>
                    <pattern
                      id="geo"
                      width="30"
                      height="30"
                      patternUnits="userSpaceOnUse"
                    >
                      <path
                        d="M15 0 L30 15 L15 30 L0 15 Z"
                        fill="none"
                        stroke="#f59e0b"
                        strokeWidth="0.5"
                      />
                    </pattern>
                  </defs>
                  <rect width="100%" height="100%" fill="url(#geo)" />
                </svg>

                <div className="relative">
                  <p className="text-xs font-semibold text-[#f59e0b] mb-1 uppercase tracking-wider">
                    Tip
                  </p>
                  <p className="text-xs text-[#8a8aae] leading-relaxed">
                    Click{" "}
                    <span className="text-[#f59e0b]">Start Working</span> on a
                    task to link it with your next focus session.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Fixed mini player at bottom */}
      <MiniPlayer />
    </>
  );
}
