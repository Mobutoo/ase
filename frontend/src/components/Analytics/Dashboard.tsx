import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { FocusChart, FocusChartLegend } from "./FocusChart";
import { CategoryPie } from "./CategoryPie";
import { DensityChart } from "./DensityChart";
import { StreakCalendar } from "./StreakCalendar";
import { useAnalyticsStore } from "../../hooks/useAnalytics";
import type { DailyStats } from "../../types/phase4";
import type { FlowMode } from "../../types";
import { Clock, Activity, Target, Flame, AlertCircle } from "lucide-react";

type DateRange = "7d" | "30d" | "90d";
const DATE_RANGE_LABEL_KEYS: Record<DateRange, string> = { "7d": "range.7d", "30d": "range.30d", "90d": "range.90d" };
const EMPTY_BY_MODE: Record<FlowMode, number> = { deep_work: 0, pomodoro: 0, kids: 0, sprint: 0, free_flow: 0 };

function subtractDays(days: number): string {
  const d = new Date(); d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

function mergeByMode(days: DailyStats[]): Record<FlowMode, number> {
  return days.reduce<Record<FlowMode, number>>(
    (acc, day) => {
      const byMode = day.byMode ?? {};
      const modes = Object.keys(byMode) as FlowMode[];
      return modes.reduce((a, m) => ({ ...a, [m]: (a[m] ?? 0) + (byMode[m] ?? 0) }), acc);
    },
    { ...EMPTY_BY_MODE }
  );
}

interface CardProps { title: string; icon?: React.ReactNode; children: React.ReactNode; className?: string; }
const Card: React.FC<CardProps> = ({ title, icon, children, className = "" }) => (
  <div className={`card p-5 flex flex-col gap-3 ${className}`}>
    <div className="flex items-center gap-2">
      {icon && <div className="w-6 h-6 rounded-md bg-ase-gold/10 flex items-center justify-center">{icon}</div>}
      <h3 className="text-sm font-semibold text-ase-muted uppercase tracking-wider">{title}</h3>
    </div>
    {children}
  </div>
);

const RANGE_DAYS: Record<DateRange, number> = { "7d": 7, "30d": 30, "90d": 90 };

export const Dashboard: React.FC = () => {
  const { t } = useTranslation();
  const [range, setRange] = useState<DateRange>("30d");

  const { daily, density, streak, isLoading, error, fetchAll } = useAnalyticsStore();

  useEffect(() => {
    fetchAll(subtractDays(RANGE_DAYS[range]));
  }, [range, fetchAll]);

  const byMode = mergeByMode(daily);
  const totalMinutes = daily.reduce((s, d) => s + d.totalMinutes, 0);
  const totalHours = (totalMinutes / 60).toFixed(1);
  const totalSessions = daily.reduce((s, d) => s + d.sessionCount, 0);

  const stats = [
    { label: t("analytics.total_focus"), value: `${totalHours}h`, sub: `${totalMinutes} ${t("generic.min")}`, icon: <Clock className="w-3.5 h-3.5 text-ase-gold" /> },
    { label: t("analytics.sessions"), value: totalSessions, sub: `${t("analytics.in")} ${daily.length} ${t("analytics.days")}`, icon: <Activity className="w-3.5 h-3.5 text-ase-gold" /> },
    { label: t("analytics.avg_day"), value: `${daily.length > 0 ? (totalMinutes / daily.length).toFixed(0) : 0}m`, sub: t("analytics.focus_minutes"), icon: <Target className="w-3.5 h-3.5 text-ase-gold" /> },
    { label: t("analytics.streak"), value: streak?.currentStreak ?? 0, sub: `${t("analytics.best")}: ${streak?.longestStreak ?? 0}`, icon: <Flame className="w-3.5 h-3.5 text-ase-gold" /> },
  ];

  return (
    <div className="flex flex-col gap-6 p-6 lg:p-10 min-h-screen">
      <div className="flex items-center justify-between flex-wrap gap-3 animate-fade-in">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">{t("analytics.title")}</h1>
          <p className="text-sm text-ase-muted mt-0.5">{t("analytics.subtitle")}</p>
        </div>
        <div className="flex gap-1 bg-ase-surface rounded-xl p-1 border border-ase-border">
          {(Object.keys(DATE_RANGE_LABEL_KEYS) as DateRange[]).map((r) => (
            <button key={r} onClick={() => setRange(r)}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                range === r ? "bg-ase-gold text-ase-bg shadow-sm" : "text-ase-muted hover:text-white"
              }`}>{t(DATE_RANGE_LABEL_KEYS[r])}</button>
          ))}
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-3 bg-red-500/10 border border-red-500/15 rounded-xl px-4 py-3 animate-scale-in">
          <AlertCircle className="w-4 h-4 text-red-400" /><span className="text-sm text-red-400">{error}</span>
        </div>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {stats.map(({ label, value, sub, icon }, i) => (
          <div key={label} className="card p-4 animate-slide-up" style={{ animationDelay: `${i * 80}ms` }}>
            <div className="flex items-center gap-2 mb-2">
              <div className="w-6 h-6 rounded-md bg-ase-gold/10 flex items-center justify-center">{icon}</div>
              <p className="text-xs text-ase-subtle uppercase tracking-wide">{label}</p>
            </div>
            <p className="text-2xl font-bold text-ase-gold">{value}</p>
            <p className="text-xs text-ase-subtle mt-0.5">{sub}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card title={t("analytics.focus_minutes")} icon={<Activity className="w-3.5 h-3.5 text-ase-gold" />} className="lg:col-span-2">
          {isLoading ? <div className="h-48 animate-pulse bg-ase-surface rounded-xl" /> : <><FocusChart data={daily} /><FocusChartLegend /></>}
        </Card>
        <Card title={t("analytics.mode_distribution")} icon={<Target className="w-3.5 h-3.5 text-ase-gold" />}>
          {isLoading ? <div className="h-48 animate-pulse bg-ase-surface rounded-xl" /> : <CategoryPie byMode={byMode} />}
        </Card>
        <Card title={t("analytics.heatmap")} icon={<Flame className="w-3.5 h-3.5 text-ase-gold" />} className="lg:col-span-2">
          {isLoading ? <div className="h-32 animate-pulse bg-ase-surface rounded-xl" /> : <DensityChart data={density} weeks={52} />}
        </Card>
        <Card title={t("analytics.streak")} icon={<Flame className="w-3.5 h-3.5 text-ase-gold" />}>
          {isLoading || !streak ? <div className="h-48 animate-pulse bg-ase-surface rounded-xl" /> : (
            <div className="flex flex-col items-center gap-2 py-4">
              <p className="text-4xl font-bold text-ase-gold">{streak.currentStreak}</p>
              <p className="text-sm text-ase-muted">{t("analytics.day_streak")}</p>
              <p className="text-xs text-ase-subtle">{t("analytics.best")}: {streak.longestStreak} {t("analytics.days")}</p>
            </div>
          )}
        </Card>
        <Card title={t("analytics.streak_calendar")} icon={<Flame className="w-3.5 h-3.5 text-ase-gold" />} className="lg:col-span-3">
          {isLoading || !streak ? <div className="h-48 animate-pulse bg-ase-surface rounded-xl" /> : <div className="max-w-sm"><StreakCalendar streak={streak} /></div>}
        </Card>
      </div>
    </div>
  );
};
