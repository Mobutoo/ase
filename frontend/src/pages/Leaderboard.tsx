import { Leaderboard as LeaderboardComponent } from "../components/Social/Leaderboard";
import { AchievementGrid } from "../components/Social/AchievementGrid";
import { Rewards } from "../components/Social/Rewards";
import { analytics as analyticsApi, leaderboard as leaderboardApi } from "../api/phase4";
import type { Achievement, Reward } from "../types/phase4";
import { useState, useEffect } from "react";

type Tab = "leaderboard" | "achievements" | "rewards";

const TAB_LABELS: Record<Tab, string> = {
  leaderboard: "Leaderboard",
  achievements: "Achievements",
  rewards: "Medals",
};

export function Leaderboard() {
  const [tab, setTab] = useState<Tab>("leaderboard");
  const [achievements, setAchievements] = useState<Achievement[]>([]);
  const [rewards, setRewards] = useState<Reward[]>([]);
  const [loadingAch, setLoadingAch] = useState(false);
  const [loadingRew, setLoadingRew] = useState(false);

  useEffect(() => {
    if (tab === "achievements" && achievements.length === 0) {
      setLoadingAch(true);
      analyticsApi.achievements()
        .then(setAchievements)
        .catch(() => {})
        .finally(() => setLoadingAch(false));
    }
    if (tab === "rewards" && rewards.length === 0) {
      setLoadingRew(true);
      leaderboardApi.rewards()
        .then(setRewards)
        .catch(() => {})
        .finally(() => setLoadingRew(false));
    }
  }, [tab]);

  return (
    <div className="flex flex-col gap-6 p-4 lg:p-6 bg-[#0f0f0f] min-h-screen">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-gray-100">Social</h1>
        <p className="text-sm text-gray-500">Rankings, achievements, and medals</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-[#1a1a2e] border border-[#2a2a3e] rounded-lg p-1 self-start">
        {(Object.keys(TAB_LABELS) as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all duration-200 ${
              tab === t
                ? "bg-[#f59e0b] text-[#0f0f0f]"
                : "text-gray-400 hover:text-gray-200"
            }`}
          >
            {TAB_LABELS[t]}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "leaderboard" && <LeaderboardComponent />}

      {tab === "achievements" && (
        loadingAch ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-32 bg-[#1a1a2e] border border-[#2a2a3e] rounded-xl animate-pulse" />
            ))}
          </div>
        ) : (
          <AchievementGrid achievements={achievements} />
        )
      )}

      {tab === "rewards" && (
        loadingRew ? (
          <div className="h-48 bg-[#1a1a2e] border border-[#2a2a3e] rounded-xl animate-pulse" />
        ) : (
          <Rewards rewards={rewards} />
        )
      )}
    </div>
  );
}
