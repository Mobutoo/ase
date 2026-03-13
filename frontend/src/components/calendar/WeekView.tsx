import { useMemo, useRef, useEffect, useCallback, useState } from "react";
import type { CalendarEvent } from "../../types/calendar";
import { EventCard } from "./EventCard";

// ---------------------------------------------------------------------------
// Constants — 5-minute granularity
// ---------------------------------------------------------------------------

const HOURS = Array.from({ length: 24 }, (_, i) => i);
const SLOT_HEIGHT_PX = 60; // 60px per hour = 1px per minute
const MIN_EVENT_PX = 14;
const WORK_START_HOUR = 7;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function isoToDate(iso: string): Date {
  return new Date(iso);
}

function toDateKey(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function getWeekDays(anchorDate: string): Date[] {
  const anchor = new Date(anchorDate + "T12:00:00");
  const dow = anchor.getDay();
  const monday = new Date(anchor);
  monday.setDate(anchor.getDate() - ((dow + 6) % 7));
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    return d;
  });
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

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

/**
 * 3-layer classification:
 * - background: subscription/booking events (semi-transparent, full width)
 * - shared: events with 2+ members (member accent color)
 * - personal: single-member or no-member events (calendar color)
 */
type EventLayer = "background" | "shared" | "personal";

function classifyLayer(event: CalendarEvent): EventLayer {
  if (event.eventType === "background" || event.isSubscribed) return "background";
  if (event.members.length >= 2) return "shared";
  return "personal";
}

/** Resolve overlapping events into non-overlapping column positions. */
function layoutColumns(
  events: CalendarEvent[]
): { event: CalendarEvent; col: number; totalCols: number }[] {
  if (events.length === 0) return [];
  const sorted = [...events].sort(
    (a, b) => isoToDate(a.startAt).getTime() - isoToDate(b.startAt).getTime()
  );

  const columns: CalendarEvent[][] = [];
  const placed = new Map<string, number>();

  for (const event of sorted) {
    const start = isoToDate(event.startAt).getTime();
    let col = 0;
    while (col < columns.length) {
      const lastInCol = columns[col][columns[col].length - 1];
      if (isoToDate(lastInCol.endAt).getTime() <= start) break;
      col++;
    }
    if (col === columns.length) columns.push([]);
    columns[col].push(event);
    placed.set(event.id, col);
  }

  const totalCols = columns.length;
  return sorted.map((event) => ({
    event,
    col: placed.get(event.id)!,
    totalCols,
  }));
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface WeekViewProps {
  anchorDate: string;
  events: CalendarEvent[];
  onEventClick?: (event: CalendarEvent) => void;
  onDayClick?: (date: string) => void;
  onSlotClick?: (date: string, hour: number, minute: number) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function WeekView({
  anchorDate,
  events,
  onEventClick,
  onDayClick,
  onSlotClick,
}: WeekViewProps) {
  const days = useMemo(() => getWeekDays(anchorDate), [anchorDate]);
  const todayKey = toDateKey(new Date());
  const scrollRef = useRef<HTMLDivElement>(null);
  const [nowTop, setNowTop] = useState(topPx(new Date().toISOString()));

  // Auto-scroll to working hours on mount / date change
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: WORK_START_HOUR * SLOT_HEIGHT_PX - 20,
      behavior: "smooth",
    });
  }, [anchorDate]);

  // Live now-indicator
  useEffect(() => {
    const id = setInterval(() => setNowTop(topPx(new Date().toISOString())), 60_000);
    return () => clearInterval(id);
  }, []);

  const allDayByDay = useCallback(
    (dayKey: string) =>
      events.filter((e) => e.allDay && toDateKey(isoToDate(e.startAt)) === dayKey),
    [events]
  );

  const timedByDay = useCallback(
    (dayKey: string) =>
      events.filter((e) => !e.allDay && toDateKey(isoToDate(e.startAt)) === dayKey),
    [events]
  );

  const handleSlotClick = useCallback(
    (dayKey: string, h: number, e: React.MouseEvent<HTMLDivElement>) => {
      if (!onSlotClick) return;
      const rect = e.currentTarget.getBoundingClientRect();
      const relY = e.clientY - rect.top;
      const minute = Math.round((relY / SLOT_HEIGHT_PX) * 60 / 5) * 5;
      onSlotClick(dayKey, h, Math.min(minute, 55));
    },
    [onSlotClick]
  );

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* ── Column headers ─────────────────────────────────── */}
      <div className="flex flex-shrink-0 border-b border-ase-border bg-ase-bg/80 backdrop-blur-sm sticky top-0 z-30">
        <div className="w-14 flex-shrink-0" />
        {days.map((day, i) => {
          const key = toDateKey(day);
          const isToday = key === todayKey;
          const dayAllDay = allDayByDay(key);
          return (
            <div
              key={key}
              className="flex-1 min-w-0 border-l border-ase-border/30 px-1 py-2"
            >
              <button
                type="button"
                onClick={() => onDayClick?.(key)}
                className="w-full flex flex-col items-center gap-0.5 group"
              >
                <span className="text-[10px] font-medium text-ase-subtle uppercase tracking-wider">
                  {DAY_LABELS[i]}
                </span>
                <span
                  className={[
                    "w-8 h-8 flex items-center justify-center rounded-full text-sm font-semibold transition-all duration-200",
                    isToday
                      ? "bg-ase-gold text-black shadow-glow"
                      : "text-ase-text group-hover:bg-ase-surface-2",
                  ].join(" ")}
                >
                  {day.getDate()}
                </span>
              </button>
              {dayAllDay.length > 0 && (
                <div className="mt-1.5 flex flex-col gap-0.5 px-0.5">
                  {dayAllDay.slice(0, 2).map((e) => (
                    <EventCard key={e.id} event={e} compact onClick={onEventClick} />
                  ))}
                  {dayAllDay.length > 2 && (
                    <span className="text-[9px] text-ase-subtle px-1">
                      +{dayAllDay.length - 2}
                    </span>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* ── Scrollable time grid ───────────────────────────── */}
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
                style={{
                  top: `${h * SLOT_HEIGHT_PX}px`,
                  height: `${SLOT_HEIGHT_PX}px`,
                }}
              >
                <span className="text-[10px] text-ase-subtle select-none -mt-2 tabular-nums">
                  {formatHour(h)}
                </span>
              </div>
            ))}
          </div>

          {/* Day columns */}
          {days.map((day) => {
            const key = toDateKey(day);
            const isToday = key === todayKey;
            const timedEvents = timedByDay(key);

            // Separate into 3 layers
            const bgEvents = timedEvents.filter((e) => classifyLayer(e) === "background");
            const sharedEvents = timedEvents.filter((e) => classifyLayer(e) === "shared");
            const personalEvents = timedEvents.filter((e) => classifyLayer(e) === "personal");

            const sharedLayout = layoutColumns(sharedEvents);
            const personalLayout = layoutColumns(personalEvents);

            return (
              <div
                key={key}
                className={[
                  "relative flex-1 min-w-0 border-l border-ase-border/20",
                  isToday ? "bg-ase-gold/[0.02]" : "",
                ].join(" ")}
              >
                {/* Hour grid + half-hour dashes */}
                {HOURS.map((h) => (
                  <div
                    key={h}
                    className="absolute inset-x-0 border-t border-ase-border/20 cursor-pointer"
                    style={{ top: `${h * SLOT_HEIGHT_PX}px`, height: `${SLOT_HEIGHT_PX}px` }}
                    onClick={(e) => handleSlotClick(key, h, e)}
                  >
                    <div
                      className="absolute inset-x-0 border-t border-dashed border-ase-border/10"
                      style={{ top: `${SLOT_HEIGHT_PX / 2}px` }}
                    />
                  </div>
                ))}

                {/* Layer 1 — Background (full-width, semi-transparent) */}
                {bgEvents.map((event) => (
                  <div
                    key={event.id}
                    className="absolute inset-x-0 z-[5]"
                    style={{
                      top: `${topPx(event.startAt)}px`,
                      height: `${heightPx(event.startAt, event.endAt)}px`,
                    }}
                  >
                    <div className="h-full mx-0.5 rounded-md bg-zinc-500/8 border border-zinc-600/12 backdrop-blur-[1px]">
                      <div className="px-2 py-0.5 flex items-center gap-1.5 h-full">
                        <div className="w-1 h-1 rounded-full bg-zinc-500/60 flex-shrink-0" />
                        <span className="text-[10px] text-zinc-500 truncate">
                          {event.title}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}

                {/* Layer 2 — Shared events (member color, left accent) */}
                {sharedLayout.map(({ event, col, totalCols }) => {
                  const w = `calc((100% - 4px) / ${totalCols})`;
                  const l = `calc(2px + (100% - 4px) * ${col} / ${totalCols})`;
                  const color = event.members[0]?.avatarColor || "#f59e0b";

                  return (
                    <div
                      key={event.id}
                      className="absolute z-[15]"
                      style={{
                        top: `${topPx(event.startAt)}px`,
                        height: `${heightPx(event.startAt, event.endAt)}px`,
                        left: l,
                        width: w,
                        minHeight: `${MIN_EVENT_PX}px`,
                      }}
                    >
                      <div
                        className="h-full rounded-md border cursor-pointer transition-all duration-150 hover:brightness-110 hover:shadow-card active:scale-[0.98] overflow-hidden"
                        style={{
                          backgroundColor: color + "18",
                          borderColor: color + "35",
                        }}
                        onClick={() => onEventClick?.(event)}
                      >
                        <div
                          className="w-[3px] h-full absolute left-0 top-0 rounded-l-md"
                          style={{ backgroundColor: color }}
                        />
                        <div className="pl-2.5 pr-1 py-1 h-full flex flex-col min-h-0">
                          <span
                            className="text-[11px] font-semibold leading-tight truncate"
                            style={{ color }}
                          >
                            {event.title}
                          </span>
                          {heightPx(event.startAt, event.endAt) > 28 && (
                            <span
                              className="text-[9px] opacity-60 mt-0.5"
                              style={{ color }}
                            >
                              {new Date(event.startAt).toLocaleTimeString([], {
                                hour: "2-digit",
                                minute: "2-digit",
                              })}
                            </span>
                          )}
                          {heightPx(event.startAt, event.endAt) > 44 &&
                            event.members.length > 0 && (
                              <div className="flex -space-x-1 mt-auto pt-0.5">
                                {event.members.slice(0, 3).map((m) => (
                                  <div
                                    key={m.id}
                                    className="w-4 h-4 rounded-full border border-black/20 flex items-center justify-center text-[7px] font-bold"
                                    style={{
                                      backgroundColor: m.avatarColor + "50",
                                      color: m.avatarColor,
                                    }}
                                    title={m.displayName}
                                  >
                                    {m.avatarEmoji || m.displayName[0]?.toUpperCase()}
                                  </div>
                                ))}
                              </div>
                            )}
                        </div>
                      </div>
                    </div>
                  );
                })}

                {/* Layer 3 — Personal events */}
                {personalLayout.map(({ event, col, totalCols }) => {
                  const w = `calc((100% - 4px) / ${totalCols})`;
                  const l = `calc(2px + (100% - 4px) * ${col} / ${totalCols})`;

                  return (
                    <div
                      key={event.id}
                      className="absolute z-10"
                      style={{
                        top: `${topPx(event.startAt)}px`,
                        height: `${heightPx(event.startAt, event.endAt)}px`,
                        left: l,
                        width: w,
                        minHeight: `${MIN_EVENT_PX}px`,
                      }}
                    >
                      <EventCard event={event} onClick={onEventClick} />
                    </div>
                  );
                })}

                {/* Now indicator */}
                {isToday && (
                  <div
                    className="absolute inset-x-0 z-[25] pointer-events-none"
                    style={{ top: `${nowTop}px` }}
                  >
                    <div className="relative">
                      <div className="absolute -left-[5px] -top-[4px] w-[10px] h-[10px] rounded-full bg-red-400 shadow-sm shadow-red-400/50" />
                      <div className="border-t-2 border-red-400/80" />
                    </div>
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
