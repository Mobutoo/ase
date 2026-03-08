import { useState } from "react";
import type { TaskPriority } from "../../types";
import type { CreateTaskPayload } from "../../types/phase2";
import { useTasksStore } from "../../hooks/useTasks";

interface AddTaskModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const PRIORITY_OPTIONS: { value: TaskPriority; label: string }[] = [
  { value: "urgent", label: "Urgent" },
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
  { value: "none", label: "None" },
];

const INITIAL_FORM: CreateTaskPayload = {
  title: "",
  description: "",
  priority: "medium",
  labels: [],
  dueDate: null,
  estimatedMinutes: null,
};

export function AddTaskModal({ isOpen, onClose }: AddTaskModalProps) {
  const addLocalTask = useTasksStore((s) => s.addLocalTask);
  const isLoading = useTasksStore((s) => s.isLoading);

  const [form, setForm] = useState<CreateTaskPayload>(INITIAL_FORM);
  const [labelInput, setLabelInput] = useState("");

  if (!isOpen) return null;

  const handleFieldChange = <K extends keyof CreateTaskPayload>(
    key: K,
    value: CreateTaskPayload[K]
  ) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleAddLabel = () => {
    const trimmed = labelInput.trim();
    if (!trimmed || form.labels?.includes(trimmed)) return;
    setForm((prev) => ({ ...prev, labels: [...(prev.labels ?? []), trimmed] }));
    setLabelInput("");
  };

  const handleRemoveLabel = (label: string) => {
    setForm((prev) => ({
      ...prev,
      labels: (prev.labels ?? []).filter((l) => l !== label),
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title.trim()) return;
    await addLocalTask(form);
    setForm(INITIAL_FORM);
    setLabelInput("");
    onClose();
  };

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) onClose();
  };

  return (
    <div
      className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={handleBackdropClick}
    >
      <div className="bg-[#1a1a2e] border border-[#2a2a3e] rounded-2xl w-full max-w-md shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-6 pb-4 border-b border-[#2a2a3e]">
          <h2 className="text-lg font-semibold text-white">New Task</h2>
          <button
            onClick={onClose}
            className="text-[#8a8aae] hover:text-white transition-colors text-xl leading-none"
          >
            ×
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="px-6 py-4 flex flex-col gap-4">
          {/* Title */}
          <div>
            <label className="block text-xs font-medium text-[#8a8aae] mb-1">
              Title <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={form.title}
              onChange={(e) => handleFieldChange("title", e.target.value)}
              placeholder="What needs to be done?"
              required
              className="
                w-full bg-[#0f0f1a] border border-[#2a2a3e] rounded-lg
                px-3 py-2 text-sm text-white placeholder-[#4a4a6e]
                focus:outline-none focus:border-[#f59e0b]/50 transition-colors
              "
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs font-medium text-[#8a8aae] mb-1">
              Description
            </label>
            <textarea
              value={form.description}
              onChange={(e) => handleFieldChange("description", e.target.value)}
              placeholder="Optional details..."
              rows={3}
              className="
                w-full bg-[#0f0f1a] border border-[#2a2a3e] rounded-lg
                px-3 py-2 text-sm text-white placeholder-[#4a4a6e]
                focus:outline-none focus:border-[#f59e0b]/50 transition-colors resize-none
              "
            />
          </div>

          {/* Priority + Estimate row */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-[#8a8aae] mb-1">
                Priority
              </label>
              <select
                value={form.priority}
                onChange={(e) =>
                  handleFieldChange("priority", e.target.value as TaskPriority)
                }
                className="
                  w-full bg-[#0f0f1a] border border-[#2a2a3e] rounded-lg
                  px-3 py-2 text-sm text-white
                  focus:outline-none focus:border-[#f59e0b]/50 transition-colors
                "
              >
                {PRIORITY_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-[#8a8aae] mb-1">
                Est. Minutes
              </label>
              <input
                type="number"
                min="1"
                max="480"
                value={form.estimatedMinutes ?? ""}
                onChange={(e) =>
                  handleFieldChange(
                    "estimatedMinutes",
                    e.target.value ? Number(e.target.value) : null
                  )
                }
                placeholder="e.g. 30"
                className="
                  w-full bg-[#0f0f1a] border border-[#2a2a3e] rounded-lg
                  px-3 py-2 text-sm text-white placeholder-[#4a4a6e]
                  focus:outline-none focus:border-[#f59e0b]/50 transition-colors
                "
              />
            </div>
          </div>

          {/* Due date */}
          <div>
            <label className="block text-xs font-medium text-[#8a8aae] mb-1">
              Due Date
            </label>
            <input
              type="date"
              value={form.dueDate ?? ""}
              onChange={(e) =>
                handleFieldChange("dueDate", e.target.value || null)
              }
              className="
                w-full bg-[#0f0f1a] border border-[#2a2a3e] rounded-lg
                px-3 py-2 text-sm text-white
                focus:outline-none focus:border-[#f59e0b]/50 transition-colors
              "
            />
          </div>

          {/* Labels */}
          <div>
            <label className="block text-xs font-medium text-[#8a8aae] mb-1">
              Labels
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={labelInput}
                onChange={(e) => setLabelInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleAddLabel();
                  }
                }}
                placeholder="Add label, press Enter"
                className="
                  flex-1 bg-[#0f0f1a] border border-[#2a2a3e] rounded-lg
                  px-3 py-2 text-sm text-white placeholder-[#4a4a6e]
                  focus:outline-none focus:border-[#f59e0b]/50 transition-colors
                "
              />
              <button
                type="button"
                onClick={handleAddLabel}
                className="
                  px-3 py-2 rounded-lg text-sm
                  bg-[#f59e0b]/20 text-[#f59e0b] border border-[#f59e0b]/30
                  hover:bg-[#f59e0b]/30 transition-colors
                "
              >
                Add
              </button>
            </div>
            {(form.labels ?? []).length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {(form.labels ?? []).map((label) => (
                  <span
                    key={label}
                    className="
                      inline-flex items-center gap-1 px-2 py-0.5 rounded-full
                      bg-[#2a2a3e] text-[#8a8aae] text-xs border border-[#3a3a4e]
                    "
                  >
                    {label}
                    <button
                      type="button"
                      onClick={() => handleRemoveLabel(label)}
                      className="text-[#6a6a8e] hover:text-white ml-0.5"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="
                flex-1 py-2.5 rounded-xl text-sm font-medium
                border border-[#2a2a3e] text-[#8a8aae]
                hover:border-[#3a3a4e] hover:text-white transition-colors
              "
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || !form.title.trim()}
              className="
                flex-1 py-2.5 rounded-xl text-sm font-semibold
                bg-[#f59e0b]/20 text-[#f59e0b] border border-[#f59e0b]/40
                hover:bg-[#f59e0b]/30 transition-colors
                disabled:opacity-50 disabled:cursor-not-allowed
              "
            >
              {isLoading ? "Creating..." : "Create Task"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
