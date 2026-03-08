import { useTranslation } from "react-i18next";
import type { UnifiedTask } from "../../types/phase2";
import { SourceBadge } from "./SourceBadge";
import { useTasksStore } from "../../hooks/useTasks";
import { Play, Check, Calendar, Clock } from "lucide-react";

interface TaskCardProps {
  task: UnifiedTask;
}

const PRIORITY_CONFIG: Record<string, { i18nKey: string; dot: string }> = {
  urgent: { i18nKey: "priority.urgent", dot: "bg-red-400" },
  high: { i18nKey: "priority.high", dot: "bg-orange-400" },
  medium: { i18nKey: "priority.medium", dot: "bg-yellow-400" },
  low: { i18nKey: "priority.low", dot: "bg-green-400" },
  none: { i18nKey: "", dot: "" },
};

export function TaskCard({ task }: TaskCardProps) {
  const { t } = useTranslation();
  const startWorking = useTasksStore((s) => s.startWorking);
  const priority = PRIORITY_CONFIG[task.priority] ?? PRIORITY_CONFIG.none;
  const isDone = task.status === "done";

  return (
    <div className={`group rounded-xl border transition-all duration-200 ${
      isDone
        ? "bg-ase-surface/50 border-ase-border/30 opacity-60"
        : "bg-ase-surface border-ase-border hover:border-ase-gold/20 hover:shadow-card"
    }`}>
      <div className="p-4 flex flex-col gap-2.5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 min-w-0">
            <div className={`mt-0.5 w-5 h-5 rounded-md border-2 flex-shrink-0 flex items-center justify-center transition-all duration-200 ${
              isDone ? "bg-ase-gold border-ase-gold" : "border-ase-border-2 group-hover:border-ase-gold/40"
            }`}>
              {isDone && <Check className="w-3 h-3 text-ase-bg" strokeWidth={3} />}
            </div>
            <span className={`text-sm font-medium leading-snug ${isDone ? "line-through text-ase-subtle" : "text-white"}`}>
              {task.title}
            </span>
          </div>
          {task.priority !== "none" && (
            <div className="flex items-center gap-1.5 flex-shrink-0">
              <div className={`w-1.5 h-1.5 rounded-full ${priority.dot}`} />
              <span className="text-xs text-ase-muted">{priority.i18nKey ? t(priority.i18nKey) : ""}</span>
            </div>
          )}
        </div>

        {task.description && (
          <p className="text-xs text-ase-subtle leading-relaxed line-clamp-2 ml-8">{task.description}</p>
        )}

        <div className="flex items-center justify-between gap-2 ml-8">
          <div className="flex items-center gap-2 flex-wrap">
            <SourceBadge source={task.source} />
            {task.labels.slice(0, 2).map((label) => (
              <span key={label} className="text-xs px-2 py-0.5 rounded-md bg-ase-bg/50 text-ase-subtle border border-ase-border/50">{label}</span>
            ))}
            {task.dueDate && (
              <span className="flex items-center gap-1 text-xs text-ase-subtle">
                <Calendar className="w-3 h-3" />{new Date(task.dueDate).toLocaleDateString()}
              </span>
            )}
            {task.estimatedMinutes && (
              <span className="flex items-center gap-1 text-xs text-ase-subtle">
                <Clock className="w-3 h-3" />{task.estimatedMinutes}m
              </span>
            )}
          </div>
          {!isDone && (
            <button onClick={() => startWorking(task.id)}
              className="flex-shrink-0 flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg bg-ase-gold/10 text-ase-gold border border-ase-gold/20 hover:bg-ase-gold/20 hover:shadow-glow transition-all duration-200 font-medium opacity-0 group-hover:opacity-100">
              <Play className="w-3 h-3 fill-current" />{t("tasks.start_working")}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
