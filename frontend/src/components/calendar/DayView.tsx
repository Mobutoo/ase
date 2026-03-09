import type { CalendarEvent } from "../../types/calendar";
import { EventCard } from "./EventCard";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const HOURS = Array.from({ length: 24 }, (_, i) => i);
const SLOT_HEIGHT_PX = 60; // px per hour

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

function topOffsetPercent(iso: string): number {
  const d = isoToDate(iso);
  return (d.getHours() + d.getMinutes() / 60) * SLOT_HEIGHT_PX;
}

function heightPercent(startIso: string, endIso: string): number {
  const start = isoToDate(startIso);
  const end = isoToDate(endIso);
  const diffH = (end.getTime() - start.getTime()) / 3_600_000;
  return Math.max(diffH * SLOT_HEIGHT_PX, 20); // minimum 20px
}

function formatHour(h: number): string {
  const period = h < 12 ? "AM" : "PM";
  const display = h === 0 ? 12 : h > 12 ? h - 12 : h;
  return `${display} ${period}`;
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
  const dayEvents = events.filter(
    (e) => !e.allDay && sameDay(isoToDate(e.startAt), date)
  );
  const allDayEvents = events.filter(
    (e) => e.allDay && sameDay(isoToDate(e.startAt), date)
  );

  const dateLabel = new Date(date + "T12:00:00").toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  const nowTop = topOffsetPercent(new Date().toISOString());
  const isToday = sameDay(new Date(), date);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 px-4 py-3 border-b border-ase-border">
        <h2 className="text-sm font-semibold text-white">{dateLabel}</h2>
        {/* All-day strip */}
        {allDayEvents.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {allDayEvents.map((e) => (
              <EventCard key={e.id} event={e} compact onClick={onEventClick} />
            ))}
          </div>
        )}
      </div>

      {/* Time grid */}
      <div className="flex-1 overflow-y-auto">
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

          {/* Events */}
          <div className="absolute inset-0 pl-14 pr-2">
            {dayEvents.map((event) => (
              <div
                key={event.id}
                className="absolute left-14 right-2 z-10"
                style={{
                  top: `${topOffsetPercent(event.startAt)}px`,
                  height: `${heightPercent(event.startAt, event.endAt)}px`,
                  minHeight: "20px",
                }}
              >
                <EventCard event={event} onClick={onEventClick} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
