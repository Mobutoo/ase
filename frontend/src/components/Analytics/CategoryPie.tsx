import React from "react";
import type { FlowMode } from "../../types";

const MODE_COLORS: Record<FlowMode, string> = {
  deep_work: "#8b5cf6",
  pomodoro: "#ef4444",
  kids: "#22c55e",
  sprint: "#eab308",
  free_flow: "#3b82f6",
};

const MODE_LABELS: Record<FlowMode, string> = {
  deep_work: "Deep Work",
  pomodoro: "Pomodoro",
  kids: "Kids",
  sprint: "Sprint",
  free_flow: "Free Flow",
};

interface Props {
  byMode: Record<FlowMode, number>; // minutes
  size?: number;
}

function polarToCartesian(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}


export const CategoryPie: React.FC<Props> = ({ byMode, size = 180 }) => {
  const safeByMode = byMode ?? ({} as Record<FlowMode, number>);
  const modes = Object.keys(safeByMode) as FlowMode[];
  const totalMinutes = modes.reduce((sum, m) => sum + (safeByMode[m] ?? 0), 0);
  const totalHours = (totalMinutes / 60).toFixed(1);

  if (totalMinutes === 0) {
    return (
      <div className="flex items-center justify-center h-44 text-gray-500 text-sm">
        No data
      </div>
    );
  }

  const cx = size / 2;
  const cy = size / 2;
  const outerR = size / 2 - 8;
  const innerR = outerR * 0.55;

  let currentAngle = 0;
  const slices = modes
    .filter((m) => (safeByMode[m] ?? 0) > 0)
    .map((mode) => {
      const mins = safeByMode[mode] ?? 0;
      const sweep = (mins / totalMinutes) * 360;
      const startAngle = currentAngle;
      currentAngle += sweep;
      return { mode, mins, startAngle, endAngle: currentAngle };
    });

  return (
    <div className="flex flex-col items-center gap-4">
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        aria-label="Focus mode distribution"
      >
        {/* Donut slices */}
        {slices.map(({ mode, startAngle, endAngle }) => {
          // Draw as filled sector minus inner circle via clip or path
          const outerStart = polarToCartesian(cx, cy, outerR, endAngle);
          const outerEnd = polarToCartesian(cx, cy, outerR, startAngle);
          const innerStart = polarToCartesian(cx, cy, innerR, endAngle);
          const innerEnd = polarToCartesian(cx, cy, innerR, startAngle);
          const largeArc = endAngle - startAngle > 180 ? 1 : 0;

          const d = [
            `M ${outerStart.x} ${outerStart.y}`,
            `A ${outerR} ${outerR} 0 ${largeArc} 0 ${outerEnd.x} ${outerEnd.y}`,
            `L ${innerEnd.x} ${innerEnd.y}`,
            `A ${innerR} ${innerR} 0 ${largeArc} 1 ${innerStart.x} ${innerStart.y}`,
            "Z",
          ].join(" ");

          return (
            <path
              key={mode}
              d={d}
              fill={MODE_COLORS[mode]}
              stroke="#0f0f0f"
              strokeWidth={2}
              className="transition-opacity duration-200 hover:opacity-80"
            />
          );
        })}

        {/* Center label */}
        <text x={cx} y={cy - 6} fill="#f3f4f6" fontSize={18} fontWeight="bold" textAnchor="middle">
          {totalHours}h
        </text>
        <text x={cx} y={cy + 12} fill="#6b7280" fontSize={10} textAnchor="middle">
          total focus
        </text>
      </svg>

      {/* Legend */}
      <div className="flex flex-col gap-1.5 w-full px-2">
        {slices.map(({ mode, mins }) => {
          const pct = ((mins / totalMinutes) * 100).toFixed(0);
          return (
            <div key={mode} className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span
                  className="inline-block w-2.5 h-2.5 rounded-full flex-shrink-0"
                  style={{ background: MODE_COLORS[mode] }}
                />
                <span className="text-xs text-gray-300">{MODE_LABELS[mode]}</span>
              </div>
              <span className="text-xs text-gray-500">{pct}%</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
