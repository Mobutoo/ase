import type { CalendarEvent } from "../../types/calendar";
import { AlertTriangle, Clock, Check, X } from "lucide-react";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatRange(startIso: string, endIso: string): string {
  const fmt = (iso: string) =>
    new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return `${fmt(startIso)} – ${fmt(endIso)}`;
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface ConflictDialogProps {
  isOpen: boolean;
  incoming: Partial<CalendarEvent> | null;
  conflicts: CalendarEvent[];
  onForce: () => void;
  onCancel: () => void;
  onReschedule?: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ConflictDialog({
  isOpen,
  incoming,
  conflicts,
  onForce,
  onCancel,
  onReschedule,
}: ConflictDialogProps) {
  if (!isOpen || !incoming) return null;

  const handleBackdrop = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) onCancel();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={handleBackdrop}
    >
      <div className="bg-ase-surface border border-ase-border rounded-2xl w-full max-w-md shadow-2xl animate-scale-in">
        {/* Header */}
        <div className="flex items-center gap-2.5 px-5 pt-5 pb-4 border-b border-ase-border">
          <div className="w-8 h-8 rounded-lg bg-orange-500/10 border border-orange-500/20 flex items-center justify-center flex-shrink-0">
            <AlertTriangle className="w-4 h-4 text-orange-400" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-white">Scheduling conflict</h2>
            <p className="text-xs text-ase-subtle mt-0.5">
              {conflicts.length === 1
                ? "1 existing event overlaps"
                : `${conflicts.length} existing events overlap`}
            </p>
          </div>
        </div>

        {/* Incoming event */}
        <div className="px-5 pt-4">
          <p className="text-xs font-medium text-ase-subtle mb-2 uppercase tracking-wider">New event</p>
          <div className="rounded-xl border border-ase-gold/30 bg-ase-gold/5 px-4 py-3">
            <p className="text-sm font-semibold text-white">{incoming.title ?? "Untitled"}</p>
            {incoming.startAt && incoming.endAt && (
              <p className="flex items-center gap-1 text-xs text-ase-muted mt-1">
                <Clock className="w-3 h-3" />
                {formatRange(incoming.startAt, incoming.endAt)}
              </p>
            )}
          </div>
        </div>

        {/* Conflict list */}
        <div className="px-5 pt-3 pb-2">
          <p className="text-xs font-medium text-ase-subtle mb-2 uppercase tracking-wider">Conflicts with</p>
          <div className="flex flex-col gap-1.5 max-h-36 overflow-y-auto">
            {conflicts.map((c) => (
              <div
                key={c.id}
                className="rounded-xl border border-ase-border bg-ase-surface-2 px-3 py-2.5 flex items-center gap-3"
              >
                <div className="w-1.5 h-8 rounded-full bg-orange-400/60 flex-shrink-0" />
                <div className="min-w-0">
                  <p className="text-sm font-medium text-white truncate">{c.title}</p>
                  <p className="flex items-center gap-1 text-xs text-ase-subtle mt-0.5">
                    <Clock className="w-3 h-3" />
                    {formatRange(c.startAt, c.endAt)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="px-5 pb-5 pt-3 flex flex-col gap-2">
          <button
            type="button"
            onClick={onForce}
            className="flex items-center justify-center gap-1.5 w-full py-2.5 rounded-xl bg-ase-gold/20 border border-ase-gold/40 text-sm font-medium text-ase-gold hover:bg-ase-gold/30 transition-colors"
          >
            <Check className="w-4 h-4" />
            Add anyway
          </button>
          {onReschedule && (
            <button
              type="button"
              onClick={onReschedule}
              className="flex items-center justify-center gap-1.5 w-full py-2.5 rounded-xl border border-ase-border text-sm text-ase-muted hover:text-white hover:border-ase-border-2 transition-colors"
            >
              Reschedule
            </button>
          )}
          <button
            type="button"
            onClick={onCancel}
            className="flex items-center justify-center gap-1.5 w-full py-2.5 rounded-xl border border-ase-border text-sm text-ase-subtle hover:text-ase-muted transition-colors"
          >
            <X className="w-4 h-4" />
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
