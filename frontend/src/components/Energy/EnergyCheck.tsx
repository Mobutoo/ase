import { useState } from "react";
import type { EnergyContext } from "../../types";
import { useEnergyStore } from "../../hooks/useEnergy";
import { RefreshCw } from "lucide-react";

interface EnergyCheckProps {
  context?: EnergyContext;
  sessionId?: number;
  onSubmit?: (level: number) => void;
  label?: string;
}

const ENERGY_EMOJIS: { level: number; emoji: string; label: string }[] = [
  { level: 1, emoji: "😫", label: "Exhausted" },
  { level: 2, emoji: "😟", label: "Low" },
  { level: 3, emoji: "😐", label: "Neutral" },
  { level: 4, emoji: "😊", label: "Good" },
  { level: 5, emoji: "🔥", label: "On Fire" },
];

export function EnergyCheck({
  context = "check_in",
  sessionId,
  onSubmit,
  label = "How's your energy?",
}: EnergyCheckProps) {
  const submitReading = useEnergyStore((s) => s.submitReading);
  const isSubmitting = useEnergyStore((s) => s.isSubmitting);
  const lastSubmittedLevel = useEnergyStore((s) => s.lastSubmittedLevel);
  const [selected, setSelected] = useState<number | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const handleSelect = async (level: number) => {
    setSelected(level);
    await submitReading(level, context, sessionId);
    setSubmitted(true);
    onSubmit?.(level);
  };

  if (submitted && lastSubmittedLevel !== null) {
    const emoji = ENERGY_EMOJIS.find((e) => e.level === lastSubmittedLevel);
    return (
      <div className="flex items-center gap-3 py-1">
        <span className="text-3xl">{emoji?.emoji}</span>
        <div>
          <p className="text-xs text-ase-muted">
            Logged: <span className="text-white font-medium">{emoji?.label}</span>
          </p>
          <button
            onClick={() => { setSelected(null); setSubmitted(false); }}
            className="flex items-center gap-1 text-xs text-ase-gold/60 hover:text-ase-gold transition-colors mt-0.5"
          >
            <RefreshCw className="w-3 h-3" />
            Change
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {label && (
        <p className="text-sm font-medium text-ase-muted text-center">{label}</p>
      )}
      <div className="flex items-center justify-center gap-2">
        {ENERGY_EMOJIS.map(({ level, emoji, label: emojiLabel }) => (
          <button
            key={level}
            onClick={() => handleSelect(level)}
            disabled={isSubmitting}
            title={emojiLabel}
            className={`
              w-10 h-10 text-2xl rounded-xl flex items-center justify-center
              transition-all duration-200 select-none
              disabled:cursor-not-allowed
              ${selected === level
                ? "ring-2 ring-ase-gold ring-offset-2 ring-offset-ase-bg scale-110 bg-ase-gold/10"
                : "hover:scale-110 hover:bg-white/5"
              }
              ${isSubmitting && selected !== level ? "opacity-40" : ""}
            `}
          >
            {emoji}
          </button>
        ))}
      </div>
      <div className="flex justify-between px-1">
        <span className="text-[10px] text-ase-subtle">Exhausted</span>
        <span className="text-[10px] text-ase-subtle">On Fire</span>
      </div>
    </div>
  );
}
