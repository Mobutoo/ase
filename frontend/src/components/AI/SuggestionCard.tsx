import { Brain, ListChecks, BookOpen, Zap, Check, X, Loader2 } from "lucide-react";
import type { AISuggestion, AISuggestionType } from "../../types/phase5";
import { SUGGESTION_TYPE_LABELS } from "../../types/phase5";
import { useAIStore } from "../../hooks/useAI";

// --- Icon mapping by suggestion type ---
const TYPE_ICON: Record<AISuggestionType, React.ElementType> = {
  daily_plan: Brain,
  task_decomposition: ListChecks,
  reflection_prompt: BookOpen,
  energy_suggestion: Zap,
};

const TYPE_COLOR: Record<AISuggestionType, string> = {
  daily_plan: "text-[#f59e0b]",
  task_decomposition: "text-[#818cf8]",
  reflection_prompt: "text-[#34d399]",
  energy_suggestion: "text-[#f472b6]",
};

const TYPE_BG: Record<AISuggestionType, string> = {
  daily_plan: "bg-[#f59e0b]/10 border-[#f59e0b]/20",
  task_decomposition: "bg-[#818cf8]/10 border-[#818cf8]/20",
  reflection_prompt: "bg-[#34d399]/10 border-[#34d399]/20",
  energy_suggestion: "bg-[#f472b6]/10 border-[#f472b6]/20",
};

// --- Content renderer ---
function renderContent(content: unknown): React.ReactNode {
  if (content === null || content === undefined) return null;

  if (typeof content === "string") {
    return (
      <p className="text-sm text-[#c0c0d8] leading-relaxed whitespace-pre-line">
        {content}
      </p>
    );
  }

  if (typeof content === "object" && !Array.isArray(content)) {
    const obj = content as Record<string, unknown>;

    // Collect text fields to display
    const lines: string[] = [];
    if (typeof obj.summary === "string") lines.push(obj.summary);
    if (typeof obj.recommendation === "string") lines.push(obj.recommendation);
    if (typeof obj.prompt === "string") lines.push(obj.prompt);
    if (typeof obj.task_title === "string") lines.push(`Task: ${obj.task_title}`);

    const items: string[] = [];
    const steps = obj.steps ?? obj.subtasks ?? obj.items ?? obj.tasks ?? obj.tips ?? obj.questions;
    if (Array.isArray(steps)) {
      steps.forEach((step: unknown) => {
        if (typeof step === "string") {
          items.push(step);
        } else if (step && typeof step === "object") {
          const s = step as Record<string, unknown>;
          const label = s.time
            ? `${s.time} — ${s.task ?? s.title ?? ""}`
            : (s.task ?? s.title ?? String(s));
          items.push(String(label));
        }
      });
    }

    return (
      <div className="flex flex-col gap-2">
        {lines.map((line, i) => (
          <p key={i} className="text-sm text-[#c0c0d8] leading-relaxed">
            {line}
          </p>
        ))}
        {items.length > 0 && (
          <ul className="flex flex-col gap-1.5 mt-1">
            {items.map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-[#c0c0d8]">
                <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-[#f59e0b]/60 flex-shrink-0" />
                {item}
              </li>
            ))}
          </ul>
        )}
        {lines.length === 0 && items.length === 0 && (
          <p className="text-sm text-[#8a8aae] leading-relaxed font-mono">
            {JSON.stringify(content, null, 2)}
          </p>
        )}
      </div>
    );
  }

  return (
    <p className="text-sm text-[#8a8aae] font-mono leading-relaxed">
      {JSON.stringify(content, null, 2)}
    </p>
  );
}

// --- Timestamp formatter ---
function formatTimestamp(isoString: string): string {
  try {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60_000);
    if (diffMins < 1) return "just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  } catch {
    return "";
  }
}

// --- Props ---
interface SuggestionCardProps {
  suggestion: AISuggestion;
}

export function SuggestionCard({ suggestion }: SuggestionCardProps) {
  const acceptSuggestion = useAIStore((s) => s.acceptSuggestion);
  const dismissSuggestion = useAIStore((s) => s.dismissSuggestion);
  const actioningIds = useAIStore((s) => s.actioningIds);

  const isActioning = actioningIds.has(suggestion.id);
  const isAccepted = suggestion.accepted === true;
  const isDismissed = suggestion.accepted === false;
  const isPending = suggestion.accepted === null;

  const Icon = TYPE_ICON[suggestion.suggestion_type] ?? Brain;
  const iconColor = TYPE_COLOR[suggestion.suggestion_type] ?? "text-[#f59e0b]";
  const iconBg = TYPE_BG[suggestion.suggestion_type] ?? "bg-[#f59e0b]/10 border-[#f59e0b]/20";
  const label = SUGGESTION_TYPE_LABELS[suggestion.suggestion_type] ?? suggestion.suggestion_type;

  return (
    <div
      className={`rounded-xl p-5 border transition-all duration-200 ${
        isDismissed
          ? "bg-[#0f0f12] border-[#2a2a3e] opacity-40"
          : isAccepted
          ? "bg-[#0f0f12] border-[#34d399]/20"
          : "bg-[#0f0f12] border-[#2a2a3e] hover:border-[#3a3a5e]"
      }`}
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-3">
          <div className={`w-8 h-8 rounded-lg border flex items-center justify-center flex-shrink-0 ${iconBg}`}>
            <Icon className={`w-4 h-4 ${iconColor}`} />
          </div>
          <div>
            <span className="text-xs font-medium uppercase tracking-wider text-[#8a8aae]">
              {label}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          {isAccepted && (
            <span className="flex items-center gap-1.5 text-xs text-[#34d399] font-medium">
              <Check className="w-3.5 h-3.5" />
              Accepted
            </span>
          )}
          {isDismissed && (
            <span className="text-xs text-[#5a5a7e]">Dismissed</span>
          )}
          <span className="text-xs text-[#5a5a7e]">
            {formatTimestamp(suggestion.created_at)}
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="mb-4">
        {renderContent(suggestion.content)}
      </div>

      {/* Action buttons — only shown for pending suggestions */}
      {isPending && (
        <div className="flex items-center gap-2 pt-3 border-t border-[#2a2a3e]">
          <button
            onClick={() => acceptSuggestion(suggestion.id)}
            disabled={isActioning}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg bg-[#f59e0b]/10 text-[#f59e0b] border border-[#f59e0b]/20 hover:bg-[#f59e0b]/20 transition-all duration-200 font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isActioning ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <Check className="w-3 h-3" />
            )}
            Accept
          </button>
          <button
            onClick={() => dismissSuggestion(suggestion.id)}
            disabled={isActioning}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg text-[#8a8aae] hover:bg-[#2a2a3e] hover:text-white transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isActioning ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <X className="w-3 h-3" />
            )}
            Dismiss
          </button>
        </div>
      )}
    </div>
  );
}
