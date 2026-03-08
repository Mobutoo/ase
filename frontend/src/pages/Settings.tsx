import { useEffect, useState, useCallback } from "react";
import {
  Settings as SettingsIcon,
  Clock,
  Palette,
  Music,
  Zap,
  Users,
  Database,
  Check,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { useSettingsStore } from "../hooks/useSettings";
import type { UserSettings } from "../types";

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface ToggleProps {
  checked: boolean;
  onChange: (value: boolean) => void;
  disabled?: boolean;
}

function Toggle({ checked, onChange, disabled = false }: ToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={[
        "relative inline-flex h-5 w-10 flex-shrink-0 cursor-pointer rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-ase-gold/50 focus:ring-offset-2 focus:ring-offset-transparent",
        checked ? "bg-ase-gold" : "bg-zinc-700",
        disabled ? "opacity-50 cursor-not-allowed" : "",
      ].join(" ")}
    >
      <span
        className={[
          "pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out mt-0.5",
          checked ? "translate-x-5" : "translate-x-0.5",
        ].join(" ")}
      />
    </button>
  );
}

interface NumberInputProps {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  disabled?: boolean;
  suffix?: string;
}

function NumberInput({
  value,
  onChange,
  min = 1,
  max = 300,
  disabled = false,
  suffix,
}: NumberInputProps) {
  const [local, setLocal] = useState(String(value));

  useEffect(() => {
    setLocal(String(value));
  }, [value]);

  const commit = () => {
    const n = parseInt(local, 10);
    if (!isNaN(n) && n >= min && n <= max) {
      onChange(n);
    } else {
      setLocal(String(value));
    }
  };

  return (
    <div className="flex items-center gap-2">
      <input
        type="number"
        min={min}
        max={max}
        value={local}
        disabled={disabled}
        onChange={(e) => setLocal(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => e.key === "Enter" && commit()}
        className="h-9 w-20 rounded-lg border border-[#2a2a3e] bg-[#0a0a14] px-3 text-sm text-white placeholder:text-[#5a5a7e] focus:outline-none focus:ring-2 focus:ring-ase-gold/50 focus:border-ase-gold/50 disabled:opacity-50 disabled:cursor-not-allowed text-center"
      />
      {suffix && <span className="text-xs text-ase-muted">{suffix}</span>}
    </div>
  );
}

interface SettingRowProps {
  label: string;
  description?: string;
  children: React.ReactNode;
}

function SettingRow({ label, description, children }: SettingRowProps) {
  return (
    <div className="flex items-center justify-between gap-4 py-3">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-white">{label}</p>
        {description && (
          <p className="text-xs text-ase-muted mt-0.5">{description}</p>
        )}
      </div>
      <div className="flex-shrink-0">{children}</div>
    </div>
  );
}

interface CardProps {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  children: React.ReactNode;
}

function Card({ icon: Icon, title, children }: CardProps) {
  return (
    <div className="rounded-xl p-6 bg-[#0f0f12] border border-[#2a2a3e]">
      <div className="flex items-center gap-2.5 mb-5">
        <Icon className="w-4 h-4 text-ase-gold" />
        <h2 className="text-sm font-medium uppercase tracking-wider text-[#8a8aae]">
          {title}
        </h2>
      </div>
      <div className="divide-y divide-[#1e1e3f]">{children}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Theme picker
// ---------------------------------------------------------------------------

const THEMES: { value: string; label: string; color: string }[] = [
  { value: "default", label: "Default", color: "#f59e0b" },
  { value: "white", label: "White", color: "#e2e8f0" },
  { value: "forest", label: "Forest", color: "#22c55e" },
  { value: "aquamarine", label: "Aquamarine", color: "#06b6d4" },
  { value: "garnet", label: "Garnet", color: "#be185d" },
  { value: "coral", label: "Coral", color: "#f97316" },
  { value: "afrofuturist", label: "Afrofuturist", color: "#a855f7" },
];

interface ThemePickerProps {
  value: string;
  onChange: (value: string) => void;
}

function ThemePicker({ value, onChange }: ThemePickerProps) {
  return (
    <div className="py-3">
      <p className="text-sm font-medium text-white mb-3">Theme</p>
      <div className="flex flex-wrap gap-3">
        {THEMES.map((theme) => (
          <button
            key={theme.value}
            type="button"
            onClick={() => onChange(theme.value)}
            title={theme.label}
            className={[
              "group relative flex flex-col items-center gap-1.5 p-0 focus:outline-none",
            ].join(" ")}
          >
            <span
              className={[
                "w-8 h-8 rounded-full flex items-center justify-center transition-all duration-150 ring-offset-2 ring-offset-[#0f0f12]",
                value === theme.value
                  ? "ring-2 scale-110"
                  : "ring-1 ring-transparent hover:scale-105",
              ].join(" ")}
              style={{
                backgroundColor: theme.color,
                boxShadow:
                  value === theme.value
                    ? `0 0 12px ${theme.color}66`
                    : undefined,
                // Use CSS ring color inline since it's dynamic
                outline:
                  value === theme.value
                    ? `2px solid ${theme.color}`
                    : "2px solid transparent",
                outlineOffset: "2px",
              }}
            >
              {value === theme.value && (
                <Check className="w-3.5 h-3.5 text-black drop-shadow" />
              )}
            </span>
            <span
              className={[
                "text-[10px] font-medium transition-colors",
                value === theme.value ? "text-white" : "text-ase-muted",
              ].join(" ")}
            >
              {theme.label}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Playlist URL input row
// ---------------------------------------------------------------------------

const FLOW_MODES: { key: string; label: string }[] = [
  { key: "deep_work", label: "Deep Work" },
  { key: "pomodoro", label: "Pomodoro" },
  { key: "sprint", label: "Sprint" },
  { key: "kids", label: "Kids" },
  { key: "free_flow", label: "Free Flow" },
];

interface PlaylistRowProps {
  mode: string;
  label: string;
  url: string;
  onChange: (url: string) => void;
}

function PlaylistRow({ label, url, onChange }: PlaylistRowProps) {
  const [local, setLocal] = useState(url);

  useEffect(() => {
    setLocal(url);
  }, [url]);

  return (
    <div className="py-3">
      <p className="text-xs text-ase-muted mb-1.5">{label}</p>
      <input
        type="url"
        value={local}
        placeholder="https://youtube.com/watch?v=..."
        onChange={(e) => setLocal(e.target.value)}
        onBlur={() => onChange(local)}
        onKeyDown={(e) => e.key === "Enter" && onChange(local)}
        className="h-9 w-full rounded-lg border border-[#2a2a3e] bg-[#0a0a14] px-3 text-sm text-white placeholder:text-[#5a5a7e] focus:outline-none focus:ring-2 focus:ring-ase-gold/50 focus:border-ase-gold/50"
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Source badge
// ---------------------------------------------------------------------------

interface SourceBadgeProps {
  label: string;
  enabled: boolean;
}

function SourceBadge({ label, enabled }: SourceBadgeProps) {
  return (
    <div className="flex items-center justify-between py-3">
      <span className="text-sm text-white">{label}</span>
      <span
        className={[
          "text-xs px-2.5 py-0.5 rounded-full font-medium border",
          enabled
            ? "text-green-400 border-green-400/30 bg-green-400/10"
            : "text-ase-muted border-ase-border bg-transparent",
        ].join(" ")}
      >
        {enabled ? "Active" : "Not configured"}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Settings page
// ---------------------------------------------------------------------------

export function Settings() {
  const { settings, isLoading, isSaving, error, savedAt, fetchSettings, updateSettings, clearError } =
    useSettingsStore();

  // Local draft — edits are buffered here; saved on button click
  const [draft, setDraft] = useState<Partial<UserSettings>>({});
  const [showSaved, setShowSaved] = useState(false);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  // When settings load, initialise draft
  useEffect(() => {
    if (settings) {
      setDraft({});
    }
  }, [settings]);

  // Flash "Saved" indicator
  useEffect(() => {
    if (savedAt) {
      setShowSaved(true);
      const t = setTimeout(() => setShowSaved(false), 2500);
      return () => clearTimeout(t);
    }
  }, [savedAt]);

  const patch = useCallback(
    <K extends keyof UserSettings>(key: K, value: UserSettings[K]) => {
      setDraft((prev) => ({ ...prev, [key]: value }));
    },
    []
  );

  const patchPlaylist = useCallback(
    (mode: string, url: string) => {
      setDraft((prev) => ({
        ...prev,
        youtube_default_playlists: {
          ...(settings?.youtube_default_playlists ?? {}),
          ...(prev.youtube_default_playlists ?? {}),
          [mode]: url,
        },
      }));
    },
    [settings]
  );

  const handleSave = async () => {
    if (Object.keys(draft).length === 0) return;
    await updateSettings(draft);
    setDraft({});
  };

  // Merged view: settings from server merged with unsaved draft
  const effective: UserSettings | null = settings
    ? { ...settings, ...draft }
    : null;

  const hasDraft = Object.keys(draft).length > 0;

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  if (isLoading && !settings) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-6 h-6 text-ase-gold animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6 lg:p-10 min-h-screen max-w-2xl mx-auto">
      {/* Header */}
      <div className="animate-fade-in">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-8 h-8 rounded-lg bg-ase-gold/10 border border-ase-gold/20 flex items-center justify-center">
            <SettingsIcon className="w-4 h-4 text-ase-gold" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Settings</h1>
        </div>
        <p className="text-sm text-ase-muted ml-11">
          Customize your flow experience
        </p>
      </div>

      {/* Error banner */}
      {error && (
        <div className="flex items-center gap-3 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
          <button
            type="button"
            onClick={clearError}
            className="ml-auto text-red-400/60 hover:text-red-400 transition-colors"
          >
            Dismiss
          </button>
        </div>
      )}

      {effective && (
        <div className="space-y-6">
          {/* ── 1. Timer Durations ──────────────────────────────────────── */}
          <Card icon={Clock} title="Timer Durations">
            <SettingRow label="Deep Work" description="Single continuous focus block">
              <NumberInput
                value={effective.deep_work_duration}
                onChange={(v) => patch("deep_work_duration", v)}
                min={10}
                max={240}
                suffix="min"
              />
            </SettingRow>
            <SettingRow label="Pomodoro Focus" description="Core focus interval">
              <NumberInput
                value={effective.focusTime}
                onChange={(v) => patch("focusTime", v)}
                min={5}
                max={90}
                suffix="min"
              />
            </SettingRow>
            <SettingRow label="Short Break" description="Brief rest between pomodoros">
              <NumberInput
                value={effective.shortBreak}
                onChange={(v) => patch("shortBreak", v)}
                min={1}
                max={30}
                suffix="min"
              />
            </SettingRow>
            <SettingRow label="Long Break" description="Extended rest after 4 cycles">
              <NumberInput
                value={effective.longBreak}
                onChange={(v) => patch("longBreak", v)}
                min={5}
                max={60}
                suffix="min"
              />
            </SettingRow>
            <SettingRow label="Sprint Duration" description="Intense short burst mode">
              <NumberInput
                value={effective.sprint_duration}
                onChange={(v) => patch("sprint_duration", v)}
                min={10}
                max={120}
                suffix="min"
              />
            </SettingRow>
            <SettingRow
              label="Free Flow Mode"
              description="Untimed open-ended sessions with no forced breaks"
            >
              <Toggle
                checked={effective.free_flow_enabled}
                onChange={(v) => patch("free_flow_enabled", v)}
              />
            </SettingRow>
          </Card>

          {/* ── 2. Appearance ───────────────────────────────────────────── */}
          <Card icon={Palette} title="Appearance">
            <ThemePicker
              value={effective.theme}
              onChange={(v) => patch("theme", v)}
            />
          </Card>

          {/* ── 3. Music Preferences ────────────────────────────────────── */}
          <Card icon={Music} title="Music Preferences">
            <p className="text-xs text-ase-muted pb-2">
              Default YouTube playlist URL per focus mode. Leave blank to use the built-in default.
            </p>
            {FLOW_MODES.map(({ key, label }) => (
              <PlaylistRow
                key={key}
                mode={key}
                label={label}
                url={effective.youtube_default_playlists?.[key] ?? ""}
                onChange={(url) => patchPlaylist(key, url)}
              />
            ))}
          </Card>

          {/* ── 4. Energy & Flow ────────────────────────────────────────── */}
          <Card icon={Zap} title="Energy & Flow">
            <SettingRow
              label="Energy Tracking"
              description="Log energy level before and after each session"
            >
              <Toggle
                checked={effective.energy_tracking_enabled}
                onChange={(v) => patch("energy_tracking_enabled", v)}
              />
            </SettingRow>
            <SettingRow
              label="Auto Mode Selection"
              description="Detect the best flow mode from task labels automatically"
            >
              <Toggle
                checked={effective.auto_mode_selection}
                onChange={(v) => patch("auto_mode_selection", v)}
              />
            </SettingRow>
          </Card>

          {/* ── 5. Profile & Social ──────────────────────────────────────── */}
          <Card icon={Users} title="Profile & Social">
            <SettingRow
              label="Public Profile"
              description="Appear on the community leaderboard"
            >
              <Toggle
                checked={effective.profile_public}
                onChange={(v) => patch("profile_public", v)}
              />
            </SettingRow>
            <div className="py-3 flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-white">Streak Freeze Days</p>
                <p className="text-xs text-ase-muted mt-0.5">
                  Automatic freeze days protect your streak when you miss a day
                </p>
              </div>
              <span className="text-sm font-semibold text-ase-gold tabular-nums">
                {(settings as (UserSettings & { streak_freeze_days_remaining?: number }) | null)
                  ?.streak_freeze_days_remaining ?? 3}{" "}
                remaining
              </span>
            </div>
          </Card>

          {/* ── 6. Task Sources ──────────────────────────────────────────── */}
          <Card icon={Database} title="Task Sources">
            <SourceBadge label="Local (Ase)" enabled={true} />
            <SourceBadge label="Plane" enabled={false} />
            <SourceBadge label="GitHub Issues" enabled={false} />
            <div className="pt-3 pb-1">
              <p className="text-xs text-ase-muted">
                Configure external task sources via the API. See the{" "}
                <code className="text-ase-gold/80 text-[11px] font-mono bg-ase-gold/5 px-1 rounded">
                  /api/v1/task-sources/
                </code>{" "}
                endpoint.
              </p>
            </div>
          </Card>

          {/* ── Save bar ─────────────────────────────────────────────────── */}
          <div className="flex items-center justify-between pt-2">
            {showSaved ? (
              <span className="flex items-center gap-1.5 text-sm text-green-400">
                <Check className="w-4 h-4" />
                Settings saved
              </span>
            ) : (
              <span className="text-xs text-ase-muted">
                {hasDraft ? "You have unsaved changes" : "All changes saved"}
              </span>
            )}
            <button
              type="button"
              onClick={handleSave}
              disabled={isSaving || !hasDraft}
              className={[
                "flex items-center gap-2 rounded-lg px-6 py-2.5 text-sm font-medium transition-all duration-150",
                hasDraft && !isSaving
                  ? "bg-ase-gold text-black hover:bg-ase-gold/90 shadow-md"
                  : "bg-ase-gold/30 text-black/50 cursor-not-allowed",
              ].join(" ")}
            >
              {isSaving && <Loader2 className="w-4 h-4 animate-spin" />}
              {isSaving ? "Saving…" : "Save Changes"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
