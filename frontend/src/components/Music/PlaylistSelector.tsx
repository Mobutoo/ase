import { useEffect, useState } from "react";
import type { Playlist } from "../../types/phase2";
import { useMusicStore } from "../../hooks/useMusic";

export function PlaylistSelector() {
  const availablePlaylists = useMusicStore((s) => s.availablePlaylists);
  const currentTrack = useMusicStore((s) => s.currentTrack);
  const setPlaylist = useMusicStore((s) => s.setPlaylist);
  const fetchPlaylists = useMusicStore((s) => s.fetchPlaylists);

  const [isOpen, setIsOpen] = useState(false);
  const [customUrl, setCustomUrl] = useState("");
  const [showCustomInput, setShowCustomInput] = useState(false);

  useEffect(() => {
    if (availablePlaylists.length === 0) {
      fetchPlaylists();
    }
  }, [availablePlaylists.length, fetchPlaylists]);

  const handleSelect = (playlist: Playlist) => {
    setPlaylist(playlist);
    setIsOpen(false);
    setShowCustomInput(false);
  };

  const handleCustomSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = customUrl.trim();
    if (!trimmed) return;
    const customPlaylist: Playlist = {
      id: `custom-${Date.now()}`,
      name: "Custom — " + trimmed.slice(0, 40),
      youtubeUrl: trimmed,
      mode: "custom",
      isDefault: false,
      isCustom: true,
    };
    setPlaylist(customPlaylist);
    setCustomUrl("");
    setIsOpen(false);
    setShowCustomInput(false);
  };

  const displayName = currentTrack?.name ?? "Select playlist...";

  return (
    <div className="relative">
      {/* Trigger button */}
      <button
        onClick={() => setIsOpen((v) => !v)}
        className="
          flex items-center gap-2 px-3 py-2 rounded-lg text-sm
          bg-[#0f0f1a] border border-[#2a2a3e] text-white
          hover:border-[#f59e0b]/40 transition-colors duration-150
          max-w-[220px] truncate
        "
      >
        <span className="text-[#f59e0b]">🎵</span>
        <span className="truncate flex-1 text-left text-[#c0c0d8]">
          {displayName}
        </span>
        <svg
          className={`w-4 h-4 text-[#8a8aae] transition-transform ${isOpen ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="
          absolute bottom-full left-0 mb-2 w-72
          bg-[#1a1a2e] border border-[#2a2a3e] rounded-xl shadow-2xl
          overflow-hidden z-50
        ">
          <div className="p-1">
            {availablePlaylists
              .filter((p) => !p.isCustom)
              .map((playlist) => (
                <button
                  key={playlist.id}
                  onClick={() => handleSelect(playlist)}
                  className={`
                    w-full text-left px-3 py-2.5 rounded-lg text-sm
                    transition-colors duration-100
                    flex items-center gap-2
                    ${
                      currentTrack?.id === playlist.id
                        ? "bg-[#f59e0b]/20 text-[#f59e0b]"
                        : "text-[#c0c0d8] hover:bg-[#2a2a3e]"
                    }
                  `}
                >
                  <span className="text-base">🎵</span>
                  <span className="flex-1 truncate">{playlist.name}</span>
                  {currentTrack?.id === playlist.id && (
                    <svg
                      className="w-4 h-4 flex-shrink-0"
                      fill="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z" />
                    </svg>
                  )}
                </button>
              ))}

            {/* Divider + custom URL */}
            <div className="border-t border-[#2a2a3e] my-1" />

            {!showCustomInput ? (
              <button
                onClick={() => setShowCustomInput(true)}
                className="
                  w-full text-left px-3 py-2.5 rounded-lg text-sm
                  text-[#8a8aae] hover:bg-[#2a2a3e] hover:text-white
                  transition-colors duration-100 flex items-center gap-2
                "
              >
                <span>➕</span>
                <span>Custom YouTube URL</span>
              </button>
            ) : (
              <form onSubmit={handleCustomSubmit} className="px-3 py-2 flex gap-2">
                <input
                  autoFocus
                  type="url"
                  value={customUrl}
                  onChange={(e) => setCustomUrl(e.target.value)}
                  placeholder="youtube.com/watch?v=..."
                  className="
                    flex-1 bg-[#0f0f1a] border border-[#2a2a3e] rounded-lg
                    px-2 py-1.5 text-xs text-white placeholder-[#4a4a6e]
                    focus:outline-none focus:border-[#f59e0b]/50
                  "
                />
                <button
                  type="submit"
                  className="
                    px-2 py-1.5 rounded-lg text-xs
                    bg-[#f59e0b]/20 text-[#f59e0b] border border-[#f59e0b]/30
                    hover:bg-[#f59e0b]/30 transition-colors
                  "
                >
                  Go
                </button>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
