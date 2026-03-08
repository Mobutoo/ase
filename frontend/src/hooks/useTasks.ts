import { create } from "zustand";
import type { UnifiedTask, TaskSource, CreateTaskPayload } from "../types/phase2";
import { unifiedTasks } from "../api/phase2";

interface TasksState {
  tasks: UnifiedTask[];
  isLoading: boolean;
  error: string | null;
  activeFilter: TaskSource | "all";

  // Actions
  fetchTasks: () => Promise<void>;
  addLocalTask: (payload: CreateTaskPayload) => Promise<void>;
  startWorking: (taskId: string) => Promise<void>;
  setFilter: (filter: TaskSource | "all") => void;
  clearError: () => void;
}

export const useTasksStore = create<TasksState>((set, get) => ({
  tasks: [],
  isLoading: false,
  error: null,
  activeFilter: "all",

  fetchTasks: async () => {
    set({ isLoading: true, error: null });
    try {
      const { activeFilter } = get();
      const params =
        activeFilter !== "all" ? { source: activeFilter } : undefined;
      const res = await unifiedTasks.list(params);
      set({ tasks: res.results, isLoading: false });
    } catch (err) {
      set({
        isLoading: false,
        error: err instanceof Error ? err.message : "Failed to fetch tasks",
      });
    }
  },

  addLocalTask: async (payload) => {
    set({ isLoading: true, error: null });
    try {
      const newTask = await unifiedTasks.create(payload);
      set((prev) => ({
        tasks: [newTask, ...prev.tasks],
        isLoading: false,
      }));
    } catch (err) {
      set({
        isLoading: false,
        error: err instanceof Error ? err.message : "Failed to create task",
      });
    }
  },

  startWorking: async (taskId) => {
    try {
      const updated = await unifiedTasks.startWorking(taskId);
      set((prev) => ({
        tasks: prev.tasks.map((t) =>
          t.id === taskId ? { ...t, ...updated } : t
        ),
      }));
    } catch (err) {
      set({
        error:
          err instanceof Error ? err.message : "Failed to start working on task",
      });
    }
  },

  setFilter: (filter) => {
    set({ activeFilter: filter });
    // Re-fetch with new filter
    get().fetchTasks();
  },

  clearError: () => set({ error: null }),
}));
