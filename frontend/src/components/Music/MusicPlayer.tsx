import { useEffect } from "react";
import type { FlowMode } from "../../types";
import { useMusicStore } from "../../hooks/useMusic";
import { YouTubeEmbed } from "./YouTubeEmbed";
import { PlaylistSelector } from "./PlaylistSelector";
import { Play, Pause, Volume2 } from "lucide-react";

interface MusicPlayerProps {
  currentMode?: FlowMode;
}

export function MusicPlayer({ currentMode }: MusicPlayerProps) {
  const isPlaying = useMusicStore((s) => s.isPlaying);
  const currentTrack = useMusicStore((s) => s.currentTrack);
  const volume = useMusicStore((s) => s.volume);
  const play = useMusicStore((s) => s.play);
  const pause = useMusicStore((s) => s.pause);
  const setVolume = useMusicStore((s) => s.setVolume);
  const setPlaylistByMode = useMusicStore((s) => s.setPlaylistByMode);
  const fetchPlaylists = useMusicStore((s) => s.fetchPlaylists);

  useEffect(() => {
    if (currentMode) setPlaylistByMode(currentMode);
  }, [currentMode, setPlaylistByMode]);

  useEffect(() => { fetchPlaylists(); }, [fetchPlaylists]);

  const handlePlayPause = () => {
    if (isPlaying) pause();
    else play();
  };

  return (
    <div className="card p-4 flex flex-col gap-4">
      <YouTubeEmbed />

      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-ase-gold/10 flex items-center justify-center">
            <Volume2 className="w-3.5 h-3.5 text-ase-gold" />
          </div>
          Music
        </h3>
        <PlaylistSelector />
      </div>

      {/* Track info */}
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={handlePlayPause}
          disabled={!currentTrack}
          className={`
            w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0
            transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed
            ${isPlaying
              ? "bg-ase-gold/15 border border-ase-gold/30 text-ase-gold shadow-glow"
              : "bg-ase-surface border border-ase-border text-ase-muted hover:text-ase-gold hover:border-ase-gold/30"
            }
          `}
        >
          {isPlaying ? (
            <Pause className="w-4 h-4" />
          ) : (
            <Play className="w-4 h-4 ml-0.5" />
          )}
        </button>
        <div className="min-w-0 flex-1">
          <p className={`text-sm truncate ${isPlaying ? "text-white" : "text-ase-muted"}`}>
            {currentTrack?.name ?? "No track selected"}
          </p>
          {isPlaying && (
            <p className="text-xs text-ase-subtle mt-0.5">Now playing</p>
          )}
        </div>
      </div>

      {/* Volume */}
      <div className="flex items-center gap-3">
        <Volume2 className="w-3.5 h-3.5 text-ase-subtle flex-shrink-0" />
        <input
          type="range"
          min={0}
          max={100}
          value={volume}
          onChange={(e) => setVolume(Number(e.target.value))}
          className="flex-1 h-1"
        />
        <span className="text-xs text-ase-subtle w-8 text-right font-mono">{volume}%</span>
      </div>

      {/* Equalizer bars */}
      {isPlaying && (
        <div className="flex items-end gap-[3px] h-4 justify-center">
          {Array.from({ length: 12 }).map((_, i) => (
            <div
              key={i}
              className="w-[3px] bg-ase-gold/50 rounded-t-sm"
              style={{
                height: `${30 + Math.random() * 70}%`,
                animation: `equalizer 0.5s ease-in-out infinite alternate`,
                animationDelay: `${i * 60}ms`,
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
