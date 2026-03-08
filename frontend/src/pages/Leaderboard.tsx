import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Leaderboard as LeaderboardComponent } from "../components/Social/Leaderboard";
import { AchievementGrid } from "../components/Social/AchievementGrid";
import { useLeaderboardStore } from "../hooks/useLeaderboard";
import type { Achievement } from "../types/phase4";
import { Trophy, Award, Medal, Star } from "lucide-react";

type Tab = "leaderboard" | "achievements" | "rewards";

const TAB_CONFIG: Record<Tab, { labelKey: string; icon: typeof Trophy }> = {
  leaderboard: { labelKey: "social.leaderboard", icon: Trophy },
  achievements: { labelKey: "social.achievements", icon: Award },
  rewards: { labelKey: "social.medals", icon: Medal },
};

export function Leaderboard() {
  const { t } = useTranslation();
  const [tab, setTab] = useState<Tab>("leaderboard");

  const {
    achievements,
    rewards,
    isLoading,
    fetchAchievements,
    fetchRewards,
  } = useLeaderboardStore();

  useEffect(() => {
    if (tab === "achievements" && achievements.length === 0) {
      fetchAchievements();
    }
    if (tab === "rewards" && rewards.total_achievements === 0 && rewards.recent.length === 0) {
      fetchRewards();
    }
  }, [tab, achievements.length, rewards.total_achievements, rewards.recent.length, fetchAchievements, fetchRewards]);

  return (
    <div className="flex flex-col gap-6 p-6 lg:p-10 min-h-screen">
      {/* Header */}
      <div className="animate-fade-in">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-8 h-8 rounded-lg bg-ase-gold/10 border border-ase-gold/20 flex items-center justify-center">
            <Trophy className="w-4 h-4 text-ase-gold" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">{t("social.title")}</h1>
        </div>
        <p className="text-sm text-ase-muted ml-11">{t("social.subtitle")}</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-ase-surface rounded-xl p-1 border border-ase-border self-start">
        {(Object.keys(TAB_CONFIG) as Tab[]).map((tabKey) => {
          const Icon = TAB_CONFIG[tabKey].icon;
          return (
            <button key={tabKey} onClick={() => setTab(tabKey)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                tab === tabKey
                  ? "bg-ase-gold text-ase-bg shadow-sm"
                  : "text-ase-muted hover:text-white"
              }`}>
              <Icon className="w-3.5 h-3.5" />
              {t(TAB_CONFIG[tabKey].labelKey)}
            </button>
          );
        })}
      </div>

      {/* Content */}
      <div className="animate-fade-in">
        {tab === "leaderboard" && <LeaderboardComponent />}

        {tab === "achievements" && (
          isLoading ? (
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
          isLoading ? (
            <div className="h-48 card animate-pulse" />
          ) : (
            <RewardsPanel
              totalAchievements={rewards.total_achievements}
              recent={rewards.recent}
            />
          )
        )}
      </div>
    </div>
  );
}

/** Rewards panel — shows total achievements + recent unlocks */
function RewardsPanel({ totalAchievements, recent }: { totalAchievements: number; recent: Achievement[] }) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-6">
      {/* Total count */}
      <div className="card p-6 flex items-center gap-4">
        <div className="w-12 h-12 rounded-xl bg-ase-gold/10 border border-ase-gold/20 flex items-center justify-center">
          <Star className="w-6 h-6 text-ase-gold" />
        </div>
        <div>
          <p className="text-3xl font-bold text-white font-mono">{totalAchievements}</p>
          <p className="text-sm text-ase-muted">{t("social.total_unlocked")}</p>
        </div>
      </div>

      {/* Recent unlocks */}
      {recent.length > 0 ? (
        <div className="flex flex-col gap-2">
          <h4 className="text-xs text-ase-subtle uppercase tracking-wider font-medium">
            {t("social.recent_unlocks")}
          </h4>
          <div className="flex flex-col gap-1.5">
            {recent.map((r, idx) => (
              <div
                key={idx}
                className="flex items-center gap-3 card px-4 py-3"
              >
                <div className="w-8 h-8 rounded-lg bg-ase-gold/10 flex items-center justify-center">
                  <Award className="w-4 h-4 text-ase-gold" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white capitalize">
                    {r.title}
                  </p>
                  <p className="text-xs text-ase-subtle">
                    {r.unlockedAt ? new Date(r.unlockedAt).toLocaleDateString() : ""}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center text-center border border-dashed border-ase-border rounded-xl p-12">
          <Medal className="w-12 h-12 text-ase-subtle mb-3" strokeWidth={1.5} />
          <p className="text-lg font-medium text-zinc-300">{t("social.no_medals")}</p>
          <p className="text-sm text-ase-subtle max-w-sm mt-1">
            {t("social.no_medals_desc")}
          </p>
        </div>
      )}
    </div>
  );
}
