import React, { useMemo } from "react";
import type { DensityEntry } from "../../types/phase4";

const LEVEL_COLORS = [
  "transparent",     // 0 sessions
  "#78350f",         // 1
  "#b45309",         // 2-3
  "#d97706",         // 4-5
  "#f59e0b",         // 6+
];

function getLevel(count: number): number {
  if (count === 0) return 0;
  if (count === 1) return 1;
  if (count <= 3) return 2;
  if (count <= 5) return 3;
  return 4;
}

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

interface Props {
  data: DensityEntry[];
  weeks?: number;
}

export const DensityChart: React.FC<Props> = ({ data, weeks = 52 }) => {
  const grid = useMemo(() => {
    const byDate = new Map<string, DensityEntry>();
    data.forEach((e) => byDate.set(e.date, e));

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    // Start from (weeks*7) days ago, aligned to Sunday
    const totalDays = weeks * 7;
    const startDate = new Date(today);
    startDate.setDate(today.getDate() - totalDays + 1);
    // Align to nearest Sunday before
    const dayOfWeek = startDate.getDay();
    startDate.setDate(startDate.getDate() - dayOfWeek);

    const cols: Array<Array<{ date: string; count: number; minutes: number }>> = [];
    let cur = new Date(startDate);

    while (cur <= today) {
      const col: Array<{ date: string; count: number; minutes: number }> = [];
      for (let d = 0; d < 7; d++) {
        const iso = cur.toISOString().slice(0, 10);
        const entry = byDate.get(iso);
        col.push({ date: iso, count: entry?.count ?? 0, minutes: entry?.minutes ?? 0 });
        cur.setDate(cur.getDate() + 1);
      }
      cols.push(col);
    }

    return cols;
  }, [data, weeks]);

  const monthLabels = useMemo(() => {
    const labels: Array<{ month: string; colIndex: number }> = [];
    let lastMonth = -1;
    grid.forEach((col, i) => {
      const date = new Date(col[0].date + "T00:00:00");
      const m = date.getMonth();
      if (m !== lastMonth) {
        labels.push({ month: MONTHS[m], colIndex: i });
        lastMonth = m;
      }
    });
    return labels;
  }, [grid]);

  const cellSize = 13;
  const gap = 2;
  const step = cellSize + gap;
  const labelH = 18;
  const labelW = 28;

  const svgW = labelW + grid.length * step;
  const svgH = labelH + 7 * step;

  return (
    <div className="w-full overflow-x-auto">
      <svg
        width={svgW}
        height={svgH}
        viewBox={`0 0 ${svgW} ${svgH}`}
        aria-label="Session density heatmap"
        style={{ minWidth: svgW }}
      >
        {/* Month labels */}
        {monthLabels.map(({ month, colIndex }) => (
          <text
            key={`${month}-${colIndex}`}
            x={labelW + colIndex * step}
            y={12}
            fill="#6b7280"
            fontSize={9}
          >
            {month}
          </text>
        ))}

        {/* Day labels */}
        {[1, 3, 5].map((d) => (
          <text
            key={d}
            x={labelW - 4}
            y={labelH + d * step + cellSize - 2}
            fill="#6b7280"
            fontSize={9}
            textAnchor="end"
          >
            {DAYS[d]}
          </text>
        ))}

        {/* Cells */}
        {grid.map((col, ci) =>
          col.map((cell, ri) => {
            const level = getLevel(cell.count);
            const color = LEVEL_COLORS[level];
            const x = labelW + ci * step;
            const y = labelH + ri * step;
            return (
              <rect
                key={cell.date}
                x={x}
                y={y}
                width={cellSize}
                height={cellSize}
                rx={2}
                fill={color}
                stroke="#2a2a3e"
                strokeWidth={0.5}
                className="transition-opacity duration-150 hover:opacity-70"
              >
                <title>
                  {cell.date}: {cell.count} session{cell.count !== 1 ? "s" : ""} ({Math.round(cell.minutes / 60 * 10) / 10}h)
                </title>
              </rect>
            );
          })
        )}
      </svg>

      {/* Legend */}
      <div className="flex items-center gap-1.5 mt-2 text-xs text-gray-500">
        <span>Less</span>
        {LEVEL_COLORS.map((color, i) => (
          <span
            key={i}
            className="inline-block w-3 h-3 rounded-sm border border-[#2a2a3e]"
            style={{ background: color === "transparent" ? "#1a1a2e" : color }}
          />
        ))}
        <span>More</span>
      </div>
    </div>
  );
};
