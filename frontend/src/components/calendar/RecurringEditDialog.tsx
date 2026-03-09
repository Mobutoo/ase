import { Repeat, AlertCircle } from "lucide-react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type RecurringEditScope = 'this' | 'following' | 'all';

interface RecurringEditDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (scope: RecurringEditScope) => void;
  action?: 'edit' | 'delete';
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function RecurringEditDialog({
  isOpen,
  onClose,
  onConfirm,
  action = 'edit',
}: RecurringEditDialogProps) {
  if (!isOpen) return null;

  const verb = action === 'delete' ? 'Delete' : 'Edit';

  const options: { value: RecurringEditScope; label: string; description: string }[] = [
    {
      value: 'this',
      label: 'This event',
      description: 'Only this occurrence will be affected',
    },
    {
      value: 'following',
      label: 'This and following events',
      description: 'This and all future occurrences will be affected',
    },
    {
      value: 'all',
      label: 'All events',
      description: 'Every occurrence of this repeating event will be affected',
    },
  ];

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={handleBackdropClick}
    >
      <div className="bg-ase-surface border border-ase-border rounded-2xl w-full max-w-sm shadow-2xl animate-scale-in">
        {/* Header */}
        <div className="flex items-center gap-2.5 px-5 pt-5 pb-4 border-b border-ase-border">
          <div className="w-8 h-8 rounded-lg bg-ase-gold/10 border border-ase-gold/20 flex items-center justify-center flex-shrink-0">
            <Repeat className="w-4 h-4 text-ase-gold" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-white">{verb} recurring event</h2>
            <p className="text-xs text-ase-subtle mt-0.5">Choose which occurrences to {verb.toLowerCase()}</p>
          </div>
        </div>

        {/* Scope options */}
        <div className="p-4 flex flex-col gap-2">
          {options.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => onConfirm(opt.value)}
              className={[
                "group w-full text-left rounded-xl border px-4 py-3 transition-all duration-150",
                "border-ase-border hover:border-ase-gold/40 hover:bg-ase-surface-2",
                action === 'delete' ? "hover:border-red-500/40" : "hover:border-ase-gold/40",
              ].join(" ")}
            >
              <p className={[
                "text-sm font-medium transition-colors",
                action === 'delete'
                  ? "text-ase-text group-hover:text-red-400"
                  : "text-ase-text group-hover:text-ase-gold",
              ].join(" ")}>
                {opt.label}
              </p>
              <p className="text-xs text-ase-subtle mt-0.5">{opt.description}</p>
            </button>
          ))}
        </div>

        {/* Warning for 'delete all' */}
        {action === 'delete' && (
          <div className="mx-4 mb-4 flex items-start gap-2 rounded-lg bg-red-500/10 border border-red-500/20 px-3 py-2">
            <AlertCircle className="w-3.5 h-3.5 text-red-400 flex-shrink-0 mt-0.5" />
            <p className="text-[11px] text-red-400/90 leading-relaxed">
              Deleting all occurrences cannot be undone.
            </p>
          </div>
        )}

        {/* Cancel */}
        <div className="px-4 pb-5">
          <button
            type="button"
            onClick={onClose}
            className="w-full py-2.5 rounded-xl border border-ase-border text-sm text-ase-muted hover:text-white hover:border-ase-border-2 transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
