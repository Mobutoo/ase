/**
 * Phase 4 API: Analytics, Leaderboard, Achievements, Rewards
 */

import type {
  DailyStats,
  WeeklyStats,
  MonthlyStats,
  DensityEntry,
  StreakInfo,
  Achievement,
  LeaderboardEntry,
  LeaderboardPeriod,
} from "../types/phase4";

/**
 * Shape returned by GET /api/v1/leaderboard/rewards/
 * Backend returns { total_achievements, recent } — NOT an array of Reward.
 */
export interface RewardsResponse {
  total_achievements: number;
  recent: Achievement[];
}

function getCsrfToken(): string {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : "";
}

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-CSRFToken": getCsrfToken(),
    ...(options.headers as Record<string, string> ?? {}),
  };
  const res = await fetch(url, { ...options, headers, credentials: "same-origin" });
  if (!res.ok) {
    const body = await res.text();
    console.error(`API Error ${res.status}:`, body);
    if (res.status === 401 || res.status === 403) {
      throw new Error("Please log in to continue");
    }
    if (res.status === 404) {
      throw new Error("Resource not found");
    }
    if (res.status >= 500) {
      throw new Error("Server error — please try again later");
    }
    throw new Error(`Request failed (${res.status})`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

function buildQs(params?: Record<string, string>): string {
  return params ? "?" + new URLSearchParams(params).toString() : "";
}

// --- Analytics ---
export const analytics = {
  daily: (params?: { from?: string; to?: string; username?: string }) => {
    const p = params
      ? Object.fromEntries(
          Object.entries(params).filter(([, v]) => v != null) as [string, string][]
        )
      : undefined;
    return request<DailyStats[]>(`/api/v1/analytics/daily/${buildQs(p)}`);
  },

  weekly: (params?: { from?: string; to?: string; username?: string }) => {
    const p = params
      ? Object.fromEntries(
          Object.entries(params).filter(([, v]) => v != null) as [string, string][]
        )
      : undefined;
    return request<WeeklyStats[]>(`/api/v1/analytics/weekly/${buildQs(p)}`);
  },

  monthly: (params?: { year?: string; username?: string }) => {
    const p = params
      ? Object.fromEntries(
          Object.entries(params).filter(([, v]) => v != null) as [string, string][]
        )
      : undefined;
    return request<MonthlyStats[]>(`/api/v1/analytics/monthly/${buildQs(p)}`);
  },

  density: (params?: { weeks?: string; username?: string }) => {
    const p = params
      ? Object.fromEntries(
          Object.entries(params).filter(([, v]) => v != null) as [string, string][]
        )
      : undefined;
    return request<DensityEntry[]>(`/api/v1/analytics/density/${buildQs(p)}`);
  },

  streak: (username?: string) => {
    const qs = username ? `?username=${encodeURIComponent(username)}` : "";
    return request<StreakInfo>(`/api/v1/analytics/streak/${qs}`);
  },

  achievements: (username?: string) => {
    const qs = username ? `?username=${encodeURIComponent(username)}` : "";
    return request<Achievement[]>(`/api/v1/analytics/achievements/${qs}`);
  },
};

// Backend period values → frontend LeaderboardPeriod mapping
const PERIOD_MAP: Record<LeaderboardPeriod, string> = {
  week: "weekly",
  month: "monthly",
  alltime: "all_time",
};

// --- Leaderboard ---
export const leaderboard = {
  list: (period: LeaderboardPeriod = "week", limit = 20) =>
    request<LeaderboardEntry[]>(
      `/api/v1/leaderboard/?period=${PERIOD_MAP[period]}&limit=${limit}`
    ),

  rewards: (username?: string) => {
    const qs = username ? `?username=${encodeURIComponent(username)}` : "";
    return request<RewardsResponse>(`/api/v1/leaderboard/rewards/${qs}`);
  },
};
