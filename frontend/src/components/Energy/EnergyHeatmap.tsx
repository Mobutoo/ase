import { useEffect } from "react";
import { useEnergyStore } from "../../hooks/useEnergy";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const HOURS = Array.from({ length: 24 }, (_, i) => i);

// Purple-to-gold scale for energy levels 1-5
function levelToColor(level: number, count: number): string {
  if (count === 0 || isNaN(level)) return "#1a1a2e"; // no data

  // Interpolate from purple (#6b21a8) → amber (#f59e0b)
  const t = (level - 1) / 4; // 0..1

  const r = Math.round(107 + (245 - 107) * t);
  const g = Math.round(33 + (158 - 33) * t);
  const b = Math.round(168 + (11 - 168) * t);

  return `rgb(${r},${g},${b})`;
}

function formatHour(h: number): string {
  if (h === 0) return "12a";
  if (h === 12) return "12p";
  return h < 12 ? `${h}a` : `${h - 12}p`;
}

export function EnergyHeatmap() {
  const heatmap = useEnergyStore((s) => s.heatmap);
  const isLoading = useEnergyStore((s) => s.isLoading);
  const fetchHeatmap = useEnergyStore((s) => s.fetchHeatmap);

  useEffect(() => {
    fetchHeatmap();
  }, [fetchHeatmap]);

  // Build lookup: dayOfWeek × hour → entry
  const safeHeatmap = heatmap ?? [];
  const lookup = new Map<string, { avgLevel: number; count: number }>();
  for (const entry of safeHeatmap) {
    lookup.set(`${entry.dayOfWeek}-${entry.hour}`, {
      avgLevel: entry.avgLevel,
      count: entry.count,
    });
  }

  const CELL_SIZE = 14;
  const CELL_GAP = 2;
  const LEFT_PAD = 32; // space for day labels
  const TOP_PAD = 20;  // space for hour labels
  const COL_STEP = CELL_SIZE + CELL_GAP;
  const ROW_STEP = CELL_SIZE + CELL_GAP;

  const svgWidth = LEFT_PAD + HOURS.length * COL_STEP;
  const svgHeight = TOP_PAD + DAYS.length * ROW_STEP;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white">Energy Heatmap</h3>
        {isLoading && (
          <div className="w-4 h-4 border-2 border-[#f59e0b]/30 border-t-[#f59e0b] rounded-full animate-spin" />
        )}
      </div>

      {safeHeatmap.length === 0 && !isLoading ? (
        <div className="flex flex-col items-center py-8 gap-2">
          <span className="text-3xl">⚡</span>
          <p className="text-xs text-[#8a8aae] text-center">
            Log your energy to build your heatmap
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <svg
            width={svgWidth}
            height={svgHeight}
            className="block"
          >
            {/* Hour labels (top, every 3h) */}
            {HOURS.filter((h) => h % 3 === 0).map((h) => (
              <text
                key={h}
                x={LEFT_PAD + h * COL_STEP + CELL_SIZE / 2}
                y={TOP_PAD - 4}
                textAnchor="middle"
                fill="#6a6a8e"
                fontSize={9}
                fontFamily="ui-monospace,monospace"
              >
                {formatHour(h)}
              </text>
            ))}

            {/* Day labels (left) */}
            {DAYS.map((day, d) => (
              <text
                key={day}
                x={LEFT_PAD - 4}
                y={TOP_PAD + d * ROW_STEP + CELL_SIZE / 2 + 3}
                textAnchor="end"
                fill="#6a6a8e"
                fontSize={9}
                fontFamily="ui-sans-serif,sans-serif"
              >
                {day}
              </text>
            ))}

            {/* Cells */}
            {DAYS.map((_, d) =>
              HOURS.map((h) => {
                const entry = lookup.get(`${d}-${h}`);
                const color = levelToColor(
                  entry?.avgLevel ?? 0,
                  entry?.count ?? 0
                );
                return (
                  <rect
                    key={`${d}-${h}`}
                    x={LEFT_PAD + h * COL_STEP}
                    y={TOP_PAD + d * ROW_STEP}
                    width={CELL_SIZE}
                    height={CELL_SIZE}
                    rx={2}
                    ry={2}
                    fill={color}
                    opacity={entry?.count ? 0.9 : 0.25}
                  >
                    {entry && (
                      <title>
                        {DAYS[d]} {formatHour(h)} — avg {entry.avgLevel.toFixed(1)} ({entry.count} readings)
                      </title>
                    )}
                  </rect>
                );
              })
            )}
          </svg>
        </div>
      )}

      {/* Legend */}
      <div className="flex items-center gap-2">
        <span className="text-[10px] text-[#6a6a8e]">Low</span>
        <div className="flex gap-0.5">
          {[1, 2, 3, 4, 5].map((level) => (
            <div
              key={level}
              className="w-3 h-3 rounded-sm"
              style={{ backgroundColor: levelToColor(level, 1) }}
            />
          ))}
        </div>
        <span className="text-[10px] text-[#6a6a8e]">High</span>
      </div>
    </div>
  );
}
