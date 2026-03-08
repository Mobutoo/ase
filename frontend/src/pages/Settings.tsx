import { Settings as SettingsIcon, Timer, Music, Zap, Palette } from "lucide-react";

export function Settings() {
  return (
    <div className="flex flex-col gap-6 p-6 lg:p-10 min-h-screen max-w-3xl">
      {/* Header */}
      <div className="animate-fade-in">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-8 h-8 rounded-lg bg-ase-gold/10 border border-ase-gold/20 flex items-center justify-center">
            <SettingsIcon className="w-4 h-4 text-ase-gold" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Settings</h1>
        </div>
        <p className="text-sm text-ase-muted ml-11">
          Customize your flow experience
        </p>
      </div>

      {/* Settings sections */}
      <div className="flex flex-col gap-4">
        {[
          { icon: Timer, title: "Timer Durations", desc: "Configure focus, break, and session durations for each mode" },
          { icon: Music, title: "Music & Playlists", desc: "Default playlists per mode, YouTube URLs, volume preferences" },
          { icon: Zap, title: "Task Sources", desc: "Connect Plane, GitHub, or other task sources" },
          { icon: Palette, title: "Appearance", desc: "Theme, accent color, and display preferences" },
        ].map(({ icon: Icon, title, desc }) => (
          <div key={title} className="card p-5 flex items-center gap-4 cursor-pointer group animate-slide-up">
            <div className="w-10 h-10 rounded-xl bg-ase-gold/10 border border-ase-gold/20 flex items-center justify-center flex-shrink-0 group-hover:bg-ase-gold/15 transition-colors">
              <Icon className="w-5 h-5 text-ase-gold" />
            </div>
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-white">{title}</h3>
              <p className="text-xs text-ase-muted mt-0.5">{desc}</p>
            </div>
            <span className="text-ase-subtle text-xs px-3 py-1 rounded-full border border-ase-border">
              Coming soon
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
