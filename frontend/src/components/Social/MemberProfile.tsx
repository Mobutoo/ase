import React from "react";
import type { LeaderboardEntry } from "../../types/phase4";
import type { FlowMode } from "../../types";
import { CategoryPie } from "../Analytics/CategoryPie";

const MEDAL_RANK: Record<number, { emoji: string; color: string }> = {
  1: { emoji: "🥇", color: "#f59e0b" },
  2: { emoji: "🥈", color: "#94a3b8" },
  3: { emoji: "🥉", color: "#cd7f32" },
};

interface Props {
  entry: LeaderboardEntry;
  achievements?: number;
}

export const MemberProfile: React.FC<Props> = ({ entry, achievements = 0 }) => {
  const rankMedal = MEDAL_RANK[entry.rank];
  const totalHours = (entry.totalMinutes / 60).toFixed(1);
  const initials = entry.displayName
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <div className="bg-[#1a1a2e] border border-[#2a2a3e] rounded-xl p-5 flex flex-col gap-4">
      {/* Top row: avatar + name + rank */}
      <div className="flex items-center gap-3">
        {entry.avatarUrl ? (
          <img
            src={entry.avatarUrl}
            alt={entry.displayName}
            className="w-14 h-14 rounded-full object-cover border-2 border-[#2a2a3e]"
          />
        ) : (
          <div className="w-14 h-14 rounded-full bg-[#2a2a3e] flex items-center justify-center text-lg font-bold text-gray-300 flex-shrink-0">
            {initials}
          </div>
        )}

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <p className="font-bold text-gray-100 truncate">{entry.displayName}</p>
            {rankMedal && <span className="text-lg">{rankMedal.emoji}</span>}
          </div>
          <p className="text-xs text-gray-500">@{entry.username}</p>
          {entry.isCurrentUser && (
            <span className="inline-block mt-0.5 text-[10px] bg-[#f59e0b]/20 text-[#f59e0b] px-1.5 py-0.5 rounded-full font-medium">
              You
            </span>
          )}
        </div>

        <div className="text-right">
          <p className="text-xl font-bold text-[#f59e0b]">#{entry.rank}</p>
          <p className="text-xs text-gray-500">rank</p>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-4 gap-2 text-center">
        {[
          { label: "Hours", value: `${totalHours}h` },
          { label: "Sessions", value: entry.sessionCount },
          { label: "Streak", value: `${entry.streak}d` },
          { label: "Score", value: entry.focusScore },
        ].map(({ label, value }) => (
          <div key={label} className="bg-[#0f0f0f] rounded-lg p-2">
            <p className="text-sm font-bold text-gray-100">{value}</p>
            <p className="text-[10px] text-gray-500 mt-0.5">{label}</p>
          </div>
        ))}
      </div>

      {/* Mini pie */}
      <div className="flex items-center gap-4">
        <div className="flex-shrink-0">
          <CategoryPie byMode={(entry.byMode ?? {}) as Record<FlowMode, number>} size={100} />
        </div>
        <div className="flex flex-col gap-1 text-xs text-gray-500">
          {achievements > 0 && (
            <p>
              <span className="text-gray-300 font-medium">{achievements}</span> achievements
            </p>
          )}
          <p className="leading-relaxed">
            Primarily focuses on{" "}
            <span className="text-gray-300">
              {Object.entries(entry.byMode ?? {})
                .sort(([, a], [, b]) => b - a)[0]?.[0]
                ?.replace("_", " ") ?? "—"}
            </span>
          </p>
        </div>
      </div>
    </div>
  );
};
