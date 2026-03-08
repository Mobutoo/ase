import React, { useMemo } from "react";
import type { StreakInfo } from "../../types/phase4";

interface Props {
  streak: StreakInfo;
  month?: Date; // defaults to current month
}

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export const StreakCalendar: React.FC<Props> = ({ streak, month }) => {
  const target = month ?? new Date();

  const { year, monthIdx, daysInMonth, firstDow } = useMemo(() => {
    const y = target.getFullYear();
    const m = target.getMonth();
    const dim = new Date(y, m + 1, 0).getDate();
    const fdow = new Date(y, m, 1).getDay();
    return { year: y, monthIdx: m, daysInMonth: dim, firstDow: fdow };
  }, [target]);

  const activeSet = useMemo(
    () => new Set(streak.activeDates),
    [streak.activeDates]
  );
  const frozenSet = useMemo(
    () => new Set(streak.frozenDates),
    [streak.frozenDates]
  );

  const monthName = target.toLocaleString("en-US", { month: "long" });

  // Build calendar grid: 7 columns
  const cells: Array<{ day: number | null; iso: string | null }> = [];
  for (let i = 0; i < firstDow; i++) cells.push({ day: null, iso: null });
  for (let d = 1; d <= daysInMonth; d++) {
    const iso = `${year}-${String(monthIdx + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    cells.push({ day: d, iso });
  }
  // Pad to full weeks
  while (cells.length % 7 !== 0) cells.push({ day: null, iso: null });

  const today = new Date().toISOString().slice(0, 10);

  function getCellStyle(iso: string | null): {
    bg: string;
    border: string;
    emoji?: string;
  } {
    if (!iso) return { bg: "transparent", border: "transparent" };
    if (iso === today) return { bg: "#1f2937", border: "#f59e0b", emoji: undefined };
    if (activeSet.has(iso)) return { bg: "#92400e", border: "#f59e0b", emoji: "🔥" };
    if (frozenSet.has(iso)) return { bg: "#1e3a5f", border: "#3b82f6", emoji: "🧊" };
    return { bg: "#1a1a2e", border: "#2a2a3e" };
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-gray-200">
          {monthName} {year}
        </span>
        <div className="flex gap-3 text-xs text-gray-400">
          <span>
            <span className="text-[#f59e0b] font-bold">{streak.currentStreak}</span> day streak
          </span>
          <span>
            <span className="text-blue-400 font-bold">{streak.freezesRemaining}</span> freezes left
          </span>
        </div>
      </div>

      {/* Day headers */}
      <div className="grid grid-cols-7 gap-1">
        {WEEKDAYS.map((wd) => (
          <div key={wd} className="text-center text-[10px] text-gray-500 font-medium py-0.5">
            {wd[0]}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div className="grid grid-cols-7 gap-1">
        {cells.map((cell, idx) => {
          const style = getCellStyle(cell.iso);
          const isToday = cell.iso === today;
          return (
            <div
              key={idx}
              className="relative flex items-center justify-center rounded-full aspect-square text-xs font-medium transition-all duration-150"
              style={{
                background: style.bg,
                border: `1.5px solid ${style.border}`,
                opacity: cell.day ? 1 : 0,
              }}
            >
              {cell.day && (
                <>
                  {style.emoji ? (
                    <span className="text-sm leading-none">{style.emoji}</span>
                  ) : (
                    <span className={isToday ? "text-[#f59e0b] font-bold" : "text-gray-400"}>
                      {cell.day}
                    </span>
                  )}
                </>
              )}
            </div>
          );
        })}
      </div>

      {/* Stats row */}
      <div className="flex justify-between text-xs text-gray-500 border-t border-[#2a2a3e] pt-2 mt-1">
        <span>Best streak: <span className="text-gray-300">{streak.longestStreak}d</span></span>
        <span>Freezes used: <span className="text-gray-300">{streak.freezesUsedTotal}</span></span>
        <span>Active days: <span className="text-gray-300">{activeSet.size}</span></span>
      </div>
    </div>
  );
};
