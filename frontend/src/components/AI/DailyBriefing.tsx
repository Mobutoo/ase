import { CalendarDays, RefreshCw, Brain, Clock } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useAIStore } from "../../hooks/useAI";
import type { AISuggestion, DailyPlanContent, DailyPlanItem } from "../../types/phase5";

// --- Helpers ---

function extractPlanContent(suggestion: AISuggestion): DailyPlanContent | null {
  const raw = suggestion.content;
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  return raw as DailyPlanContent;
}

function getPlanItems(plan: DailyPlanContent): DailyPlanItem[] {
  return plan.items ?? plan.tasks ?? [];
}

// --- Sub-components ---

function PlanItem({ item, index }: { item: DailyPlanItem; index: number }) {
  const title = item.task ?? item.title ?? `Step ${index + 1}`;
  const time = item.time;
  const duration = item.duration_minutes;
  const notes = item.notes;

  return (
    <div className="flex items-start gap-3 py-2.5 border-b border-[#2a2a3e] last:border-0">
      {/* Index badge */}
      <div className="flex-shrink-0 w-5 h-5 rounded-full bg-[#f59e0b]/10 border border-[#f59e0b]/20 flex items-center justify-center mt-0.5">
        <span className="text-[10px] font-bold text-[#f59e0b]">{index + 1}</span>
      </div>

      <div className="flex-1 min-w-0">
        <p className="text-sm text-white font-medium leading-snug">{title}</p>
        {notes && (
          <p className="text-xs text-[#8a8aae] mt-0.5 leading-relaxed">{notes}</p>
        )}
      </div>

      <div className="flex items-center gap-2 flex-shrink-0">
        {time && (
          <span className="flex items-center gap-1 text-xs text-[#8a8aae]">
            <Clock className="w-3 h-3" />
            {time}
          </span>
        )}
        {duration && !time && (
          <span className="text-xs text-[#5a5a7e]">{duration}m</span>
        )}
      </div>
    </div>
  );
}

function EmptyPlan({ onRequest, isLoading }: { onRequest: () => void; isLoading: boolean }) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col items-center justify-center py-10 px-4 border border-dashed border-[#2a2a3e] rounded-xl">
      <div className="w-10 h-10 rounded-xl bg-[#f59e0b]/5 border border-[#f59e0b]/10 flex items-center justify-center mb-3">
        <Brain className="w-5 h-5 text-[#f59e0b]/40" />
      </div>
      <p className="text-sm text-[#8a8aae] text-center mb-1">{t("ai.no_plan")}</p>
      <p className="text-xs text-[#5a5a7e] text-center mb-4 leading-relaxed">
        {t("ai.no_plan_help")}
      </p>
      <button
        onClick={onRequest}
        disabled={isLoading}
        className="flex items-center gap-2 text-xs px-4 py-2 rounded-lg bg-[#f59e0b]/10 text-[#f59e0b] border border-[#f59e0b]/20 hover:bg-[#f59e0b]/20 transition-all duration-200 font-medium disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <RefreshCw className={`w-3 h-3 ${isLoading ? "animate-spin" : ""}`} />
        {isLoading ? t("ai.requesting") : t("ai.generate_plan")}
      </button>
    </div>
  );
}

// --- Main component ---

export function DailyBriefing() {
  const { t } = useTranslation();
  const suggestions = useAIStore((s) => s.suggestions);
  const isRequestingPlan = useAIStore((s) => s.isRequestingPlan);
  const requestDailyPlan = useAIStore((s) => s.requestDailyPlan);

  // Pick the most recent daily_plan suggestion
  const planSuggestion = suggestions
    .filter((s) => s.suggestion_type === "daily_plan")
    [0] ?? null;

  const planContent = planSuggestion ? extractPlanContent(planSuggestion) : null;
  const items = planContent ? getPlanItems(planContent) : [];
  const summary = planContent?.summary;

  return (
    <div className="rounded-xl p-5 bg-[#0f0f12] border border-[#2a2a3e] hover:border-[#3a3a5e] transition-all duration-200">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-[#f59e0b]/10 border border-[#f59e0b]/20 flex items-center justify-center">
            <CalendarDays className="w-4 h-4 text-[#f59e0b]" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">{t("ai.plan_title")}</h3>
            <p className="text-xs text-[#8a8aae]">
              {new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })}
            </p>
          </div>
        </div>

        {planSuggestion && (
          <button
            onClick={() => requestDailyPlan()}
            disabled={isRequestingPlan}
            title="Request a new plan"
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg text-[#8a8aae] hover:bg-[#2a2a3e] hover:text-white transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RefreshCw className={`w-3 h-3 ${isRequestingPlan ? "animate-spin" : ""}`} />
            {isRequestingPlan ? t("ai.requesting") : t("ai.new_plan")}
          </button>
        )}
      </div>

      {/* Content */}
      {!planSuggestion ? (
        <EmptyPlan onRequest={() => requestDailyPlan()} isLoading={isRequestingPlan} />
      ) : (
        <div>
          {summary && (
            <p className="text-sm text-[#c0c0d8] leading-relaxed mb-4 pb-4 border-b border-[#2a2a3e]">
              {summary}
            </p>
          )}

          {items.length > 0 ? (
            <div className="flex flex-col">
              {items.map((item, i) => (
                <PlanItem key={i} item={item} index={i} />
              ))}
            </div>
          ) : (
            <p className="text-sm text-[#8a8aae] leading-relaxed">
              {typeof planContent === "object" && planContent !== null
                ? JSON.stringify(planSuggestion.content, null, 2)
                : t("ai.no_plan_items")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
