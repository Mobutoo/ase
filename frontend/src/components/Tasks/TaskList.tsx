import { useEffect, useState } from "react";
import type { TaskSource } from "../../types/phase2";
import { useTasksStore } from "../../hooks/useTasks";
import { TaskCard } from "./TaskCard";
import { AddTaskModal } from "./AddTaskModal";

type FilterTab = TaskSource | "all";

const FILTER_TABS: { value: FilterTab; label: string }[] = [
  { value: "all", label: "All" },
  { value: "local", label: "Local" },
  { value: "plane", label: "Plane" },
  { value: "github", label: "GitHub" },
];

export function TaskList() {
  const tasks = useTasksStore((s) => s.tasks);
  const isLoading = useTasksStore((s) => s.isLoading);
  const error = useTasksStore((s) => s.error);
  const activeFilter = useTasksStore((s) => s.activeFilter);
  const setFilter = useTasksStore((s) => s.setFilter);
  const fetchTasks = useTasksStore((s) => s.fetchTasks);
  const clearError = useTasksStore((s) => s.clearError);

  const [isModalOpen, setIsModalOpen] = useState(false);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const filteredTasks =
    activeFilter === "all"
      ? tasks
      : tasks.filter((t) => t.source === activeFilter);

  const pendingTasks = filteredTasks.filter((t) => t.status !== "done");
  const doneTasks = filteredTasks.filter((t) => t.status === "done");

  return (
    <div className="flex flex-col h-full gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-white">Tasks</h2>
        <button
          onClick={() => setIsModalOpen(true)}
          className="
            flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium
            bg-[#f59e0b]/20 text-[#f59e0b] border border-[#f59e0b]/30
            hover:bg-[#f59e0b]/30 transition-colors duration-150
          "
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Add Task
        </button>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 bg-[#1a1a2e] rounded-xl p-1 border border-[#2a2a3e]">
        {FILTER_TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setFilter(tab.value)}
            className={`
              flex-1 py-1.5 px-3 rounded-lg text-sm font-medium transition-all duration-150
              ${
                activeFilter === tab.value
                  ? "bg-[#f59e0b]/20 text-[#f59e0b] shadow-sm"
                  : "text-[#8a8aae] hover:text-white"
              }
            `}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Error banner */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 flex items-center justify-between">
          <p className="text-sm text-red-400">{error}</p>
          <button
            onClick={clearError}
            className="text-red-400/60 hover:text-red-400 text-lg leading-none"
          >
            ×
          </button>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto space-y-2 pr-0.5">
        {isLoading && tasks.length === 0 ? (
          <div className="flex items-center justify-center py-16">
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 border-2 border-[#f59e0b]/30 border-t-[#f59e0b] rounded-full animate-spin" />
              <p className="text-sm text-[#8a8aae]">Loading tasks...</p>
            </div>
          </div>
        ) : filteredTasks.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <div className="text-4xl">📋</div>
            <p className="text-[#8a8aae] text-sm">No tasks yet</p>
            <button
              onClick={() => setIsModalOpen(true)}
              className="
                text-sm text-[#f59e0b] underline underline-offset-2
                hover:text-[#f59e0b]/80 transition-colors
              "
            >
              Create your first task
            </button>
          </div>
        ) : (
          <>
            {pendingTasks.map((task) => (
              <TaskCard key={task.id} task={task} />
            ))}

            {doneTasks.length > 0 && (
              <>
                <div className="flex items-center gap-3 py-2">
                  <div className="h-px flex-1 bg-[#2a2a3e]" />
                  <span className="text-xs text-[#6a6a8e] font-medium">
                    Completed ({doneTasks.length})
                  </span>
                  <div className="h-px flex-1 bg-[#2a2a3e]" />
                </div>
                {doneTasks.map((task) => (
                  <TaskCard key={task.id} task={task} />
                ))}
              </>
            )}
          </>
        )}
      </div>

      {/* Task count footer */}
      {filteredTasks.length > 0 && (
        <p className="text-xs text-[#6a6a8e] text-center">
          {pendingTasks.length} pending · {doneTasks.length} completed
        </p>
      )}

      <AddTaskModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
    </div>
  );
}
