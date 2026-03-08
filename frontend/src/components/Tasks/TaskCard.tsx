import type { UnifiedTask } from "../../types/phase2";
import { SourceBadge } from "./SourceBadge";
import { useTasksStore } from "../../hooks/useTasks";

interface TaskCardProps {
  task: UnifiedTask;
}

const PRIORITY_CONFIG: Record<
  string,
  { label: string; colorClass: string }
> = {
  urgent: { label: "Urgent", colorClass: "text-red-400 bg-red-500/20 border-red-500/30" },
  high: { label: "High", colorClass: "text-orange-400 bg-orange-500/20 border-orange-500/30" },
  medium: { label: "Medium", colorClass: "text-yellow-400 bg-yellow-500/20 border-yellow-500/30" },
  low: { label: "Low", colorClass: "text-green-400 bg-green-500/20 border-green-500/30" },
  none: { label: "", colorClass: "" },
};

export function TaskCard({ task }: TaskCardProps) {
  const startWorking = useTasksStore((s) => s.startWorking);

  const priority = PRIORITY_CONFIG[task.priority] ?? PRIORITY_CONFIG.none;
  const isDone = task.status === "done";

  const handleStartWorking = () => {
    startWorking(task.id);
  };

  return (
    <div
      className={`
        group bg-[#1a1a2e] rounded-xl border border-[#2a2a3e]
        hover:border-[#f59e0b]/30 transition-all duration-200
        p-4 flex flex-col gap-3
        ${isDone ? "opacity-60" : ""}
      `}
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          {/* Completion checkbox */}
          <div
            className={`
              mt-0.5 w-5 h-5 rounded border-2 flex-shrink-0 flex items-center justify-center
              transition-colors duration-150 cursor-pointer
              ${isDone
                ? "bg-[#f59e0b] border-[#f59e0b]"
                : "border-[#3a3a4e] hover:border-[#f59e0b]/60"
              }
            `}
          >
            {isDone && (
              <svg
                className="w-3 h-3 text-black"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={3}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M5 13l4 4L19 7"
                />
              </svg>
            )}
          </div>

          {/* Title */}
          <span
            className={`text-sm font-medium leading-snug ${
              isDone ? "line-through text-[#6a6a8e]" : "text-white"
            }`}
          >
            {task.title}
          </span>
        </div>

        {/* Priority badge */}
        {task.priority !== "none" && (
          <span
            className={`
              flex-shrink-0 text-xs px-2 py-0.5 rounded-full border font-medium
              ${priority.colorClass}
            `}
          >
            {priority.label}
          </span>
        )}
      </div>

      {/* Description */}
      {task.description && (
        <p className="text-xs text-[#8a8aae] leading-relaxed line-clamp-2 ml-8">
          {task.description}
        </p>
      )}

      {/* Footer row */}
      <div className="flex items-center justify-between gap-2 ml-8">
        <div className="flex items-center gap-2 flex-wrap">
          <SourceBadge source={task.source} />

          {/* Labels */}
          {task.labels.slice(0, 2).map((label) => (
            <span
              key={label}
              className="text-xs px-2 py-0.5 rounded-full bg-[#2a2a3e] text-[#8a8aae] border border-[#3a3a4e]"
            >
              {label}
            </span>
          ))}

          {/* Due date */}
          {task.dueDate && (
            <span className="text-xs text-[#6a6a8e]">
              Due {new Date(task.dueDate).toLocaleDateString()}
            </span>
          )}
        </div>

        {/* Start Working button */}
        {!isDone && (
          <button
            onClick={handleStartWorking}
            className="
              flex-shrink-0 text-xs px-3 py-1.5 rounded-lg
              bg-[#f59e0b]/20 text-[#f59e0b] border border-[#f59e0b]/30
              hover:bg-[#f59e0b]/30 transition-colors duration-150
              font-medium whitespace-nowrap
            "
          >
            Start Working
          </button>
        )}
      </div>
    </div>
  );
}
