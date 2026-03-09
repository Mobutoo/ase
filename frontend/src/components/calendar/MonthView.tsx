import type { CalendarEvent } from "../../types/calendar";
import { EventCard } from "./EventCard";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function toDateKey(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function isoToDate(iso: string): Date {
  return new Date(iso);
}

/** Returns a 6-row grid of dates for the given month anchor. */
function getMonthGrid(anchorDate: string): Date[] {
  const anchor = new Date(anchorDate + "T12:00:00");
  const year = anchor.getFullYear();
  const month = anchor.getMonth();

  const firstDay = new Date(year, month, 1);
  // Shift so Monday is column 0
  const startOffset = (firstDay.getDay() + 6) % 7;
  const gridStart = new Date(firstDay);
  gridStart.setDate(1 - startOffset);

  return Array.from({ length: 42 }, (_, i) => {
    const d = new Date(gridStart);
    d.setDate(gridStart.getDate() + i);
    return d;
  });
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface MonthViewProps {
  anchorDate: string; // YYYY-MM-DD, any date in the target month
  events: CalendarEvent[];
  onEventClick?: (event: CalendarEvent) => void;
  onDayClick?: (date: string) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function MonthView({ anchorDate, events, onEventClick, onDayClick }: MonthViewProps) {
  const anchor = new Date(anchorDate + "T12:00:00");
  const currentMonth = anchor.getMonth();
  const grid = getMonthGrid(anchorDate);
  const todayKey = toDateKey(new Date());

  const eventsByDay = (dayKey: string) =>
    events.filter((e) => toDateKey(isoToDate(e.startAt)) === dayKey);

  return (
    <div className="flex flex-col h-full overflow-hidden select-none">
      {/* Weekday headers */}
      <div className="grid grid-cols-7 flex-shrink-0 border-b border-ase-border">
        {DAY_LABELS.map((label) => (
          <div
            key={label}
            className="py-2 text-center text-[10px] font-medium uppercase tracking-wider text-ase-subtle"
          >
            {label}
          </div>
        ))}
      </div>

      {/* 6-row grid */}
      <div className="grid grid-cols-7 grid-rows-6 flex-1 overflow-hidden">
        {grid.map((day) => {
          const key = toDateKey(day);
          const isCurrentMonth = day.getMonth() === currentMonth;
          const isToday = key === todayKey;
          const dayEvents = eventsByDay(key);

          return (
            <div
              key={key}
              className={[
                "border-b border-r border-ase-border/40 p-1 flex flex-col gap-0.5 overflow-hidden",
                "min-h-[80px] transition-colors duration-150",
                isCurrentMonth ? "" : "opacity-40",
                "hover:bg-ase-surface/50 cursor-pointer",
              ].join(" ")}
              onClick={() => onDayClick?.(key)}
            >
              {/* Day number */}
              <div className="flex-shrink-0 flex justify-end px-0.5">
                <span
                  className={[
                    "w-6 h-6 flex items-center justify-center rounded-full text-xs font-medium",
                    isToday
                      ? "bg-ase-gold text-black font-bold"
                      : "text-ase-muted",
                  ].join(" ")}
                >
                  {day.getDate()}
                </span>
              </div>

              {/* Events (up to 3, then +N) */}
              <div className="flex flex-col gap-0.5 overflow-hidden">
                {dayEvents.slice(0, 3).map((e) => (
                  <EventCard
                    key={e.id}
                    event={e}
                    compact
                    onClick={(ev) => {
                      ev; // prevent day click
                      onEventClick?.(e);
                    }}
                  />
                ))}
                {dayEvents.length > 3 && (
                  <span className="text-[10px] text-ase-subtle px-1">
                    +{dayEvents.length - 3} more
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
