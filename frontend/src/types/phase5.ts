// --- AI Suggestion Types ---

export type AISuggestionType =
  | "daily_plan"
  | "task_decomposition"
  | "reflection_prompt"
  | "energy_suggestion";

/**
 * A single AI-generated suggestion as returned by the backend serializer.
 * `accepted` is null when pending, true when accepted, false when dismissed.
 */
export interface AISuggestion {
  id: number;
  username: string;
  suggestionType: AISuggestionType;
  /** Arbitrary JSON from the AI — shape varies by suggestionType. */
  content: unknown;
  accepted: boolean | null;
  createdAt: string;
}

// --- Content shapes by type (best-effort — AI output may vary) ---

export interface DailyPlanItem {
  time?: string;
  task?: string;
  title?: string;
  durationMinutes?: number;
  notes?: string;
}

export interface DailyPlanContent {
  summary?: string;
  items?: DailyPlanItem[];
  tasks?: DailyPlanItem[];
}

export interface TaskDecompositionContent {
  taskTitle?: string;
  steps?: string[];
  subtasks?: string[];
  estimatedTotalMinutes?: number;
}

export interface ReflectionPromptContent {
  prompt?: string;
  questions?: string[];
  theme?: string;
}

export interface EnergySuggestionContent {
  level?: number;
  recommendation?: string;
  tips?: string[];
}

// --- API request/response shapes ---

export interface AISuggestionListParams {
  type?: AISuggestionType;
  pending?: "true" | "false";
}

export interface PlanRequestPayload {
  include_done_tasks?: boolean;
  energy_days?: number;
}

/** Returned by request_plan / request_reflection when n8n processes async. */
export interface WebhookAckResponse {
  status: "queued";
  message: string;
}

// --- UI helpers ---

export const SUGGESTION_TYPE_LABELS: Record<AISuggestionType, string> = {
  daily_plan: "Daily Plan",
  task_decomposition: "Task Breakdown",
  reflection_prompt: "Reflection",
  energy_suggestion: "Energy Tip",
};
