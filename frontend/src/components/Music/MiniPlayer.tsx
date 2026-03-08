import { useMusicStore } from "../../hooks/useMusic";
import { PlaylistSelector } from "./PlaylistSelector";

export function MiniPlayer() {
  const isPlaying = useMusicStore((s) => s.isPlaying);
  const currentTrack = useMusicStore((s) => s.currentTrack);
  const volume = useMusicStore((s) => s.volume);
  const play = useMusicStore((s) => s.play);
  const pause = useMusicStore((s) => s.pause);
  const setVolume = useMusicStore((s) => s.setVolume);

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
    <div
      className="
        fixed bottom-0 left-0 right-0 z-40
        h-12 bg-[#1a1a2e] border-t border-[#2a2a3e]
        flex items-center px-4 gap-3
        backdrop-blur-sm
      "
    >
      {/* Track info */}
      <div className="flex items-center gap-2 min-w-0 flex-1">
        <span className="text-base flex-shrink-0">🎵</span>
        <span className="text-xs text-[#c0c0d8] truncate">
          {currentTrack?.name ?? "No track selected"}
        </span>
        {isPlaying && (
          <span className="flex-shrink-0 flex gap-0.5 items-end h-3">
            {[0, 150, 300].map((delay) => (
              <span
                key={delay}
                className="w-0.5 bg-[#f59e0b] rounded-full"
                style={{
                  height: "100%",
                  animation: `equalizer 0.8s ease-in-out infinite alternate`,
                  animationDelay: `${delay}ms`,
                }}
              />
            ))}
          </span>
        )}
      </div>

      {/* Play / Pause */}
      <button
        onClick={handlePlayPause}
        disabled={!currentTrack}
        className="
          w-8 h-8 rounded-full flex items-center justify-center
          bg-[#f59e0b]/20 text-[#f59e0b] border border-[#f59e0b]/30
          hover:bg-[#f59e0b]/30 transition-colors duration-150
          disabled:opacity-40 disabled:cursor-not-allowed
          flex-shrink-0
        "
      >
        {isPlaying ? (
          <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
          </svg>
        ) : (
          <svg className="w-3.5 h-3.5 ml-0.5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z" />
          </svg>
        )}
      </button>

      {/* Playlist selector */}
      <PlaylistSelector />

      {/* Volume */}
      <div className="hidden sm:flex items-center gap-2 flex-shrink-0">
        <svg
          className="w-4 h-4 text-[#8a8aae]"
          fill="currentColor"
          viewBox="0 0 24 24"
        >
          <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z" />
        </svg>
        <input
          type="range"
          min={0}
          max={100}
          value={volume}
          onChange={handleVolumeChange}
          className="w-20 h-1 appearance-none bg-[#2a2a3e] rounded-full cursor-pointer accent-[#f59e0b]"
          style={{ accentColor: "#f59e0b" }}
        />
        <span className="text-xs text-[#8a8aae] w-6 text-right">{volume}</span>
      </div>
    </div>
  );
}
