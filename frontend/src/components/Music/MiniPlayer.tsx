import { useTranslation } from "react-i18next";
import { useMusicStore } from "../../hooks/useMusic";
import { PlaylistSelector } from "./PlaylistSelector";
import { Play, Pause, Volume2, Music } from "lucide-react";

interface MiniPlayerProps {
  /** Left offset in pixels (matches sidebar width) */
  leftOffset?: number;
  /** When true, hides the bar for immersive focus mode */
  dimmed?: boolean;
}

export function MiniPlayer({ leftOffset = 0, dimmed = false }: MiniPlayerProps) {
  const { t } = useTranslation();
  const isPlaying = useMusicStore((s) => s.isPlaying);
  const currentTrack = useMusicStore((s) => s.currentTrack);
  const volume = useMusicStore((s) => s.volume);
  const play = useMusicStore((s) => s.play);
  const pause = useMusicStore((s) => s.pause);
  const setVolume = useMusicStore((s) => s.setVolume);

  const handlePlayPause = () => {
    if (isPlaying) pause();
    else play();
  };

  return (
    <div
      className={`fixed bottom-0 right-0 z-40 h-14 glass-strong flex items-center px-4 gap-4 transition-all duration-300 ${
        dimmed ? "opacity-0 pointer-events-none" : ""
      }`}
      style={{ left: `${leftOffset}px` }}
    >
      {/* Track info */}
      <div className="flex items-center gap-2.5 min-w-0 flex-1">
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 transition-all ${
          isPlaying ? "bg-ase-gold/10 border border-ase-gold/20" : "bg-ase-surface border border-ase-border"
        }`}>
          <Music className={`w-3.5 h-3.5 ${isPlaying ? "text-ase-gold" : "text-ase-muted"}`} />
        </div>
        <span className={`text-sm truncate ${isPlaying ? "text-white" : "text-ase-muted"}`}>
          {currentTrack?.name ?? t("music.no_track")}
        </span>
        {isPlaying && (
          <span className="flex-shrink-0 flex gap-[2px] items-end h-3">
            {[0, 120, 240].map((delay) => (
              <span key={delay} className="w-[2px] bg-ase-gold/60 rounded-full"
                style={{ height: "100%", animation: `equalizer 0.7s ease-in-out infinite alternate`, animationDelay: `${delay}ms` }} />
            ))}
          </span>
        )}
      </div>

      {/* Play/Pause */}
      <button
        onClick={handlePlayPause}
        disabled={!currentTrack}
        className={`w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed ${
          isPlaying
            ? "bg-ase-gold/15 text-ase-gold border border-ase-gold/25 shadow-glow"
            : "bg-ase-surface text-ase-muted border border-ase-border hover:text-ase-gold hover:border-ase-gold/30"
        }`}
      >
        {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 ml-0.5" />}
      </button>

      <PlaylistSelector />

      {/* Volume */}
      <div className="hidden sm:flex items-center gap-2 flex-shrink-0">
        <Volume2 className="w-3.5 h-3.5 text-ase-subtle" />
        <input type="range" min={0} max={100} value={volume}
          onChange={(e) => setVolume(Number(e.target.value))}
          className="w-20 h-1" />
        <span className="text-xs text-ase-subtle w-7 text-right font-mono">{volume}</span>
      </div>
    </div>
  );
}
