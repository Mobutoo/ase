import { useEffect, useRef } from "react";
import { useMusicStore } from "../../hooks/useMusic";

// YouTube IFrame API types (minimal)
declare global {
  interface Window {
    YT: {
      Player: new (
        el: HTMLElement,
        opts: {
          videoId?: string;
          playerVars?: Record<string, number | string>;
          events?: {
            onReady?: (e: { target: YTPlayer }) => void;
            onStateChange?: (e: { data: number }) => void;
            onError?: () => void;
          };
        }
      ) => YTPlayer;
      PlayerState: { PLAYING: number; PAUSED: number; ENDED: number };
    };
    onYouTubeIframeAPIReady: () => void;
  }
}

interface YTPlayer {
  playVideo(): void;
  pauseVideo(): void;
  setVolume(v: number): void;
  loadVideoById(id: string): void;
  loadPlaylist(opts: { listType: string; list: string }): void;
  destroy(): void;
}

function extractVideoId(url: string): string | null {
  const match = url.match(
    /(?:v=|youtu\.be\/|embed\/)([A-Za-z0-9_-]{11})/
  );
  return match ? match[1] : null;
}

function extractPlaylistId(url: string): string | null {
  const match = url.match(/[?&]list=([A-Za-z0-9_-]+)/);
  return match ? match[1] : null;
}

let apiLoadStarted = false;

function loadYouTubeApi(onReady: () => void) {
  if (window.YT?.Player) {
    onReady();
    return;
  }
  const prev = window.onYouTubeIframeAPIReady;
  window.onYouTubeIframeAPIReady = () => {
    prev?.();
    onReady();
  };
  if (!apiLoadStarted) {
    apiLoadStarted = true;
    const script = document.createElement("script");
    script.src = "https://www.youtube.com/iframe_api";
    document.head.appendChild(script);
  }
}

export function YouTubeEmbed() {
  const isPlaying = useMusicStore((s) => s.isPlaying);
  const currentTrack = useMusicStore((s) => s.currentTrack);
  const volume = useMusicStore((s) => s.volume);
  const playerReady = useMusicStore((s) => s._playerReady);
  const setPlayerReady = useMusicStore((s) => s.setPlayerReady);
  const pause = useMusicStore((s) => s.pause);

  const containerRef = useRef<HTMLDivElement>(null);
  const playerRef = useRef<YTPlayer | null>(null);
  const readyRef = useRef(false);       // API loaded + player created
  const playerReadyRef = useRef(false);  // onReady fired — methods safe to call

  // Load API + create player
  useEffect(() => {
    loadYouTubeApi(() => {
      if (!containerRef.current || readyRef.current) return;
      readyRef.current = true;

      playerRef.current = new window.YT.Player(containerRef.current, {
        playerVars: {
          autoplay: 0,
          controls: 0,
          modestbranding: 1,
          rel: 0,
          showinfo: 0,
        },
        events: {
          onReady: () => {
            playerReadyRef.current = true;
            setPlayerReady(true);
          },
          onStateChange: (e) => {
            if (e.data === window.YT.PlayerState.ENDED) pause();
          },
          onError: () => pause(),
        },
      });
    });

    return () => {
      playerRef.current?.destroy();
      playerRef.current = null;
      readyRef.current = false;
      playerReadyRef.current = false;
      setPlayerReady(false);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Load track when currentTrack changes OR player becomes ready
  useEffect(() => {
    const player = playerRef.current;
    if (!player || !playerReady || !currentTrack?.youtubeUrl) return;

    const listId = extractPlaylistId(currentTrack.youtubeUrl);
    const videoId = extractVideoId(currentTrack.youtubeUrl);

    if (listId) {
      player.loadPlaylist({ listType: "playlist", list: listId });
    } else if (videoId) {
      player.loadVideoById(videoId);
    }
  }, [currentTrack, playerReady]);

  // Play / pause (re-runs when player becomes ready)
  useEffect(() => {
    const player = playerRef.current;
    if (!player || !playerReady) return;
    if (isPlaying) {
      player.playVideo();
    } else {
      player.pauseVideo();
    }
  }, [isPlaying, playerReady]);

  // Volume (re-runs when player becomes ready)
  useEffect(() => {
    if (!playerReady) return;
    playerRef.current?.setVolume(volume);
  }, [volume, playerReady]);

  // Hidden player — visually invisible but mounted in DOM
  return (
    <div className="absolute -top-[9999px] -left-[9999px] pointer-events-none" aria-hidden="true">
      <div ref={containerRef} style={{ width: 1, height: 1 }} />
    </div>
  );
}
