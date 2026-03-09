import { useState } from "react";
import { Settings2, Globe, Bot, DollarSign, Check, Loader2 } from "lucide-react";
import type { Circle, CirclePreset } from "../../types/circle";

// ---------------------------------------------------------------------------
// Common timezones (subset — avoids Intl.supportedValuesOf ES2022 dependency)
// ---------------------------------------------------------------------------

const COMMON_TIMEZONES = [
  "UTC",
  "Africa/Abidjan", "Africa/Cairo", "Africa/Johannesburg", "Africa/Lagos", "Africa/Nairobi",
  "America/Bogota", "America/Buenos_Aires", "America/Chicago", "America/Denver",
  "America/Los_Angeles", "America/Mexico_City", "America/New_York", "America/Sao_Paulo",
  "America/Toronto", "America/Vancouver",
  "Asia/Dhaka", "Asia/Dubai", "Asia/Hong_Kong", "Asia/Jakarta", "Asia/Karachi",
  "Asia/Kolkata", "Asia/Seoul", "Asia/Shanghai", "Asia/Singapore", "Asia/Tokyo",
  "Australia/Melbourne", "Australia/Sydney",
  "Europe/Amsterdam", "Europe/Berlin", "Europe/Brussels", "Europe/Istanbul",
  "Europe/London", "Europe/Madrid", "Europe/Moscow", "Europe/Paris", "Europe/Rome",
  "Pacific/Auckland", "Pacific/Honolulu",
];

// ---------------------------------------------------------------------------
// Preset options
// ---------------------------------------------------------------------------

const PRESET_OPTIONS: { value: CirclePreset; label: string; emoji: string; description: string }[] = [
  { value: "family", label: "Family", emoji: "🏠", description: "Household & family planning" },
  { value: "colocation", label: "Colocation", emoji: "🏘️", description: "Shared living space" },
  { value: "team", label: "Team", emoji: "💼", description: "Work team coordination" },
  { value: "club", label: "Club", emoji: "🎯", description: "Club or association" },
  { value: "custom", label: "Custom", emoji: "⚙️", description: "Custom configuration" },
];

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface CircleSettingsProps {
  circle: Circle;
  onSave: (payload: Partial<Circle>) => Promise<void>;
  isSaving?: boolean;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function CircleSettings({ circle, onSave, isSaving = false }: CircleSettingsProps) {
  const [draft, setDraft] = useState<Partial<Circle>>({});
  const [showSaved, setShowSaved] = useState(false);

  const effective: Circle = { ...circle, ...draft };
  const hasDraft = Object.keys(draft).length > 0;

  const patch = <K extends keyof Circle>(key: K, value: Circle[K]) => {
    setDraft((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    if (!hasDraft) return;
    await onSave(draft);
    setDraft({});
    setShowSaved(true);
    setTimeout(() => setShowSaved(false), 2500);
  };

  return (
    <div className="rounded-xl border border-ase-border bg-ase-surface p-5 flex flex-col gap-5">
      {/* Header */}
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-ase-gold/10 border border-ase-gold/20 flex items-center justify-center">
          <Settings2 className="w-3.5 h-3.5 text-ase-gold" />
        </div>
        <h3 className="text-sm font-semibold text-white">Circle settings</h3>
      </div>

      {/* Circle name */}
      <div>
        <label className="text-xs font-medium text-ase-subtle block mb-1">Circle name</label>
        <input
          type="text"
          value={effective.name}
          onChange={(e) => patch("name", e.target.value)}
          className="w-full h-9 rounded-lg border border-ase-border bg-ase-bg px-3 text-sm text-white focus:outline-none focus:border-ase-gold/50"
        />
      </div>

      {/* Timezone */}
      <div>
        <div className="flex items-center gap-1.5 mb-1">
          <Globe className="w-3.5 h-3.5 text-ase-muted" />
          <label className="text-xs font-medium text-ase-subtle">Timezone</label>
        </div>
        <select
          value={effective.timezone}
          onChange={(e) => patch("timezone", e.target.value)}
          className="w-full h-9 rounded-lg border border-ase-border bg-ase-bg px-3 text-sm text-white focus:outline-none focus:border-ase-gold/50"
        >
          {COMMON_TIMEZONES.map((tz) => (
            <option key={tz} value={tz}>{tz}</option>
          ))}
        </select>
      </div>

      {/* Preset */}
      <div>
        <label className="text-xs font-medium text-ase-subtle block mb-2">Circle type</label>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {PRESET_OPTIONS.map((opt) => {
            const selected = effective.preset === opt.value;
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => patch("preset", opt.value)}
                className={[
                  "flex flex-col items-start gap-1 rounded-xl border px-3 py-2.5 text-left transition-all duration-150",
                  selected
                    ? "border-ase-gold/40 bg-ase-gold/10"
                    : "border-ase-border bg-ase-bg hover:border-ase-border-2",
                ].join(" ")}
              >
                <span className="text-base leading-none">{opt.emoji}</span>
                <span className={[
                  "text-xs font-semibold",
                  selected ? "text-ase-gold" : "text-ase-text",
                ].join(" ")}>
                  {opt.label}
                </span>
                <span className="text-[10px] text-ase-subtle leading-tight">{opt.description}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Agent settings */}
      <div className="border-t border-ase-border pt-4">
        <div className="flex items-center gap-1.5 mb-3">
          <Bot className="w-3.5 h-3.5 text-ase-muted" />
          <h4 className="text-xs font-semibold text-ase-muted uppercase tracking-wider">AI Agent</h4>
        </div>

        {/* Agent enabled toggle */}
        <div className="flex items-center justify-between py-2">
          <div>
            <p className="text-sm font-medium text-white">Enable agent</p>
            <p className="text-xs text-ase-subtle mt-0.5">
              Agent can suggest and auto-create calendar events
            </p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={effective.agentEnabled}
            onClick={() => patch("agentEnabled", !effective.agentEnabled)}
            className={[
              "relative inline-flex h-5 w-10 flex-shrink-0 rounded-full transition-colors duration-200",
              effective.agentEnabled ? "bg-ase-gold" : "bg-zinc-700",
            ].join(" ")}
          >
            <span
              className={[
                "inline-block h-4 w-4 transform rounded-full bg-white shadow mt-0.5 transition-transform duration-200",
                effective.agentEnabled ? "translate-x-5" : "translate-x-0.5",
              ].join(" ")}
            />
          </button>
        </div>

        {/* Budget limit */}
        {effective.agentEnabled && (
          <div className="mt-2">
            <div className="flex items-center gap-1.5 mb-1">
              <DollarSign className="w-3.5 h-3.5 text-ase-muted" />
              <label className="text-xs font-medium text-ase-subtle">
                Monthly AI budget limit (USD)
              </label>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min={0}
                max={100}
                step={0.5}
                value={effective.agentBudgetLimit}
                onChange={(e) => patch("agentBudgetLimit", parseFloat(e.target.value) || 0)}
                className="w-24 h-9 rounded-lg border border-ase-border bg-ase-bg px-3 text-sm text-white text-center focus:outline-none focus:border-ase-gold/50"
              />
              <span className="text-xs text-ase-subtle">per month</span>
            </div>
          </div>
        )}
      </div>

      {/* Save bar */}
      <div className="flex items-center justify-between pt-1 border-t border-ase-border">
        {showSaved ? (
          <span className="flex items-center gap-1.5 text-sm text-green-400">
            <Check className="w-4 h-4" />
            Saved
          </span>
        ) : (
          <span className="text-xs text-ase-subtle">
            {hasDraft ? "Unsaved changes" : "All changes saved"}
          </span>
        )}
        <button
          type="button"
          onClick={handleSave}
          disabled={!hasDraft || isSaving}
          className={[
            "flex items-center gap-1.5 px-5 py-2 rounded-lg text-sm font-medium transition-all duration-150",
            hasDraft && !isSaving
              ? "bg-ase-gold text-black hover:bg-ase-gold/90"
              : "bg-ase-gold/30 text-black/50 cursor-not-allowed",
          ].join(" ")}
        >
          {isSaving && <Loader2 className="w-4 h-4 animate-spin" />}
          {isSaving ? "Saving…" : "Save changes"}
        </button>
      </div>
    </div>
  );
}
