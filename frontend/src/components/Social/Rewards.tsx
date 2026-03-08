import React from "react";
import type { Reward, MedalType } from "../../types/phase4";

const MEDAL_CONFIG: Record<MedalType, { emoji: string; color: string; label: string }> = {
  gold: { emoji: "🥇", color: "#f59e0b", label: "Gold" },
  silver: { emoji: "🥈", color: "#94a3b8", label: "Silver" },
  bronze: { emoji: "🥉", color: "#cd7f32", label: "Bronze" },
};

interface Props {
  rewards: Reward[];
  compact?: boolean;
}

export const Rewards: React.FC<Props> = ({ rewards, compact = false }) => {
  const safeRewards = rewards ?? [];
  const counts: Record<MedalType, number> = { gold: 0, silver: 0, bronze: 0 };
  safeRewards.forEach((r) => { counts[r.medal] += r.count; });

  if (compact) {
    return (
      <div className="flex gap-3">
        {(["gold", "silver", "bronze"] as MedalType[]).map((medal) => (
          <div key={medal} className="flex items-center gap-1">
            <span className="text-lg">{MEDAL_CONFIG[medal].emoji}</span>
            <span
              className="text-sm font-bold"
              style={{ color: MEDAL_CONFIG[medal].color }}
            >
              {counts[medal]}
            </span>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Summary row */}
      <div className="grid grid-cols-3 gap-3">
        {(["gold", "silver", "bronze"] as MedalType[]).map((medal) => {
          const cfg = MEDAL_CONFIG[medal];
          return (
            <div
              key={medal}
              className="flex flex-col items-center gap-2 bg-[#1a1a2e] border border-[#2a2a3e] rounded-xl p-4"
              style={{ borderColor: `${cfg.color}40` }}
            >
              <span className="text-4xl">{cfg.emoji}</span>
              <span
                className="text-2xl font-bold"
                style={{ color: cfg.color }}
              >
                {counts[medal]}
              </span>
              <span className="text-xs text-gray-500">{cfg.label}</span>
            </div>
          );
        })}
      </div>

      {/* History list */}
      {safeRewards.length > 0 && (
        <div className="flex flex-col gap-2">
          <h4 className="text-xs text-gray-500 uppercase tracking-wider">History</h4>
          <div className="flex flex-col gap-1.5">
            {[...safeRewards]
              .sort((a, b) => new Date(b.awardedAt).getTime() - new Date(a.awardedAt).getTime())
              .map((reward, idx) => {
                const cfg = MEDAL_CONFIG[reward.medal];
                return (
                  <div
                    key={idx}
                    className="flex items-center gap-3 bg-[#1a1a2e] border border-[#2a2a3e] rounded-lg px-3 py-2"
                  >
                    <span className="text-xl">{cfg.emoji}</span>
                    <div className="flex-1 min-w-0">
                      <p
                        className="text-sm font-medium truncate"
                        style={{ color: cfg.color }}
                      >
                        {cfg.label} Medal
                      </p>
                      <p className="text-xs text-gray-500">{reward.periodLabel}</p>
                    </div>
                    <span className="text-xs text-gray-600">
                      {new Date(reward.awardedAt).toLocaleDateString()}
                    </span>
                  </div>
                );
              })}
          </div>
        </div>
      )}
    </div>
  );
};
