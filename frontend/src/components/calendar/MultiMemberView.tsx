import { useMemo, useRef, useEffect, useState } from "react";
import type { CalendarEvent } from "../../types/calendar";
import type { CircleMember } from "../../types/circle";
import { Users } from "lucide-react";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const HOURS = Array.from({ length: 24 }, (_, i) => i);
const SLOT_HEIGHT_PX = 60;
const MIN_EVENT_PX = 14;
const WORK_START_HOUR = 7;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function isoToDate(iso: string): Date {
  return new Date(iso);
}

function toDateKey(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function topPx(iso: string): number {
  const d = isoToDate(iso);
  return (d.getHours() + d.getMinutes() / 60) * SLOT_HEIGHT_PX;
}

function heightPx(startIso: string, endIso: string): number {
  const diff =
    (isoToDate(endIso).getTime() - isoToDate(startIso).getTime()) / 3_600_000;
  return Math.max(diff * SLOT_HEIGHT_PX, MIN_EVENT_PX);
}

function formatHour(h: number): string {
  const p = h < 12 ? "AM" : "PM";
  const d = h === 0 ? 12 : h > 12 ? h - 12 : h;
  return `${d}${p}`;
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface MultiMemberViewProps {
  date: string; // YYYY-MM-DD
  events: CalendarEvent[];
  members: CircleMember[];
  onEventClick?: (event: CalendarEvent) => void;
}

// ---------------------------------------------------------------------------
// Component — Side-by-side columns, one per member
// ---------------------------------------------------------------------------

export function MultiMemberView({
  date,
  events,
  members,
  onEventClick,
}: MultiMemberViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [nowTop, setNowTop] = useState(topPx(new Date().toISOString()));
  const isToday = toDateKey(new Date()) === date;

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: WORK_START_HOUR * SLOT_HEIGHT_PX - 20,
      behavior: "smooth",
    });
  }, [date]);

  useEffect(() => {
    const id = setInterval(() => setNowTop(topPx(new Date().toISOString())), 60_000);
    return () => clearInterval(id);
  }, []);

  // Background events visible across all columns
  const backgroundEvents = useMemo(
    () =>
      events.filter(
        (e) =>
          !e.allDay &&
          toDateKey(isoToDate(e.startAt)) === date &&
          (e.eventType === "background" || e.isSubscribed)
      ),
    [events, date]
  );

  // Events per member
  const eventsByMember = useMemo(() => {
    const map = new Map<string, CalendarEvent[]>();
    for (const m of members) {
      map.set(m.id, []);
    }
    for (const e of events) {
      if (e.allDay) continue;
      if (toDateKey(isoToDate(e.startAt)) !== date) continue;
      if (e.eventType === "background" || e.isSubscribed) continue;

      if (e.members.length === 0) {
        // Unassigned → show in first member column
        if (members.length > 0) {
          map.get(members[0].id)?.push(e);
        }
      } else {
        for (const m of e.members) {
          map.get(m.id)?.push(e);
        }
      }
    }
    return map;
  }, [events, members, date]);

  if (members.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-ase-subtle">
        <Users className="w-5 h-5 mr-2 opacity-50" />
        <span className="text-sm">No members in this circle</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* ── Member column headers ──────────────────────────── */}
      <div className="flex flex-shrink-0 border-b border-ase-border bg-ase-bg/80 backdrop-blur-sm sticky top-0 z-30">
        <div className="w-14 flex-shrink-0" />
        {members.map((m) => (
          <div
            key={m.id}
            className="flex-1 min-w-0 border-l border-ase-border/30 py-2 px-2"
          >
            <div className="flex items-center gap-2 justify-center">
              <div
                className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 border-2"
                style={{
                  backgroundColor: m.avatarColor + "30",
                  color: m.avatarColor,
                  borderColor: m.avatarColor + "50",
                }}
              >
                {m.avatarEmoji || m.displayName[0]?.toUpperCase()}
              </div>
              <span className="text-xs font-medium text-ase-text truncate hidden sm:block">
                {m.displayName}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* ── Scrollable grid ────────────────────────────────── */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto scroll-smooth">
        <div
          className="flex relative"
          style={{ height: `${HOURS.length * SLOT_HEIGHT_PX}px` }}
        >
          {/* Time gutter */}
          <div className="relative w-14 flex-shrink-0 border-r border-ase-border/20">
            {HOURS.map((h) => (
              <div
                key={h}
                className="absolute flex items-start justify-end pr-2"
                style={{ top: `${h * SLOT_HEIGHT_PX}px`, height: `${SLOT_HEIGHT_PX}px` }}
              >
                <span className="text-[10px] text-ase-subtle select-none -mt-2 tabular-nums">
                  {formatHour(h)}
                </span>
              </div>
            ))}
          </div>

          {/* Member columns */}
          {members.map((member) => {
            const memberEvents = eventsByMember.get(member.id) || [];

            return (
              <div
                key={member.id}
                className="relative flex-1 min-w-0 border-l border-ase-border/20"
              >
                {/* Hour lines */}
                {HOURS.map((h) => (
                  <div
                    key={h}
                    className="absolute inset-x-0 border-t border-ase-border/20"
                    style={{ top: `${h * SLOT_HEIGHT_PX}px` }}
                  >
                    <div
                      className="absolute inset-x-0 border-t border-dashed border-ase-border/8"
                      style={{ top: `${SLOT_HEIGHT_PX / 2}px` }}
                    />
                  </div>
                ))}

                {/* Background events (shared across all columns) */}
                {backgroundEvents.map((event) => (
                  <div
                    key={`bg-${event.id}`}
                    className="absolute inset-x-0 z-[3]"
                    style={{
                      top: `${topPx(event.startAt)}px`,
                      height: `${heightPx(event.startAt, event.endAt)}px`,
                    }}
                  >
                    <div className="h-full mx-0.5 rounded-sm bg-zinc-500/6 border border-zinc-600/8">
                      <span className="text-[9px] text-zinc-600 px-1.5 py-0.5 truncate block">
                        {event.title}
                      </span>
                    </div>
                  </div>
                ))}

                {/* Member events */}
                {memberEvents.map((event) => (
                  <div
                    key={event.id}
                    className="absolute inset-x-0.5 z-10"
                    style={{
                      top: `${topPx(event.startAt)}px`,
                      height: `${heightPx(event.startAt, event.endAt)}px`,
                      minHeight: `${MIN_EVENT_PX}px`,
                    }}
                  >
                    <div
                      className="h-full rounded-md border cursor-pointer transition-all duration-150 hover:brightness-110 hover:shadow-card active:scale-[0.98] overflow-hidden"
                      style={{
                        backgroundColor: member.avatarColor + "18",
                        borderColor: member.avatarColor + "30",
                      }}
                      onClick={() => onEventClick?.(event)}
                    >
                      <div
                        className="w-[3px] h-full absolute left-0 top-0 rounded-l-md"
                        style={{ backgroundColor: member.avatarColor }}
                      />
                      <div className="pl-2.5 pr-1 py-0.5 h-full flex flex-col">
                        <span
                          className="text-[10px] font-semibold truncate leading-tight"
                          style={{ color: member.avatarColor }}
                        >
                          {event.title}
                        </span>
                        {heightPx(event.startAt, event.endAt) > 26 && (
                          <span
                            className="text-[9px] opacity-50"
                            style={{ color: member.avatarColor }}
                          >
                            {new Date(event.startAt).toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}

                {/* Now indicator */}
                {isToday && (
                  <div
                    className="absolute inset-x-0 z-20 pointer-events-none"
                    style={{ top: `${nowTop}px` }}
                  >
                    <div className="border-t-2 border-red-400/60" />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
