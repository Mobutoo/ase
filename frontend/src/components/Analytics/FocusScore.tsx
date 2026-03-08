import React, { useEffect, useRef, useState } from "react";
import type { FocusScoreBreakdown } from "../../types/phase4";

interface Props {
  score: FocusScoreBreakdown;
  size?: number;
}

function describeArc(cx: number, cy: number, r: number, startDeg: number, endDeg: number): string {
  const toRad = (deg: number) => ((deg - 90) * Math.PI) / 180;
  const x1 = cx + r * Math.cos(toRad(startDeg));
  const y1 = cy + r * Math.sin(toRad(startDeg));
  const x2 = cx + r * Math.cos(toRad(endDeg));
  const y2 = cy + r * Math.sin(toRad(endDeg));
  const large = endDeg - startDeg > 180 ? 1 : 0;
  return `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`;
}

const BREAKDOWN_LABELS: Array<{ key: keyof Omit<FocusScoreBreakdown, "overall">; label: string; color: string }> = [
  { key: "consistency", label: "Consistency", color: "#8b5cf6" },
  { key: "volume", label: "Volume", color: "#f59e0b" },
  { key: "completion", label: "Completion", color: "#22c55e" },
  { key: "diversity", label: "Diversity", color: "#3b82f6" },
];

export const FocusScore: React.FC<Props> = ({ score, size = 160 }) => {
  const [displayed, setDisplayed] = useState(0);
  const rafRef = useRef<number>(0);

  useEffect(() => {
    const target = score.overall;
    const duration = 1000;
    const start = performance.now();

    const animate = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // easeOutCubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayed(Math.round(eased * target));
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(animate);
      }
    };

    rafRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(rafRef.current);
  }, [score.overall]);

  const cx = size / 2;
  const cy = size / 2;
  const r = size / 2 - 16;
  const strokeW = 14;

  const endDeg = (displayed / 100) * 360;

  // Color based on score
  const gaugeColor =
    displayed >= 75 ? "#f59e0b" : displayed >= 50 ? "#8b5cf6" : displayed >= 25 ? "#3b82f6" : "#6b7280";

  return (
    <div className="flex flex-col items-center gap-4">
      {/* Circular gauge */}
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        aria-label={`Focus score: ${score.overall}`}
      >
        {/* Track */}
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="#2a2a3e"
          strokeWidth={strokeW}
        />

        {/* Fill arc */}
        {displayed > 0 && (
          <path
            d={describeArc(cx, cy, r, 0, Math.min(endDeg, 359.99))}
            fill="none"
            stroke={gaugeColor}
            strokeWidth={strokeW}
            strokeLinecap="round"
          />
        )}

        {/* Center text */}
        <text
          x={cx}
          y={cy - 8}
          fill="#f3f4f6"
          fontSize={30}
          fontWeight="bold"
          textAnchor="middle"
          dominantBaseline="middle"
        >
          {displayed}
        </text>
        <text
          x={cx}
          y={cy + 16}
          fill="#6b7280"
          fontSize={11}
          textAnchor="middle"
        >
          / 100
        </text>
      </svg>

      {/* Breakdown bars */}
      <div className="w-full space-y-2">
        {BREAKDOWN_LABELS.map(({ key, label, color }) => {
          const val = score[key];
          return (
            <div key={key} className="flex items-center gap-2">
              <span className="text-xs text-gray-400 w-20 shrink-0">{label}</span>
              <div className="flex-1 h-1.5 bg-[#2a2a3e] rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{ width: `${val}%`, background: color }}
                />
              </div>
              <span className="text-xs text-gray-500 w-8 text-right">{val}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
