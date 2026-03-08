import React, { useState } from "react";
import type { Achievement, AchievementCategory } from "../../types/phase4";

interface Props {
  achievements: Achievement[];
}

const CATEGORY_LABELS: Record<AchievementCategory, string> = {
  streak: "Streak",
  focus: "Focus",
  social: "Social",
  milestone: "Milestone",
  special: "Special",
};

const CATEGORY_ORDER: AchievementCategory[] = [
  "milestone", "streak", "focus", "social", "special",
];

interface AchievementCardProps {
  achievement: Achievement;
}

const AchievementCard: React.FC<AchievementCardProps> = ({ achievement }) => {
  const unlocked = achievement.unlockedAt !== null;
  const pct = Math.min((achievement.progress / achievement.maxProgress) * 100, 100);

  return (
    <div
      className={`
        relative flex flex-col items-center gap-2 p-4 rounded-xl border transition-all duration-300
        ${unlocked
          ? "bg-[#1a1a2e] border-[#f59e0b] ring-2 ring-[#f59e0b] shadow-[0_0_15px_rgba(245,158,11,0.3)]"
          : "bg-[#1a1a2e] border-[#2a2a3e] opacity-60 grayscale"
        }
      `}
    >
      {/* Icon */}
      <div className={`text-3xl ${!unlocked ? "grayscale opacity-40" : ""}`}>
        {achievement.icon}
      </div>

      {/* Title */}
      <div className="text-center">
        <p className={`text-sm font-semibold ${unlocked ? "text-gray-100" : "text-gray-500"}`}>
          {achievement.title}
        </p>
        <p className="text-xs text-gray-500 mt-0.5 leading-tight">
          {achievement.description}
        </p>
      </div>

      {/* Progress bar */}
      {!unlocked && achievement.maxProgress > 1 && (
        <div className="w-full">
          <div className="flex justify-between text-[10px] text-gray-600 mb-1">
            <span>{achievement.progress}</span>
            <span>{achievement.maxProgress}</span>
          </div>
          <div className="h-1 bg-[#2a2a3e] rounded-full overflow-hidden">
            <div
              className="h-full bg-[#4b3a1f] rounded-full"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      )}

      {/* XP badge */}
      {unlocked && (
        <span className="absolute top-2 right-2 text-[10px] font-bold text-[#f59e0b] bg-[#78350f]/40 px-1.5 py-0.5 rounded-full">
          +{achievement.xpReward}xp
        </span>
      )}

      {/* Unlock date */}
      {unlocked && achievement.unlockedAt && (
        <p className="text-[10px] text-gray-600">
          {new Date(achievement.unlockedAt).toLocaleDateString()}
        </p>
      )}
    </div>
  );
};

export const AchievementGrid: React.FC<Props> = ({ achievements }) => {
  const [filter, setFilter] = useState<AchievementCategory | "all">("all");

  const unlockedCount = achievements.filter((a) => a.unlockedAt !== null).length;

  const filtered =
    filter === "all"
      ? achievements
      : achievements.filter((a) => a.category === filter);

  // Sort: unlocked first, then by category order
  const sorted = [...filtered].sort((a, b) => {
    if (a.unlockedAt && !b.unlockedAt) return -1;
    if (!a.unlockedAt && b.unlockedAt) return 1;
    return 0;
  });

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h2 className="text-base font-bold text-gray-100">Achievements</h2>
          <p className="text-sm text-gray-500">
            {unlockedCount} / {achievements.length} unlocked
          </p>
        </div>

        {/* Progress bar */}
        <div className="flex items-center gap-2">
          <div className="w-32 h-2 bg-[#2a2a3e] rounded-full overflow-hidden">
            <div
              className="h-full bg-[#f59e0b] rounded-full transition-all duration-500"
              style={{ width: achievements.length > 0 ? `${(unlockedCount / achievements.length) * 100}%` : "0%" }}
            />
          </div>
          <span className="text-xs text-gray-500">
            {achievements.length > 0 ? Math.round((unlockedCount / achievements.length) * 100) : 0}%
          </span>
        </div>
      </div>

      {/* Category filter */}
      <div className="flex gap-1.5 flex-wrap">
        {(["all", ...CATEGORY_ORDER] as const).map((cat) => (
          <button
            key={cat}
            onClick={() => setFilter(cat)}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-all duration-200 ${
              filter === cat
                ? "bg-[#f59e0b] text-[#0f0f0f]"
                : "bg-[#2a2a3e] text-gray-400 hover:text-gray-200"
            }`}
          >
            {cat === "all" ? "All" : CATEGORY_LABELS[cat]}
          </button>
        ))}
      </div>

      {/* Grid */}
      {sorted.length === 0 ? (
        <div className="text-center text-gray-500 py-8 text-sm">No achievements found</div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          {sorted.map((a) => (
            <AchievementCard key={a.id} achievement={a} />
          ))}
        </div>
      )}
    </div>
  );
};
