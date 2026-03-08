import React, { useEffect, useState, useCallback } from "react";
import type { LeaderboardEntry, LeaderboardPeriod } from "../../types/phase4";
import { leaderboard as leaderboardApi } from "../../api/phase4";
import { MemberProfile } from "./MemberProfile";

const PERIOD_LABELS: Record<LeaderboardPeriod, string> = {
  week: "This Week",
  month: "This Month",
  alltime: "All Time",
};

const RANK_BORDERS: Record<number, string> = {
  1: "border-[#f59e0b]",
  2: "border-[#94a3b8]",
  3: "border-[#cd7f32]",
};

const RANK_BG: Record<number, string> = {
  1: "bg-[#f59e0b]/10",
  2: "bg-[#94a3b8]/10",
  3: "bg-[#cd7f32]/10",
};

const MEDALS = ["🥇", "🥈", "🥉"];

interface RowProps {
  entry: LeaderboardEntry;
  onClick: () => void;
}

const LeaderboardRow: React.FC<RowProps> = ({ entry, onClick }) => {
  const isTop3 = entry.rank <= 3;
  const totalHours = (entry.totalMinutes / 60).toFixed(1);
  const initials = entry.displayName
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <button
      onClick={onClick}
      className={`
        w-full flex items-center gap-3 px-4 py-3 rounded-xl border transition-all duration-200
        hover:border-[#f59e0b]/40 hover:bg-[#f59e0b]/5 text-left
        ${isTop3 ? `${RANK_BORDERS[entry.rank]} ${RANK_BG[entry.rank]}` : "border-[#2a2a3e] bg-[#1a1a2e]"}
        ${entry.isCurrentUser ? "ring-1 ring-[#f59e0b]/30" : ""}
      `}
    >
      {/* Rank */}
      <div className="w-8 text-center flex-shrink-0">
        {isTop3 ? (
          <span className="text-xl">{MEDALS[entry.rank - 1]}</span>
        ) : (
          <span className="text-sm font-bold text-gray-500">#{entry.rank}</span>
        )}
      </div>

      {/* Avatar */}
      {entry.avatarUrl ? (
        <img
          src={entry.avatarUrl}
          alt={entry.displayName}
          className="w-9 h-9 rounded-full object-cover border border-[#2a2a3e] flex-shrink-0"
        />
      ) : (
        <div className="w-9 h-9 rounded-full bg-[#2a2a3e] flex items-center justify-center text-xs font-bold text-gray-400 flex-shrink-0">
          {initials}
        </div>
      )}

      {/* Name */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <p className={`text-sm font-semibold truncate ${entry.isCurrentUser ? "text-[#f59e0b]" : "text-gray-200"}`}>
            {entry.displayName}
          </p>
          {entry.isCurrentUser && (
            <span className="text-[10px] bg-[#f59e0b]/20 text-[#f59e0b] px-1 py-0.5 rounded-full font-medium">
              You
            </span>
          )}
        </div>
        <p className="text-[11px] text-gray-500">
          {entry.sessionCount} sessions · {entry.streak}d streak
        </p>
      </div>

      {/* Hours */}
      <div className="text-right flex-shrink-0">
        <p className="text-sm font-bold text-gray-100">{totalHours}h</p>
        <p className="text-[10px] text-gray-500">focus</p>
      </div>

      {/* Score */}
      <div className="text-right w-12 flex-shrink-0">
        <p className="text-sm font-bold text-[#f59e0b]">{entry.focusScore}</p>
        <p className="text-[10px] text-gray-500">score</p>
      </div>
    </button>
  );
};

export const Leaderboard: React.FC = () => {
  const [period, setPeriod] = useState<LeaderboardPeriod>("week");
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<LeaderboardEntry | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await leaderboardApi.list(period);
      setEntries(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load leaderboard");
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="flex flex-col gap-4">
      {/* Period toggle */}
      <div className="flex gap-1 bg-[#1a1a2e] border border-[#2a2a3e] rounded-lg p-1 self-start">
        {(Object.keys(PERIOD_LABELS) as LeaderboardPeriod[]).map((p) => (
          <button
            key={p}
            onClick={() => { setPeriod(p); setSelected(null); }}
            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all duration-200 ${
              period === p
                ? "bg-[#f59e0b] text-[#0f0f0f]"
                : "text-gray-400 hover:text-gray-200"
            }`}
          >
            {PERIOD_LABELS[p]}
          </button>
        ))}
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-700 text-red-300 text-sm rounded-lg px-4 py-3">
          {error}
        </div>
      )}

      <div className="flex flex-col lg:flex-row gap-4">
        {/* List */}
        <div className="flex-1 flex flex-col gap-2">
          {loading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-16 bg-[#1a1a2e] border border-[#2a2a3e] rounded-xl animate-pulse" />
            ))
          ) : entries.length === 0 ? (
            <div className="text-center text-gray-500 py-12 text-sm">No data yet</div>
          ) : (
            entries.map((entry) => (
              <LeaderboardRow
                key={entry.username}
                entry={entry}
                onClick={() => setSelected(selected?.username === entry.username ? null : entry)}
              />
            ))
          )}
        </div>

        {/* Profile panel */}
        {selected && (
          <div className="w-full lg:w-72 flex-shrink-0">
            <MemberProfile entry={selected} />
          </div>
        )}
      </div>
    </div>
  );
};
