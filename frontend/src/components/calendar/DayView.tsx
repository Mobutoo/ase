import { useEffect, useRef, useState, useMemo } from "react";
import type { CalendarEvent } from "../../types/calendar";
import { EventCard } from "./EventCard";
import { SubscriptionBadge } from "./SubscriptionBadge";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const HOURS = Array.from({ length: 24 }, (_, i) => i);
const SLOT_HEIGHT_PX = 60; // px per hour = 1px per minute
const WORK_START_HOUR = 7;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function isoToDate(iso: string): Date {
  return new Date(iso);
}

function sameDay(date: Date, dateStr: string): boolean {
  const d = new Date(dateStr + "T00:00:00");
  return (
    date.getFullYear() === d.getFullYear() &&
    date.getMonth() === d.getMonth() &&
    date.getDate() === d.getDate()
  );
}

function topPx(iso: string): number {
  const d = isoToDate(iso);
  return (d.getHours() + d.getMinutes() / 60) * SLOT_HEIGHT_PX;
}

function heightPx(startIso: string, endIso: string): number {
  const start = isoToDate(startIso);
  const end = isoToDate(endIso);
  const diffH = (end.getTime() - start.getTime()) / 3_600_000;
  return Math.max(diffH * SLOT_HEIGHT_PX, 20);
}

function formatHour(h: number): string {
  const period = h < 12 ? "AM" : "PM";
  const display = h === 0 ? 12 : h > 12 ? h - 12 : h;
  return `${display} ${period}`;
}

// ---------------------------------------------------------------------------
// 3-layer classification (mirrors WeekView)
// ---------------------------------------------------------------------------

type EventLayer = "background" | "shared" | "personal";

function classifyLayer(event: CalendarEvent): EventLayer {
  if (event.eventType === "background" || event.isSubscribed) return "background";
  if (event.members.length >= 2) return "shared";
  return "personal";
}

/** Resolve overlapping events into non-overlapping column positions. */
function layoutColumns(
  events: CalendarEvent[],
): { event: CalendarEvent; col: number; totalCols: number }[] {
  if (events.length === 0) return [];
  const sorted = [...events].sort(
    (a, b) => isoToDate(a.startAt).getTime() - isoToDate(b.startAt).getTime(),
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

interface DayViewProps {
  date: string; // YYYY-MM-DD
  events: CalendarEvent[];
  onEventClick?: (event: CalendarEvent) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function DayView({ date, events, onEventClick }: DayViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [nowTop, setNowTop] = useState(topPx(new Date().toISOString()));
  const isToday = sameDay(new Date(), date);

  // Auto-scroll to working hours
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: WORK_START_HOUR * SLOT_HEIGHT_PX - 20,
      behavior: "smooth",
    });
  }, [date]);

  // Live now-indicator
  useEffect(() => {
    const id = setInterval(() => setNowTop(topPx(new Date().toISOString())), 60_000);
    return () => clearInterval(id);
  }, []);

  const dayEvents = useMemo(
    () => events.filter((e) => !e.allDay && sameDay(isoToDate(e.startAt), date)),
    [events, date],
  );

  const allDayEvents = useMemo(
    () => events.filter((e) => e.allDay && sameDay(isoToDate(e.startAt), date)),
    [events, date],
  );

  // Classify into 3 layers
  const bgEvents = useMemo(
    () => dayEvents.filter((e) => classifyLayer(e) === "background"),
    [dayEvents],
  );
  const sharedEvents = useMemo(
    () => dayEvents.filter((e) => classifyLayer(e) === "shared"),
    [dayEvents],
  );
  const personalEvents = useMemo(
    () => dayEvents.filter((e) => classifyLayer(e) === "personal"),
    [dayEvents],
  );

  const sharedLayout = useMemo(() => layoutColumns(sharedEvents), [sharedEvents]);
  const personalLayout = useMemo(() => layoutColumns(personalEvents), [personalEvents]);

  const dateLabel = new Date(date + "T12:00:00").toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 px-4 py-3 border-b border-ase-border">
        <h2 className="text-sm font-semibold text-white">{dateLabel}</h2>
        {/* All-day strip */}
        {allDayEvents.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {allDayEvents.map((e) => (
              <div key={e.id} className="relative">
                <EventCard event={e} compact onClick={onEventClick} />
                {e.isSubscribed && <SubscriptionBadge />}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Time grid */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="relative" style={{ height: `${HOURS.length * SLOT_HEIGHT_PX}px` }}>
          {/* Hour lines */}
          {HOURS.map((h) => (
            <div
              key={h}
              className="absolute inset-x-0 flex items-start"
              style={{ top: `${h * SLOT_HEIGHT_PX}px`, height: `${SLOT_HEIGHT_PX}px` }}
            >
              <span className="w-14 flex-shrink-0 pr-2 text-right text-[11px] text-ase-subtle select-none -mt-2">
                {formatHour(h)}
              </span>
              <div className="flex-1 border-t border-ase-border/40" />
            </div>
          ))}

          {/* Current time indicator */}
          {isToday && (
            <div
              className="absolute inset-x-0 z-20 flex items-center pointer-events-none"
              style={{ top: `${nowTop}px`, paddingLeft: "56px" }}
            >
              <div className="w-2 h-2 rounded-full bg-red-400 -ml-1 flex-shrink-0" />
              <div className="flex-1 border-t-2 border-red-400/80" />
            </div>
          )}

          {/* ── Layer 1: Background events (full width, semi-transparent) ── */}
          <div className="absolute inset-0 pl-14 pr-2">
            {bgEvents.map((event) => (
              <div
                key={event.id}
                className="absolute left-14 right-2 z-[5] rounded-lg border border-zinc-700/40 bg-zinc-800/30 px-2 py-1 overflow-hidden cursor-pointer hover:bg-zinc-700/40 transition-colors"
                style={{
                  top: `${topPx(event.startAt)}px`,
                  height: `${heightPx(event.startAt, event.endAt)}px`,
                }}
                onClick={() => onEventClick?.(event)}
              >
                <div className="flex items-center gap-1.5">
                  <SubscriptionBadge />
                  <span className="text-[11px] text-zinc-400 truncate">{event.title}</span>
                </div>
                <span className="text-[10px] text-zinc-500">
                  {isoToDate(event.startAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  {" – "}
                  {isoToDate(event.endAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
              </div>
            ))}
          </div>

          {/* ── Layer 2: Shared events (member accent, columns) ── */}
          <div className="absolute inset-0 pl-14 pr-2">
            {sharedLayout.map(({ event, col, totalCols }) => {
              const memberColor = event.members[0]?.avatarColor ?? "#f59e0b";
              const w = `calc(${100 / totalCols}% - 4px)`;
              const l = `calc(${(col * 100) / totalCols}%)`;
              return (
                <div
                  key={event.id}
                  className="absolute z-[15] rounded-lg overflow-hidden cursor-pointer hover:brightness-110 transition-all"
                  style={{
                    top: `${topPx(event.startAt)}px`,
                    height: `${heightPx(event.startAt, event.endAt)}px`,
                    width: w,
                    left: l,
                    backgroundColor: `${memberColor}18`,
                    borderLeft: `3px solid ${memberColor}`,
                  }}
                  onClick={() => onEventClick?.(event)}
                >
                  <div className="px-2 py-1">
                    <p className="text-xs font-medium text-white truncate">{event.title}</p>
                    <p className="text-[10px] text-ase-subtle">
                      {isoToDate(event.startAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      {" – "}
                      {isoToDate(event.endAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </p>
                    {/* Member avatars */}
                    <div className="flex -space-x-1 mt-0.5">
                      {event.members.slice(0, 4).map((m) => (
                        <span
                          key={m.id}
                          className="w-4 h-4 rounded-full flex items-center justify-center text-[8px] font-bold border border-black/40"
                          style={{ backgroundColor: m.avatarColor ?? "#888" }}
                          title={m.displayName}
                        >
                          {m.avatarEmoji || m.displayName?.[0]?.toUpperCase()}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* ── Layer 3: Personal events (calendar color, columns) ── */}
          <div className="absolute inset-0 pl-14 pr-2">
            {personalLayout.map(({ event, col, totalCols }) => {
              const w = `calc(${100 / totalCols}% - 4px)`;
              const l = `calc(${(col * 100) / totalCols}%)`;
              return (
                <div
                  key={event.id}
                  className="absolute z-10"
                  style={{
                    top: `${topPx(event.startAt)}px`,
                    height: `${heightPx(event.startAt, event.endAt)}px`,
                    width: w,
                    left: l,
                    minHeight: "20px",
                  }}
                >
                  <EventCard event={event} onClick={onEventClick} />
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
