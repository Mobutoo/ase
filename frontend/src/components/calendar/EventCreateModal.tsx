import { useState } from "react";
import {
  CalendarDays,
  Clock,
  MapPin,
  Repeat,
  Users,
  Bell,
  Eye,
  X,
  Loader2,
} from "lucide-react";
import type { CalendarEvent, EventReminder } from "../../types/calendar";
import type { CircleMember } from "../../types/circle";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function toLocalDatetime(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}`
  );
}

function roundUpToNext15(date: Date): Date {
  const ms = 15 * 60 * 1000;
  return new Date(Math.ceil(date.getTime() / ms) * ms);
}

const DEFAULT_REMINDER: EventReminder = { id: "r1", offsetMinutes: 15, channel: "push" };

// ---------------------------------------------------------------------------
// Initial state factory
// ---------------------------------------------------------------------------

function buildInitialForm(anchor?: string): Partial<CalendarEvent> {
  const start = roundUpToNext15(anchor ? new Date(anchor + "T09:00:00") : new Date());
  const end = new Date(start.getTime() + 60 * 60 * 1000);
  return {
    title: "",
    description: "",
    location: "",
    startAt: start.toISOString(),
    endAt: end.toISOString(),
    allDay: false,
    eventType: "event",
    displayMode: "normal",
    visibility: "family",
    members: [],
    reminders: [DEFAULT_REMINDER],
  };
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface FieldLabelProps { label: string; icon: React.ComponentType<{ className?: string }> }

function FieldLabel({ label, icon: Icon }: FieldLabelProps) {
  return (
    <div className="flex items-center gap-1.5 mb-1">
      <Icon className="w-3.5 h-3.5 text-ase-muted" />
      <span className="text-xs font-medium text-ase-subtle">{label}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface EventCreateModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (payload: Partial<CalendarEvent>) => Promise<void>;
  initialDate?: string; // YYYY-MM-DD
  availableMembers?: CircleMember[];
  isSaving?: boolean;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function EventCreateModal({
  isOpen,
  onClose,
  onSave,
  initialDate,
  availableMembers = [],
  isSaving = false,
}: EventCreateModalProps) {
  const [form, setForm] = useState<Partial<CalendarEvent>>(() =>
    buildInitialForm(initialDate)
  );

  if (!isOpen) return null;

  const patch = <K extends keyof CalendarEvent>(key: K, value: CalendarEvent[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title?.trim()) return;
    await onSave(form);
    setForm(buildInitialForm(initialDate));
    onClose();
  };

  const handleBackdrop = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) onClose();
  };

  const toggleMember = (member: CircleMember) => {
    const current = form.members ?? [];
    const exists = current.some((m) => m.id === member.id);
    const updated = exists
      ? current.filter((m) => m.id !== member.id)
      : [...current, member];
    patch("members", updated);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={handleBackdrop}
    >
      <div className="bg-ase-surface border border-ase-border rounded-2xl w-full max-w-lg shadow-2xl animate-scale-in max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-5 pt-5 pb-4 border-b border-ase-border">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-ase-gold/10 border border-ase-gold/20 flex items-center justify-center">
              <CalendarDays className="w-4 h-4 text-ase-gold" />
            </div>
            <h2 className="text-sm font-semibold text-white">New event</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="w-7 h-7 flex items-center justify-center rounded-lg text-ase-subtle hover:text-white hover:bg-ase-surface-2 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="px-5 py-4 flex flex-col gap-4">
          {/* Title */}
          <div>
            <label className="text-xs font-medium text-ase-subtle block mb-1">
              Title <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={form.title ?? ""}
              onChange={(e) => patch("title", e.target.value)}
              placeholder="What's happening?"
              required
              className="w-full h-10 rounded-xl border border-ase-border bg-ase-bg px-3 text-sm text-white placeholder:text-ase-subtle focus:outline-none focus:border-ase-gold/50"
            />
          </div>

          {/* All-day toggle + datetime */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <FieldLabel label="Date & Time" icon={Clock} />
              <label className="flex items-center gap-2 cursor-pointer">
                <span className="text-xs text-ase-subtle">All day</span>
                <button
                  type="button"
                  role="switch"
                  aria-checked={form.allDay}
                  onClick={() => patch("allDay", !form.allDay)}
                  className={[
                    "relative inline-flex h-5 w-10 rounded-full transition-colors duration-200",
                    form.allDay ? "bg-ase-gold" : "bg-zinc-700",
                  ].join(" ")}
                >
                  <span
                    className={[
                      "inline-block h-4 w-4 transform rounded-full bg-white shadow mt-0.5 transition-transform duration-200",
                      form.allDay ? "translate-x-5" : "translate-x-0.5",
                    ].join(" ")}
                  />
                </button>
              </label>
            </div>

            {form.allDay ? (
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="date"
                  value={form.startAt ? form.startAt.slice(0, 10) : ""}
                  onChange={(e) => patch("startAt", e.target.value + "T00:00:00.000Z")}
                  className="h-9 w-full rounded-lg border border-ase-border bg-ase-bg px-3 text-sm text-white focus:outline-none focus:border-ase-gold/50"
                />
                <input
                  type="date"
                  value={form.endAt ? form.endAt.slice(0, 10) : ""}
                  onChange={(e) => patch("endAt", e.target.value + "T23:59:59.000Z")}
                  className="h-9 w-full rounded-lg border border-ase-border bg-ase-bg px-3 text-sm text-white focus:outline-none focus:border-ase-gold/50"
                />
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="datetime-local"
                  value={form.startAt ? toLocalDatetime(form.startAt) : ""}
                  onChange={(e) => patch("startAt", new Date(e.target.value).toISOString())}
                  className="h-9 w-full rounded-lg border border-ase-border bg-ase-bg px-3 text-sm text-white focus:outline-none focus:border-ase-gold/50"
                />
                <input
                  type="datetime-local"
                  value={form.endAt ? toLocalDatetime(form.endAt) : ""}
                  onChange={(e) => patch("endAt", new Date(e.target.value).toISOString())}
                  className="h-9 w-full rounded-lg border border-ase-border bg-ase-bg px-3 text-sm text-white focus:outline-none focus:border-ase-gold/50"
                />
              </div>
            )}
          </div>

          {/* Location */}
          <div>
            <FieldLabel label="Location" icon={MapPin} />
            <input
              type="text"
              value={form.location ?? ""}
              onChange={(e) => patch("location", e.target.value)}
              placeholder="Add location (optional)"
              className="w-full h-9 rounded-lg border border-ase-border bg-ase-bg px-3 text-sm text-white placeholder:text-ase-subtle focus:outline-none focus:border-ase-gold/50"
            />
          </div>

          {/* Recurrence + Visibility row */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <FieldLabel label="Recurrence" icon={Repeat} />
              <select
                value={form.recurrenceRule ?? ""}
                onChange={(e) => patch("recurrenceRule", e.target.value || undefined)}
                className="w-full h-9 rounded-lg border border-ase-border bg-ase-bg px-3 text-sm text-white focus:outline-none focus:border-ase-gold/50"
              >
                <option value="">Does not repeat</option>
                <option value="FREQ=DAILY">Daily</option>
                <option value="FREQ=WEEKLY">Weekly</option>
                <option value="FREQ=MONTHLY">Monthly</option>
                <option value="FREQ=YEARLY">Yearly</option>
                <option value="FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR">Weekdays</option>
              </select>
            </div>
            <div>
              <FieldLabel label="Visibility" icon={Eye} />
              <select
                value={form.visibility ?? "family"}
                onChange={(e) => patch("visibility", e.target.value as CalendarEvent["visibility"])}
                className="w-full h-9 rounded-lg border border-ase-border bg-ase-bg px-3 text-sm text-white focus:outline-none focus:border-ase-gold/50"
              >
                <option value="family">Circle</option>
                <option value="adults_only">Adults only</option>
                <option value="private">Private</option>
              </select>
            </div>
          </div>

          {/* Members */}
          {availableMembers.length > 0 && (
            <div>
              <FieldLabel label="Invite members" icon={Users} />
              <div className="flex flex-wrap gap-1.5">
                {availableMembers.map((member) => {
                  const selected = (form.members ?? []).some((m) => m.id === member.id);
                  return (
                    <button
                      key={member.id}
                      type="button"
                      onClick={() => toggleMember(member)}
                      className={[
                        "flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium border transition-all duration-150",
                        selected
                          ? "bg-ase-gold/20 border-ase-gold/40 text-ase-gold"
                          : "bg-ase-surface-2 border-ase-border text-ase-muted hover:border-ase-border-2",
                      ].join(" ")}
                    >
                      <span
                        className="w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold"
                        style={{ backgroundColor: member.avatarColor + "40", color: member.avatarColor }}
                      >
                        {member.avatarEmoji || member.displayName[0]?.toUpperCase()}
                      </span>
                      {member.displayName}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Reminder */}
          <div>
            <FieldLabel label="Reminder" icon={Bell} />
            <select
              value={form.reminders?.[0]?.offsetMinutes ?? 15}
              onChange={(e) =>
                patch("reminders", [
                  { id: "r1", offsetMinutes: Number(e.target.value), channel: "push" },
                ])
              }
              className="w-full h-9 rounded-lg border border-ase-border bg-ase-bg px-3 text-sm text-white focus:outline-none focus:border-ase-gold/50"
            >
              <option value={0}>At time of event</option>
              <option value={5}>5 minutes before</option>
              <option value={15}>15 minutes before</option>
              <option value={30}>30 minutes before</option>
              <option value={60}>1 hour before</option>
              <option value={120}>2 hours before</option>
              <option value={1440}>1 day before</option>
            </select>
          </div>

          {/* Description */}
          <div>
            <label className="text-xs font-medium text-ase-subtle block mb-1">Notes</label>
            <textarea
              value={form.description ?? ""}
              onChange={(e) => patch("description", e.target.value)}
              placeholder="Add notes or description..."
              rows={2}
              className="w-full rounded-xl border border-ase-border bg-ase-bg px-3 py-2 text-sm text-white placeholder:text-ase-subtle focus:outline-none focus:border-ase-gold/50 resize-none"
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2.5 rounded-xl border border-ase-border text-sm text-ase-muted hover:text-white hover:border-ase-border-2 transition-colors font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSaving || !form.title?.trim()}
              className={[
                "flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl text-sm font-semibold transition-all duration-150",
                form.title?.trim() && !isSaving
                  ? "bg-ase-gold/20 border border-ase-gold/40 text-ase-gold hover:bg-ase-gold/30"
                  : "bg-ase-surface-2 border border-ase-border text-ase-subtle cursor-not-allowed",
              ].join(" ")}
            >
              {isSaving && <Loader2 className="w-4 h-4 animate-spin" />}
              {isSaving ? "Saving…" : "Create event"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
