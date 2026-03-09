import type { CalendarEvent } from "../../types/calendar";
import { MapPin, Users, Repeat, Link2 } from "lucide-react";

// ---------------------------------------------------------------------------
// Colour helpers
// ---------------------------------------------------------------------------

const EVENT_TYPE_COLORS: Record<CalendarEvent["eventType"], string> = {
  event: "bg-ase-gold/20 border-ase-gold/40 text-ase-gold",
  recurring: "bg-mode-flow/20 border-mode-flow/40 text-mode-flow",
  background: "bg-zinc-700/30 border-zinc-600/30 text-zinc-400",
  task: "bg-mode-deep/20 border-mode-deep/40 text-purple-300",
  dependent: "bg-orange-500/20 border-orange-500/40 text-orange-300",
};

const DISPLAY_MODE_OPACITY: Record<CalendarEvent["displayMode"], string> = {
  normal: "opacity-100",
  background: "opacity-50",
  private: "opacity-80",
  shared: "opacity-100",
};

// ---------------------------------------------------------------------------
// Format helpers
// ---------------------------------------------------------------------------

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface EventCardProps {
  event: CalendarEvent;
  compact?: boolean;
  onClick?: (event: CalendarEvent) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function EventCard({ event, compact = false, onClick }: EventCardProps) {
  const colorClass = EVENT_TYPE_COLORS[event.eventType] ?? EVENT_TYPE_COLORS.event;
  const opacityClass = DISPLAY_MODE_OPACITY[event.displayMode] ?? "opacity-100";

  const handleClick = () => onClick?.(event);

  if (compact) {
    return (
      <button
        type="button"
        onClick={handleClick}
        className={[
          "w-full text-left rounded-md border px-1.5 py-0.5 text-xs font-medium truncate",
          "transition-all duration-150 hover:brightness-110 active:scale-95",
          colorClass,
          opacityClass,
        ].join(" ")}
        title={event.title}
      >
        {event.allDay ? event.title : `${formatTime(event.startAt)} ${event.title}`}
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      className={[
        "group w-full text-left rounded-lg border px-2.5 py-2 cursor-pointer",
        "transition-all duration-150 hover:brightness-110 hover:shadow-card active:scale-[0.98]",
        colorClass,
        opacityClass,
      ].join(" ")}
    >
      {/* Layer 1 — Title + time */}
      <div className="flex items-start justify-between gap-1 min-w-0">
        <span className="text-xs font-semibold leading-tight truncate">{event.title}</span>
        {event.eventType === "recurring" && (
          <Repeat className="w-3 h-3 flex-shrink-0 opacity-70 mt-0.5" />
        )}
        {event.linkedTaskId && (
          <Link2 className="w-3 h-3 flex-shrink-0 opacity-70 mt-0.5" />
        )}
      </div>

      {!event.allDay && (
        <p className="text-[10px] opacity-70 mt-0.5 leading-none">
          {formatTime(event.startAt)} – {formatTime(event.endAt)}
        </p>
      )}

      {/* Layer 2 — Location */}
      {event.location && (
        <p className="flex items-center gap-1 text-[10px] opacity-60 mt-1 leading-none truncate">
          <MapPin className="w-2.5 h-2.5 flex-shrink-0" />
          {event.location}
        </p>
      )}

      {/* Layer 3 — Members */}
      {event.members.length > 0 && (
        <div className="flex items-center gap-1 mt-1.5">
          <Users className="w-2.5 h-2.5 opacity-50" />
          <div className="flex -space-x-1.5">
            {event.members.slice(0, 4).map((m) => (
              <div
                key={m.id}
                className="w-4 h-4 rounded-full border border-current/20 flex items-center justify-center text-[8px] font-bold"
                style={{ backgroundColor: m.avatarColor + "40", color: m.avatarColor }}
                title={m.displayName}
              >
                {m.avatarEmoji || m.displayName[0]?.toUpperCase()}
              </div>
            ))}
            {event.members.length > 4 && (
              <div className="w-4 h-4 rounded-full bg-zinc-700 border border-zinc-600 flex items-center justify-center text-[8px] text-zinc-400">
                +{event.members.length - 4}
              </div>
            )}
          </div>
        </div>
      )}
    </button>
  );
}
