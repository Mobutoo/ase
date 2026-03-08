import type { FlowMode } from "./index";

// --- Analytics: Daily Stats ---
export interface DailyStats {
  date: string; // ISO date "YYYY-MM-DD"
  totalMinutes: number;
  sessionCount: number;
  completedCount: number;
  byMode: Record<FlowMode, number>; // minutes per mode
  avgEnergy: number | null;
}

// --- Analytics: Weekly Stats ---
export interface WeeklyStats {
  weekStart: string; // ISO date
  weekEnd: string;
  totalMinutes: number;
  totalSessions: number;
  completionRate: number; // 0-1
  byMode: Record<FlowMode, number>;
  bestDay: string | null;
  focusScore: number; // 0-100
}

// --- Analytics: Monthly Stats ---
export interface MonthlyStats {
  month: string; // "YYYY-MM"
  totalMinutes: number;
  totalSessions: number;
  completionRate: number;
  byMode: Record<FlowMode, number>;
  activeDays: number;
  focusScore: number;
}

// --- Density Grid Entry (GitHub-style heatmap) ---
export interface DensityEntry {
  date: string; // "YYYY-MM-DD"
  count: number; // number of sessions
  minutes: number;
}

// --- Streak Info ---
export interface StreakInfo {
  currentStreak: number;
  longestStreak: number;
  activeDates: string[]; // "YYYY-MM-DD"
  frozenDates: string[]; // dates where freeze was used
  lastActiveDate: string | null;
  freezesRemaining: number;
  freezesUsedTotal: number;
}

// --- Achievement ---
export type AchievementCategory =
  | "streak"
  | "focus"
  | "social"
  | "milestone"
  | "special";

export interface Achievement {
  id: string;
  title: string;
  description: string;
  category: AchievementCategory;
  icon: string; // emoji or icon name
  unlockedAt: string | null; // ISO datetime, null if locked
  progress: number; // 0-100
  maxProgress: number;
  xpReward: number;
}

// --- Leaderboard Entry ---
export type LeaderboardPeriod = "week" | "month" | "alltime";

export interface LeaderboardEntry {
  rank: number;
  username: string;
  displayName: string;
  avatarUrl: string | null;
  totalMinutes: number;
  sessionCount: number;
  streak: number;
  focusScore: number;
  byMode: Record<FlowMode, number>;
  isCurrentUser: boolean;
}

// --- Reward / Medal ---
export type MedalType = "gold" | "silver" | "bronze";

export interface Reward {
  medal: MedalType;
  count: number;
  periodLabel: string; // e.g. "Week of Mar 3"
  awardedAt: string; // ISO datetime
}

// --- Focus Score breakdown ---
export interface FocusScoreBreakdown {
  overall: number; // 0-100
  consistency: number; // streak component
  volume: number; // total minutes component
  completion: number; // completion rate component
  diversity: number; // mode diversity component
}
