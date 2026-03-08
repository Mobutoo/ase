interface ProgressRingProps {
  /** 0 to 1 */
  progress: number;
  size?: number;
  strokeWidth?: number;
  color?: string;
  bgColor?: string;
  children?: React.ReactNode;
}

export function ProgressRing({
  progress,
  size = 300,
  strokeWidth = 4,
  color = "#f59e0b",
  bgColor = "rgba(245, 158, 11, 0.08)",
  children,
}: ProgressRingProps) {
  const pad = 32;
  const full = size + pad;
  const cx = full / 2;
  const cy = full / 2;
  const radius = (size - strokeWidth * 2) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - Math.min(1, Math.max(0, progress)));
  const outerR = radius + 16;
  const innerR = radius - 12;

  return (
    <div className="relative" style={{ width: full, height: full }}>
      <svg
        width={full}
        height={full}
        className="transform -rotate-90"
        viewBox={`0 0 ${full} ${full}`}
      >
        {/* Outer decorative dashes */}
        <circle cx={cx} cy={cy} r={outerR} fill="none"
          stroke="rgba(30,30,63,0.3)" strokeWidth={1} strokeDasharray="4 8" />

        {/* BG ring */}
        <circle cx={cx} cy={cy} r={radius} fill="none"
          stroke={bgColor} strokeWidth={strokeWidth} />

        {/* Progress */}
        <circle cx={cx} cy={cy} r={radius} fill="none"
          stroke={color} strokeWidth={strokeWidth + 2} strokeLinecap="round"
          strokeDasharray={circumference} strokeDashoffset={offset}
          className="transition-[stroke-dashoffset] duration-500 ease-linear"
          style={{ filter: `drop-shadow(0 0 6px ${color}40)` }} />

        {/* Inner ring */}
        <circle cx={cx} cy={cy} r={innerR} fill="none"
          stroke="rgba(30,30,63,0.2)" strokeWidth={1} />

        {/* Tip dot */}
        {progress > 0.01 && progress < 0.99 && (
          <circle
            cx={cx + radius * Math.cos(2 * Math.PI * progress - Math.PI / 2)}
            cy={cy + radius * Math.sin(2 * Math.PI * progress - Math.PI / 2)}
            r={5} fill={color}
            style={{ filter: `drop-shadow(0 0 8px ${color}80)` }} />
        )}
      </svg>

      <div className="absolute inset-0 flex items-center justify-center">
        {children}
      </div>
    </div>
  );
}
