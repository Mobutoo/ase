import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Sparkles, AlertCircle, X, Brain, ListChecks, BookOpen, Zap } from "lucide-react";
import { useAIStore } from "../../hooks/useAI";
import type { AISuggestionType } from "../../types/phase5";
import { SUGGESTION_TYPE_LABELS } from "../../types/phase5";
import { DailyBriefing } from "./DailyBriefing";
import { ReflectionPrompt } from "./ReflectionPrompt";
import { SuggestionCard } from "./SuggestionCard";

// --- Filter tabs ---

type FilterTab = "all" | AISuggestionType;

const TABS: { id: FilterTab; label: string; Icon: React.ElementType }[] = [
  { id: "all", label: "All", Icon: Sparkles },
  { id: "task_decomposition", label: SUGGESTION_TYPE_LABELS.task_decomposition, Icon: ListChecks },
  { id: "energy_suggestion", label: SUGGESTION_TYPE_LABELS.energy_suggestion, Icon: Zap },
  { id: "daily_plan", label: SUGGESTION_TYPE_LABELS.daily_plan, Icon: Brain },
  { id: "reflection_prompt", label: SUGGESTION_TYPE_LABELS.reflection_prompt, Icon: BookOpen },
];

// --- Loading skeleton ---

function SuggestionSkeleton() {
  return (
    <div className="rounded-xl p-5 bg-[#0f0f12] border border-[#2a2a3e] animate-pulse">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-8 h-8 rounded-lg bg-[#2a2a3e]" />
        <div className="h-3 w-24 rounded bg-[#2a2a3e]" />
      </div>
      <div className="space-y-2 mb-4">
        <div className="h-3 w-full rounded bg-[#2a2a3e]" />
        <div className="h-3 w-4/5 rounded bg-[#2a2a3e]" />
        <div className="h-3 w-3/5 rounded bg-[#2a2a3e]" />
      </div>
      <div className="flex gap-2 pt-3 border-t border-[#2a2a3e]">
        <div className="h-7 w-20 rounded-lg bg-[#2a2a3e]" />
        <div className="h-7 w-20 rounded-lg bg-[#2a2a3e]" />
      </div>
    </div>
  );
}

// --- Empty state ---

function EmptySuggestions({ filter: _filter }: { filter: FilterTab }) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col items-center justify-center py-12 border border-dashed border-[#2a2a3e] rounded-xl">
      <div className="w-10 h-10 rounded-xl bg-[#f59e0b]/5 border border-[#f59e0b]/10 flex items-center justify-center mb-3">
        <Sparkles className="w-5 h-5 text-[#f59e0b]/40" />
      </div>
      <p className="text-sm text-[#8a8aae] text-center mb-1">
        {t("ai.no_items")}
      </p>
      <p className="text-xs text-[#5a5a7e] text-center leading-relaxed max-w-xs">
        {t("ai.empty_help")}
      </p>
    </div>
  );
}

// --- Main panel ---

export function AICopilotPanel() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<FilterTab>("all");

  const suggestions = useAIStore((s) => s.suggestions);
  const isLoading = useAIStore((s) => s.isLoading);
  const error = useAIStore((s) => s.error);
  const fetchSuggestions = useAIStore((s) => s.fetchSuggestions);
  const clearError = useAIStore((s) => s.clearError);

  useEffect(() => {
    fetchSuggestions();
  }, [fetchSuggestions]);

  // Exclude daily_plan and reflection_prompt from the suggestion list
  // (they are shown in dedicated cards above/below)
  const INLINE_TYPES: AISuggestionType[] = ["task_decomposition", "energy_suggestion"];

  const filteredSuggestions = suggestions.filter((s) => {
    if (activeTab === "all") {
      return INLINE_TYPES.includes(s.suggestion_type as AISuggestionType);
    }
    if (activeTab === "daily_plan" || activeTab === "reflection_prompt") {
      return false; // handled by dedicated cards
    }
    return s.suggestion_type === activeTab;
  });

  // Count per tab
  const countForTab = (tab: FilterTab): number => {
    if (tab === "all") return suggestions.filter((s) => INLINE_TYPES.includes(s.suggestion_type as AISuggestionType)).length;
    if (tab === "daily_plan" || tab === "reflection_prompt") {
      return suggestions.filter((s) => s.suggestion_type === tab).length;
    }
    return suggestions.filter((s) => s.suggestion_type === tab).length;
  };

  return (
    <div className="min-h-screen bg-ase-bg pb-20">
      {/* Page header */}
      <div className="px-6 lg:px-10 pt-8 pb-6">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-end justify-between gap-4 mb-1">
            <div className="animate-fade-in">
              <div className="flex items-center gap-3 mb-1">
                <div className="w-8 h-8 rounded-lg bg-[#f59e0b]/10 border border-[#f59e0b]/20 flex items-center justify-center">
                  <Sparkles className="w-4 h-4 text-[#f59e0b]" />
                </div>
                <h1 className="text-2xl font-bold text-white tracking-tight">{t("ai.title")}</h1>
              </div>
              <p className="text-sm text-[#8a8aae] ml-11">
                {t("ai.subtitle")}
              </p>
            </div>
          </div>
          <div className="mt-5 h-px bg-gradient-to-r from-[#f59e0b]/30 via-[#f59e0b]/10 to-transparent" />
        </div>
      </div>

      {/* Main content */}
      <div className="px-6 lg:px-10 max-w-4xl mx-auto">
        {/* Error banner */}
        {error && (
          <div className="flex items-center justify-between gap-3 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 mb-6 animate-fade-in">
            <div className="flex items-center gap-2 text-sm text-red-400">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
            <button
              onClick={clearError}
              aria-label="Dismiss error"
              className="text-red-400/60 hover:text-red-400 transition-colors duration-200"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        <div className="flex flex-col gap-6">
          {/* Daily Briefing */}
          <section className="animate-slide-up">
            <p className="text-xs font-medium uppercase tracking-wider text-[#8a8aae] mb-3">
              {t("ai.schedule")}
            </p>
            <DailyBriefing />
          </section>

          {/* Suggestions section */}
          <section className="animate-slide-up" style={{ animationDelay: "0.05s" }}>
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs font-medium uppercase tracking-wider text-[#8a8aae]">
                {t("ai.suggestions")}
              </p>
              {suggestions.length > 0 && (
                <span className="text-xs text-[#5a5a7e]">
                  {suggestions.filter((s) => s.accepted === null).length} {t("ai.pending")}
                </span>
              )}
            </div>

            {/* Filter tabs */}
            <div className="flex items-center gap-1 mb-4 overflow-x-auto pb-1">
              {TABS.map(({ id, label, Icon }) => {
                const count = countForTab(id);
                const isActive = activeTab === id;
                return (
                  <button
                    key={id}
                    onClick={() => setActiveTab(id)}
                    className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg whitespace-nowrap transition-all duration-200 font-medium flex-shrink-0 ${
                      isActive
                        ? "bg-[#f59e0b]/10 text-[#f59e0b] border border-[#f59e0b]/20"
                        : "text-[#8a8aae] hover:bg-[#2a2a3e] hover:text-white border border-transparent"
                    }`}
                  >
                    <Icon className="w-3 h-3" />
                    {label}
                    {count > 0 && (
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                        isActive ? "bg-[#f59e0b]/20 text-[#f59e0b]" : "bg-[#2a2a3e] text-[#8a8aae]"
                      }`}>
                        {count}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>

            {/* Suggestion list or skeleton */}
            {isLoading ? (
              <div className="flex flex-col gap-4">
                <SuggestionSkeleton />
                <SuggestionSkeleton />
              </div>
            ) : filteredSuggestions.length === 0 ? (
              <EmptySuggestions filter={activeTab} />
            ) : (
              <div className="flex flex-col gap-4">
                {filteredSuggestions.map((suggestion) => (
                  <SuggestionCard key={suggestion.id} suggestion={suggestion} />
                ))}
              </div>
            )}
          </section>

          {/* Reflection prompt */}
          <section className="animate-slide-up" style={{ animationDelay: "0.1s" }}>
            <p className="text-xs font-medium uppercase tracking-wider text-[#8a8aae] mb-3">
              {t("ai.reflection")}
            </p>
            <ReflectionPrompt />
          </section>
        </div>
      </div>
    </div>
  );
}
