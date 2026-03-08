import { useEffect } from "react";
import type { FlowMode } from "../../types";
import { useMusicStore } from "../../hooks/useMusic";
import { YouTubeEmbed } from "./YouTubeEmbed";
import { PlaylistSelector } from "./PlaylistSelector";

interface MusicPlayerProps {
  /** Pass current timer mode to auto-select playlist */
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

  // Auto-select playlist on mode change
  useEffect(() => {
    if (currentMode) {
      setPlaylistByMode(currentMode);
    }
  }, [currentMode, setPlaylistByMode]);

  // Prefetch available playlists
  useEffect(() => {
    fetchPlaylists();
  }, [fetchPlaylists]);

  const handlePlayPause = () => {
    if (isPlaying) {
      pause();
    } else {
      play();
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setVolume(Number(e.target.value));
  };

  return (
    <div className="bg-[#1a1a2e] rounded-xl border border-[#2a2a3e] p-4 flex flex-col gap-4">
      {/* Hidden YouTube player */}
      <YouTubeEmbed />

      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <span>🎵</span> Music
        </h3>
        <PlaylistSelector />
      </div>

      {/* Track name */}
      <div className="flex items-center gap-2 min-w-0">
        <div
          className={`
            w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0
            ${isPlaying ? "bg-[#f59e0b]/20 border border-[#f59e0b]/30" : "bg-[#2a2a3e] border border-[#3a3a4e]"}
          `}
        >
          <span className="text-sm">{isPlaying ? "▶" : "⏸"}</span>
        </div>
        <p className="text-sm text-[#c0c0d8] truncate">
          {currentTrack?.name ?? "No track selected"}
        </p>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-3">
        {/* Play/Pause button */}
        <button
          onClick={handlePlayPause}
          disabled={!currentTrack}
          className="
            w-10 h-10 rounded-full flex items-center justify-center
            bg-[#f59e0b]/20 text-[#f59e0b] border border-[#f59e0b]/30
            hover:bg-[#f59e0b]/30 transition-colors duration-150
            disabled:opacity-40 disabled:cursor-not-allowed
          "
        >
          {isPlaying ? (
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
            </svg>
          ) : (
            <svg className="w-4 h-4 ml-0.5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M8 5v14l11-7z" />
            </svg>
          )}
        </button>

        {/* Volume slider */}
        <div className="flex items-center gap-2 flex-1">
          <svg
            className="w-4 h-4 text-[#8a8aae] flex-shrink-0"
            fill="currentColor"
            viewBox="0 0 24 24"
          >
            <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z" />
          </svg>
          <input
            type="range"
            min={0}
            max={100}
            value={volume}
            onChange={handleVolumeChange}
            className="flex-1 h-1 appearance-none bg-[#2a2a3e] rounded-full cursor-pointer"
            style={{ accentColor: "#f59e0b" }}
          />
          <span className="text-xs text-[#8a8aae] w-7 text-right">{volume}%</span>
        </div>
      </div>

      {/* Equalizer bars (playing indicator) */}
      {isPlaying && (
        <div className="flex items-end gap-0.5 h-4 justify-center">
          {Array.from({ length: 8 }).map((_, i) => (
            <div
              key={i}
              className="w-1 bg-[#f59e0b]/60 rounded-t-sm"
              style={{
                height: `${30 + Math.random() * 70}%`,
                animation: `equalizer 0.5s ease-in-out infinite alternate`,
                animationDelay: `${i * 80}ms`,
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
