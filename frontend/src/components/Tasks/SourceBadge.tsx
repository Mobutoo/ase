import { useTranslation } from "react-i18next";
import type { TaskSource } from "../../types/phase2";

interface SourceBadgeProps {
  source: TaskSource;
  className?: string;
}

const SOURCE_CONFIG: Record<
  TaskSource,
  { i18nKey: string; icon: string; colorClass: string }
> = {
  local: {
    i18nKey: "source.local",
    icon: "🏠",
    colorClass: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  },
  plane: {
    i18nKey: "source.plane",
    icon: "✈️",
    colorClass: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  },
  github: {
    i18nKey: "source.github",
    icon: "🐙",
    colorClass: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  },
  superproductivity: {
    i18nKey: "source.superproductivity",
    icon: "⚡",
    colorClass: "bg-violet-500/20 text-violet-400 border-violet-500/30",
  },
};

export function SourceBadge({ source, className = "" }: SourceBadgeProps) {
  const { t } = useTranslation();
  const config = SOURCE_CONFIG[source];

  return (
    <span
      className={`
        inline-flex items-center gap-1 px-2 py-0.5
        text-xs font-medium rounded-full border
        ${config.colorClass}
        ${className}
      `}
    >
      <span>{config.icon}</span>
      <span>{t(config.i18nKey)}</span>
    </span>
  );
}
