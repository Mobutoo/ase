import React, { useEffect, useState, useCallback } from "react";
import { FocusChart, FocusChartLegend } from "./FocusChart";
import { CategoryPie } from "./CategoryPie";
import { DensityChart } from "./DensityChart";
import { StreakCalendar } from "./StreakCalendar";
import { FocusScore } from "./FocusScore";
import { analytics } from "../../api/phase4";
import type { DailyStats, DensityEntry, StreakInfo, FocusScoreBreakdown } from "../../types/phase4";
import type { FlowMode } from "../../types";

type DateRange = "7d" | "30d" | "90d";

const DATE_RANGE_LABELS: Record<DateRange, string> = {
  "7d": "7 days",
  "30d": "30 days",
  "90d": "90 days",
};

const EMPTY_BY_MODE: Record<FlowMode, number> = {
  deep_work: 0, pomodoro: 0, kids: 0, sprint: 0, free_flow: 0,
};

function subtractDays(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

function mergeByMode(days: DailyStats[]): Record<FlowMode, number> {
  return days.reduce<Record<FlowMode, number>>(
    (acc, day) => {
      const modes = Object.keys(day.byMode) as FlowMode[];
      return modes.reduce((a, m) => ({ ...a, [m]: (a[m] ?? 0) + (day.byMode[m] ?? 0) }), acc);
    },
    { ...EMPTY_BY_MODE }
  );
}

interface CardProps {
  title: string;
  children: React.ReactNode;
  className?: string;
}

const Card: React.FC<CardProps> = ({ title, children, className = "" }) => (
  <div className={`bg-[#1a1a2e] border border-[#2a2a3e] rounded-xl p-4 flex flex-col gap-3 ${className}`}>
    <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">{title}</h3>
    {children}
  </div>
);

export const Dashboard: React.FC = () => {
  const [range, setRange] = useState<DateRange>("30d");
  const [daily, setDaily] = useState<DailyStats[]>([]);
  const [density, setDensity] = useState<DensityEntry[]>([]);
  const [streak, setStreak] = useState<StreakInfo | null>(null);
  const [focusScore, setFocusScore] = useState<FocusScoreBreakdown | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const rangeDays: Record<DateRange, number> = { "7d": 7, "30d": 30, "90d": 90 };

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const from = subtractDays(rangeDays[range]);
      const [dailyData, densityData, streakData, scoreData] = await Promise.all([
        analytics.daily({ from }),
        analytics.density({ weeks: "52" }),
        analytics.streak(),
        analytics.focusScore(),
      ]);
      setDaily(dailyData);
      setDensity(densityData);
      setStreak(streakData);
      setFocusScore(scoreData);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load analytics");
    } finally {
      setLoading(false);
    }
  }, [range]);

  useEffect(() => { load(); }, [load]);

  const byMode = mergeByMode(daily);
  const totalMinutes = daily.reduce((s, d) => s + d.totalMinutes, 0);
  const totalHours = (totalMinutes / 60).toFixed(1);
  const totalSessions = daily.reduce((s, d) => s + d.sessionCount, 0);

  return (
    <div className="flex flex-col gap-6 p-4 lg:p-6 bg-[#0f0f0f] min-h-screen">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-100">Analytics</h1>
          <p className="text-sm text-gray-500">Your focus performance over time</p>
        </div>

        <div className="flex gap-1 bg-[#1a1a2e] border border-[#2a2a3e] rounded-lg p-1">
          {(Object.keys(DATE_RANGE_LABELS) as DateRange[]).map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all duration-200 ${
                range === r
                  ? "bg-[#f59e0b] text-[#0f0f0f]"
                  : "text-gray-400 hover:text-gray-200"
              }`}
            >
              {DATE_RANGE_LABELS[r]}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-700 text-red-300 text-sm rounded-lg px-4 py-3">
          {error}
        </div>
      )}

      {/* Summary stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { label: "Total Focus", value: `${totalHours}h`, sub: `${totalMinutes} min` },
          { label: "Sessions", value: totalSessions, sub: `in ${daily.length} days` },
          { label: "Avg/Day", value: `${daily.length > 0 ? (totalMinutes / daily.length).toFixed(0) : 0}m`, sub: "focus minutes" },
          { label: "Focus Score", value: focusScore?.overall ?? "—", sub: "/ 100" },
        ].map(({ label, value, sub }) => (
          <div
            key={label}
            className="bg-[#1a1a2e] border border-[#2a2a3e] rounded-xl p-4"
          >
            <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
            <p className="text-2xl font-bold text-[#f59e0b] mt-1">{value}</p>
            <p className="text-xs text-gray-600 mt-0.5">{sub}</p>
          </div>
        ))}
      </div>

      {/* Main charts grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Focus chart — spans 2 cols */}
        <Card title="Focus Minutes / Day" className="lg:col-span-2">
          {loading ? (
            <div className="h-48 animate-pulse bg-[#2a2a3e] rounded" />
          ) : (
            <>
              <FocusChart data={daily} />
              <FocusChartLegend />
            </>
          )}
        </Card>

        {/* Pie */}
        <Card title="Mode Distribution">
          {loading ? (
            <div className="h-48 animate-pulse bg-[#2a2a3e] rounded" />
          ) : (
            <CategoryPie byMode={byMode} />
          )}
        </Card>

        {/* Density */}
        <Card title="Activity Heatmap (52 weeks)" className="lg:col-span-2">
          {loading ? (
            <div className="h-32 animate-pulse bg-[#2a2a3e] rounded" />
          ) : (
            <DensityChart data={density} weeks={52} />
          )}
        </Card>

        {/* Focus Score */}
        <Card title="Focus Score">
          {loading || !focusScore ? (
            <div className="h-48 animate-pulse bg-[#2a2a3e] rounded" />
          ) : (
            <FocusScore score={focusScore} />
          )}
        </Card>

        {/* Streak Calendar */}
        <Card title="Streak Calendar" className="lg:col-span-3">
          {loading || !streak ? (
            <div className="h-48 animate-pulse bg-[#2a2a3e] rounded" />
          ) : (
            <div className="max-w-sm">
              <StreakCalendar streak={streak} />
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};
