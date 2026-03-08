import { useState } from "react";
import { BookOpen, RefreshCw, Send } from "lucide-react";
import { useAIStore } from "../../hooks/useAI";
import type { AISuggestion, ReflectionPromptContent } from "../../types/phase5";

// --- Helpers ---

function extractReflectionContent(suggestion: AISuggestion): ReflectionPromptContent | null {
  const raw = suggestion.content;
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  return raw as ReflectionPromptContent;
}

function getQuestions(content: ReflectionPromptContent): string[] {
  const questions: string[] = [];
  if (content.prompt) questions.push(content.prompt);
  if (content.questions) {
    content.questions.forEach((q) => {
      if (q !== content.prompt) questions.push(q);
    });
  }
  return questions.filter(Boolean);
}

// --- Empty state ---

function EmptyReflection({ onRequest, isLoading }: { onRequest: () => void; isLoading: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center py-10 px-4 border border-dashed border-[#2a2a3e] rounded-xl">
      <div className="w-10 h-10 rounded-xl bg-[#34d399]/5 border border-[#34d399]/10 flex items-center justify-center mb-3">
        <BookOpen className="w-5 h-5 text-[#34d399]/40" />
      </div>
      <p className="text-sm text-[#8a8aae] text-center mb-1">No reflection prompt yet</p>
      <p className="text-xs text-[#5a5a7e] text-center mb-4 leading-relaxed">
        At the end of the day, get an AI-generated reflection prompt based on your sessions.
      </p>
      <button
        onClick={onRequest}
        disabled={isLoading}
        className="flex items-center gap-2 text-xs px-4 py-2 rounded-lg bg-[#34d399]/10 text-[#34d399] border border-[#34d399]/20 hover:bg-[#34d399]/20 transition-all duration-200 font-medium disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <RefreshCw className={`w-3 h-3 ${isLoading ? "animate-spin" : ""}`} />
        {isLoading ? "Requesting..." : "Get Reflection Prompt"}
      </button>
    </div>
  );
}

// --- Main component ---

export function ReflectionPrompt() {
  const [notes, setNotes] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const suggestions = useAIStore((s) => s.suggestions);
  const isRequestingReflection = useAIStore((s) => s.isRequestingReflection);
  const requestReflection = useAIStore((s) => s.requestReflection);
  const acceptSuggestion = useAIStore((s) => s.acceptSuggestion);

  // Pick the most recent reflection_prompt suggestion
  const reflectionSuggestion = suggestions
    .filter((s) => s.suggestion_type === "reflection_prompt")
    [0] ?? null;

  const reflectionContent = reflectionSuggestion
    ? extractReflectionContent(reflectionSuggestion)
    : null;

  const questions = reflectionContent ? getQuestions(reflectionContent) : [];
  const theme = reflectionContent?.theme;

  function handleSubmit() {
    if (!reflectionSuggestion || !notes.trim()) return;
    // Accept the suggestion when the user submits their reflection
    acceptSuggestion(reflectionSuggestion.id);
    setSubmitted(true);
  }

  function handleNewPrompt() {
    setNotes("");
    setSubmitted(false);
    requestReflection();
  }

  return (
    <div className="rounded-xl p-5 bg-[#0f0f12] border border-[#2a2a3e] hover:border-[#3a3a5e] transition-all duration-200">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-[#34d399]/10 border border-[#34d399]/20 flex items-center justify-center">
            <BookOpen className="w-4 h-4 text-[#34d399]" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">End-of-Day Reflection</h3>
            {theme && (
              <p className="text-xs text-[#8a8aae]">{theme}</p>
            )}
          </div>
        </div>

        {reflectionSuggestion && (
          <button
            onClick={handleNewPrompt}
            disabled={isRequestingReflection}
            title="Get a new reflection prompt"
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg text-[#8a8aae] hover:bg-[#2a2a3e] hover:text-white transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RefreshCw className={`w-3 h-3 ${isRequestingReflection ? "animate-spin" : ""}`} />
            {isRequestingReflection ? "Requesting..." : "New Prompt"}
          </button>
        )}
      </div>

      {/* Content */}
      {!reflectionSuggestion ? (
        <EmptyReflection onRequest={handleNewPrompt} isLoading={isRequestingReflection} />
      ) : submitted ? (
        /* Submitted state */
        <div className="flex flex-col items-center justify-center py-8">
          <div className="w-10 h-10 rounded-full bg-[#34d399]/10 border border-[#34d399]/20 flex items-center justify-center mb-3">
            <Send className="w-5 h-5 text-[#34d399]" />
          </div>
          <p className="text-sm text-white font-medium mb-1">Reflection saved</p>
          <p className="text-xs text-[#8a8aae] text-center mb-4 leading-relaxed">
            Great work taking time to reflect. See you tomorrow.
          </p>
          <button
            onClick={handleNewPrompt}
            className="text-xs text-[#8a8aae] hover:text-white transition-colors duration-200"
          >
            Start a new reflection
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {/* Questions */}
          {questions.length > 0 && (
            <div className="flex flex-col gap-2">
              {questions.map((q, i) => (
                <div
                  key={i}
                  className={`flex items-start gap-3 ${i > 0 ? "pt-2 border-t border-[#2a2a3e]" : ""}`}
                >
                  <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-[#34d399]/60 flex-shrink-0" />
                  <p className="text-sm text-[#c0c0d8] leading-relaxed">{q}</p>
                </div>
              ))}
            </div>
          )}

          {/* Text area */}
          <div>
            <label className="block text-xs font-medium text-[#8a8aae] uppercase tracking-wider mb-2">
              Your Notes
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Write your reflection here..."
              rows={5}
              className="w-full rounded-lg bg-[#1a1a2e] border border-[#2a2a3e] focus:border-[#34d399]/40 focus:outline-none text-sm text-[#c0c0d8] placeholder:text-[#5a5a7e] px-3 py-2.5 leading-relaxed resize-none transition-colors duration-200"
            />
          </div>

          {/* Submit */}
          <div className="flex items-center justify-end">
            <button
              onClick={handleSubmit}
              disabled={!notes.trim()}
              className="flex items-center gap-2 text-xs px-4 py-2 rounded-lg bg-[#34d399]/10 text-[#34d399] border border-[#34d399]/20 hover:bg-[#34d399]/20 transition-all duration-200 font-medium disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Send className="w-3 h-3" />
              Save Reflection
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
