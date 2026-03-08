import React from "react";
import type { DailyStats } from "../../types/phase4";
import type { FlowMode } from "../../types";

const MODE_COLORS: Record<FlowMode, string> = {
  deep_work: "#8b5cf6",
  pomodoro: "#ef4444",
  kids: "#22c55e",
  sprint: "#eab308",
  free_flow: "#3b82f6",
};

const MODE_ORDER: FlowMode[] = ["deep_work", "pomodoro", "kids", "sprint", "free_flow"];

interface Props {
  data: DailyStats[];
  height?: number;
}

export const FocusChart: React.FC<Props> = ({ data, height = 200 }) => {
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-500 text-sm">
        No data available
      </div>
    );
  }

  const maxMinutes = Math.max(...data.map((d) => d.totalMinutes), 1);
  const svgWidth = 600;
  const svgHeight = height;
  const padLeft = 40;
  const padRight = 10;
  const padTop = 10;
  const padBottom = 24;
  const chartW = svgWidth - padLeft - padRight;
  const chartH = svgHeight - padTop - padBottom;
  const barGroupW = chartW / data.length;
  const barW = Math.min(barGroupW * 0.7, 32);

  return (
    <svg
      viewBox={`0 0 ${svgWidth} ${svgHeight}`}
      className="w-full"
      style={{ height }}
      aria-label="Focus minutes per day"
    >
      {/* Y-axis gridlines */}
      {[0, 0.25, 0.5, 0.75, 1].map((frac) => {
        const y = padTop + chartH * (1 - frac);
        const label = Math.round(maxMinutes * frac);
        return (
          <g key={frac}>
            <line
              x1={padLeft}
              x2={svgWidth - padRight}
              y1={y}
              y2={y}
              stroke="#2a2a3e"
              strokeWidth={1}
            />
            <text
              x={padLeft - 4}
              y={y + 4}
              fill="#6b7280"
              fontSize={10}
              textAnchor="end"
            >
              {label}
            </text>
          </g>
        );
      })}

      {/* Bars */}
      {data.map((day, i) => {
        const cx = padLeft + i * barGroupW + barGroupW / 2;
        const x = cx - barW / 2;
        let stackY = padTop + chartH;

        const segments = MODE_ORDER.map((mode) => {
          const mins = day.byMode[mode] ?? 0;
          const barH = (mins / maxMinutes) * chartH;
          const segY = stackY - barH;
          stackY = segY;
          return { mode, mins, barH, segY };
        }).filter((s) => s.mins > 0);

        const dateLabel = day.date.slice(5); // "MM-DD"

        return (
          <g key={day.date}>
            {segments.map(({ mode, barH, segY }) => (
              <rect
                key={mode}
                x={x}
                y={segY}
                width={barW}
                height={barH}
                fill={MODE_COLORS[mode]}
                rx={2}
              />
            ))}
            <text
              x={cx}
              y={padTop + chartH + 14}
              fill="#6b7280"
              fontSize={9}
              textAnchor="middle"
            >
              {dateLabel}
            </text>
          </g>
        );
      })}
    </svg>
  );
};

// Legend component
export const FocusChartLegend: React.FC = () => (
  <div className="flex flex-wrap gap-3 mt-2">
    {MODE_ORDER.map((mode) => (
      <div key={mode} className="flex items-center gap-1.5">
        <span
          className="inline-block w-3 h-3 rounded-sm"
          style={{ background: MODE_COLORS[mode] }}
        />
        <span className="text-xs text-gray-400 capitalize">
          {mode.replace("_", " ")}
        </span>
      </div>
    ))}
  </div>
);
