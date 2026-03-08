import { useEffect, useState } from "react";
import type { TaskSource } from "../../types/phase2";
import { useTasksStore } from "../../hooks/useTasks";
import { TaskCard } from "./TaskCard";
import { AddTaskModal } from "./AddTaskModal";
import { Plus, AlertCircle, X, Inbox } from "lucide-react";

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

  useEffect(() => { fetchTasks(); }, [fetchTasks]);

  const safeTasks = tasks ?? [];
  const filteredTasks = activeFilter === "all" ? safeTasks : safeTasks.filter((t) => t.source === activeFilter);
  const pendingTasks = filteredTasks.filter((t) => t.status !== "done");
  const doneTasks = filteredTasks.filter((t) => t.status === "done");

  return (
    <div className="flex flex-col h-full gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Tasks</h2>
        <button onClick={() => setIsModalOpen(true)}
          className="group flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium bg-ase-gold/10 text-ase-gold border border-ase-gold/20 hover:bg-ase-gold/20 hover:border-ase-gold/30 hover:shadow-glow transition-all duration-200 active:scale-[0.97]">
          <Plus className="w-4 h-4 transition-transform group-hover:rotate-90 duration-200" />
          Add Task
        </button>
      </div>

      <div className="flex gap-1 bg-ase-bg/50 rounded-xl p-1 border border-ase-border/50">
        {FILTER_TABS.map((tab) => (
          <button key={tab.value} onClick={() => setFilter(tab.value)}
            className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all duration-200 ${
              activeFilter === tab.value
                ? "bg-ase-gold/15 text-ase-gold shadow-sm border border-ase-gold/20"
                : "text-ase-muted hover:text-white border border-transparent"
            }`}>
            {tab.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="flex items-center gap-3 bg-red-500/10 border border-red-500/15 rounded-xl px-4 py-3 animate-scale-in">
          <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
          <p className="text-sm text-red-400 flex-1">{error}</p>
          <button onClick={clearError} className="text-red-400/60 hover:text-red-400 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      <div className="flex-1 overflow-y-auto space-y-2 pr-0.5">
        {isLoading && safeTasks.length === 0 ? (
          <div className="flex items-center justify-center py-16">
            <div className="flex flex-col items-center gap-3">
              <div className="w-10 h-10 border-2 border-ase-gold/20 border-t-ase-gold rounded-full animate-spin" />
              <p className="text-sm text-ase-muted">Loading tasks...</p>
            </div>
          </div>
        ) : filteredTasks.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <div className="w-16 h-16 rounded-2xl bg-ase-surface border border-ase-border flex items-center justify-center">
              <Inbox className="w-7 h-7 text-ase-muted/50" />
            </div>
            <div className="text-center">
              <p className="text-ase-muted text-sm font-medium">No tasks yet</p>
              <p className="text-ase-subtle text-xs mt-1">Create your first task to get started</p>
            </div>
            <button onClick={() => setIsModalOpen(true)}
              className="text-sm text-ase-gold font-medium hover:text-ase-accent transition-colors">
              + Create Task
            </button>
          </div>
        ) : (
          <>
            {pendingTasks.map((task, i) => (
              <div key={task.id} className="animate-fade-in" style={{ animationDelay: `${i * 50}ms` }}>
                <TaskCard task={task} />
              </div>
            ))}
            {doneTasks.length > 0 && (
              <>
                <div className="flex items-center gap-3 py-3">
                  <div className="h-px flex-1 bg-ase-border/50" />
                  <span className="text-xs text-ase-subtle font-medium px-2">Completed ({doneTasks.length})</span>
                  <div className="h-px flex-1 bg-ase-border/50" />
                </div>
                {doneTasks.map((task) => (<TaskCard key={task.id} task={task} />))}
              </>
            )}
          </>
        )}
      </div>

      {filteredTasks.length > 0 && (
        <div className="flex items-center justify-center gap-4 py-1">
          <span className="text-xs text-ase-subtle"><span className="text-ase-muted font-medium">{pendingTasks.length}</span> pending</span>
          <span className="w-1 h-1 rounded-full bg-ase-border" />
          <span className="text-xs text-ase-subtle"><span className="text-ase-muted font-medium">{doneTasks.length}</span> completed</span>
        </div>
      )}

      <AddTaskModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
    </div>
  );
}
