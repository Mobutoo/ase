import { useState } from "react";
import type { EnergyContext } from "../../types";
import { useEnergyStore } from "../../hooks/useEnergy";

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
      <div className="flex flex-col items-center gap-2 py-2">
        <span className="text-4xl">{emoji?.emoji}</span>
        <p className="text-xs text-[#8a8aae]">
          Logged: {emoji?.label}
        </p>
        <button
          onClick={() => {
            setSelected(null);
            setSubmitted(false);
          }}
          className="text-xs text-[#f59e0b]/70 hover:text-[#f59e0b] transition-colors underline underline-offset-2"
        >
          Change
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {label && (
        <p className="text-sm font-medium text-[#c0c0d8] text-center">{label}</p>
      )}

      <div className="flex items-center justify-center gap-2">
        {ENERGY_EMOJIS.map(({ level, emoji, label: emojiLabel }) => (
          <button
            key={level}
            onClick={() => handleSelect(level)}
            disabled={isSubmitting}
            title={emojiLabel}
            className={`
              w-10 h-10 text-2xl rounded-full flex items-center justify-center
              transition-all duration-150 select-none
              disabled:cursor-not-allowed
              ${
                selected === level
                  ? "ring-2 ring-[#f59e0b] ring-offset-2 ring-offset-[#1a1a2e] scale-110"
                  : "hover:scale-110 hover:ring-2 hover:ring-[#f59e0b]/50 hover:ring-offset-1 hover:ring-offset-[#1a1a2e]"
              }
              ${isSubmitting && selected !== level ? "opacity-50" : ""}
            `}
          >
            {emoji}
          </button>
        ))}
      </div>

      <div className="flex justify-between px-1">
        <span className="text-[10px] text-[#6a6a8e]">Exhausted</span>
        <span className="text-[10px] text-[#6a6a8e]">On Fire</span>
      </div>
    </div>
  );
}
