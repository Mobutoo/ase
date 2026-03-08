import { Leaderboard as LeaderboardComponent } from "../components/Social/Leaderboard";
import { AchievementGrid } from "../components/Social/AchievementGrid";
import { Rewards } from "../components/Social/Rewards";
import { analytics as analyticsApi, leaderboard as leaderboardApi } from "../api/phase4";
import type { Achievement, Reward } from "../types/phase4";
import { useState, useEffect } from "react";
import { Trophy, Award, Medal } from "lucide-react";

type Tab = "leaderboard" | "achievements" | "rewards";

const TAB_CONFIG: Record<Tab, { label: string; icon: typeof Trophy }> = {
  leaderboard: { label: "Leaderboard", icon: Trophy },
  achievements: { label: "Achievements", icon: Award },
  rewards: { label: "Medals", icon: Medal },
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
      analyticsApi.achievements().then(setAchievements).catch(() => {}).finally(() => setLoadingAch(false));
    }
    if (tab === "rewards" && rewards.length === 0) {
      setLoadingRew(true);
      leaderboardApi.rewards().then(setRewards).catch(() => {}).finally(() => setLoadingRew(false));
    }
  }, [tab]);

  return (
    <div className="flex flex-col gap-6 p-6 lg:p-10 min-h-screen">
      {/* Header */}
      <div className="animate-fade-in">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-8 h-8 rounded-lg bg-ase-gold/10 border border-ase-gold/20 flex items-center justify-center">
            <Trophy className="w-4 h-4 text-ase-gold" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Social</h1>
        </div>
        <p className="text-sm text-ase-muted ml-11">Rankings, achievements, and medals</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-ase-surface rounded-xl p-1 border border-ase-border self-start">
        {(Object.keys(TAB_CONFIG) as Tab[]).map((t) => {
          const Icon = TAB_CONFIG[t].icon;
          return (
            <button key={t} onClick={() => setTab(t)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                tab === t
                  ? "bg-ase-gold text-ase-bg shadow-sm"
                  : "text-ase-muted hover:text-white"
              }`}>
              <Icon className="w-3.5 h-3.5" />
              {TAB_CONFIG[t].label}
            </button>
          );
        })}
      </div>

      {/* Content */}
      <div className="animate-fade-in">
        {tab === "leaderboard" && <LeaderboardComponent />}

        {tab === "achievements" && (
          loadingAch ? (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="h-32 card animate-pulse" />
              ))}
            </div>
          ) : (
            <AchievementGrid achievements={achievements} />
          )
        )}

        {tab === "rewards" && (
          loadingRew ? (
            <div className="h-48 card animate-pulse" />
          ) : (
            <Rewards rewards={rewards} />
          )
        )}
      </div>
    </div>
  );
}
