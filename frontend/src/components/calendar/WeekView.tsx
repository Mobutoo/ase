import type { CalendarEvent } from "../../types/calendar";
import { EventCard } from "./EventCard";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const HOURS = Array.from({ length: 24 }, (_, i) => i);
const SLOT_HEIGHT_PX = 56;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function isoToDate(iso: string): Date {
  return new Date(iso);
}

function toDateKey(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function getWeekDays(anchorDate: string): Date[] {
  const anchor = new Date(anchorDate + "T12:00:00");
  const dow = anchor.getDay(); // 0=Sun
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
  const diff = (isoToDate(endIso).getTime() - isoToDate(startIso).getTime()) / 3_600_000;
  return Math.max(diff * SLOT_HEIGHT_PX, 18);
}

function formatHour(h: number): string {
  const p = h < 12 ? "AM" : "PM";
  const d = h === 0 ? 12 : h > 12 ? h - 12 : h;
  return `${d}${p}`;
}

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface WeekViewProps {
  anchorDate: string; // any YYYY-MM-DD in the target week
  events: CalendarEvent[];
  onEventClick?: (event: CalendarEvent) => void;
  onDayClick?: (date: string) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function WeekView({ anchorDate, events, onEventClick, onDayClick }: WeekViewProps) {
  const days = getWeekDays(anchorDate);
  const todayKey = toDateKey(new Date());
  const nowTop = topPx(new Date().toISOString());

  const allDayByDay = (dayKey: string) =>
    events.filter((e) => e.allDay && toDateKey(isoToDate(e.startAt)) === dayKey);

  const timedByDay = (dayKey: string) =>
    events.filter((e) => !e.allDay && toDateKey(isoToDate(e.startAt)) === dayKey);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Column headers */}
      <div className="flex flex-shrink-0 border-b border-ase-border">
        {/* Gutter */}
        <div className="w-12 flex-shrink-0" />
        {days.map((day, i) => {
          const key = toDateKey(day);
          const isToday = key === todayKey;
          const dayAllDay = allDayByDay(key);
          return (
            <div
              key={key}
              className="flex-1 min-w-0 border-l border-ase-border/40 px-1 py-1.5"
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
                    "w-7 h-7 flex items-center justify-center rounded-full text-sm font-semibold transition-colors",
                    isToday
                      ? "bg-ase-gold text-black"
                      : "text-ase-text group-hover:bg-ase-surface-2",
                  ].join(" ")}
                >
                  {day.getDate()}
                </span>
              </button>
              {/* All-day events */}
              {dayAllDay.length > 0 && (
                <div className="mt-1 flex flex-col gap-0.5">
                  {dayAllDay.map((e) => (
                    <EventCard key={e.id} event={e} compact onClick={onEventClick} />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Scrollable time grid */}
      <div className="flex-1 overflow-y-auto">
        <div className="flex" style={{ height: `${HOURS.length * SLOT_HEIGHT_PX}px` }}>
          {/* Time gutter */}
          <div className="relative w-12 flex-shrink-0">
            {HOURS.map((h) => (
              <div
                key={h}
                className="absolute flex items-start justify-end pr-1"
                style={{ top: `${h * SLOT_HEIGHT_PX}px`, height: `${SLOT_HEIGHT_PX}px` }}
              >
                <span className="text-[10px] text-ase-subtle select-none -mt-2">
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

            return (
              <div
                key={key}
                className="relative flex-1 min-w-0 border-l border-ase-border/40"
              >
                {/* Hour lines */}
                {HOURS.map((h) => (
                  <div
                    key={h}
                    className="absolute inset-x-0 border-t border-ase-border/30"
                    style={{ top: `${h * SLOT_HEIGHT_PX}px` }}
                  />
                ))}

                {/* Now indicator */}
                {isToday && (
                  <div
                    className="absolute inset-x-0 z-20 pointer-events-none"
                    style={{ top: `${nowTop}px` }}
                  >
                    <div className="border-t-2 border-red-400/80 relative">
                      <div className="absolute -left-1 -top-[5px] w-2.5 h-2.5 rounded-full bg-red-400" />
                    </div>
                  </div>
                )}

                {/* Events */}
                {timedEvents.map((event) => (
                  <div
                    key={event.id}
                    className="absolute inset-x-0.5 z-10"
                    style={{
                      top: `${topPx(event.startAt)}px`,
                      height: `${heightPx(event.startAt, event.endAt)}px`,
                      minHeight: "18px",
                    }}
                  >
                    <EventCard event={event} onClick={onEventClick} />
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
