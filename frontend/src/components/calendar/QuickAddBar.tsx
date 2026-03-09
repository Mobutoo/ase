import { useState, useRef, useEffect } from "react";
import { Sparkles, Plus, Loader2 } from "lucide-react";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface QuickAddBarProps {
  onSubmit: (text: string) => Promise<void>;
  placeholder?: string;
  isLoading?: boolean;
}

// ---------------------------------------------------------------------------
// NLP hint examples shown in placeholder rotation
// ---------------------------------------------------------------------------

const HINTS = [
  'Try "Meeting with Alex tomorrow at 3pm"',
  'Try "Dentist Friday at 10am, 1 hour"',
  'Try "Team standup every weekday at 9"',
  'Try "Pick up kids at 5pm, remind me 30min before"',
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function QuickAddBar({ onSubmit, placeholder, isLoading = false }: QuickAddBarProps) {
  const [text, setText] = useState("");
  const [hintIdx, setHintIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Rotate hints every 4 seconds
  useEffect(() => {
    const id = setInterval(() => setHintIdx((i) => (i + 1) % HINTS.length), 4000);
    return () => clearInterval(id);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || isLoading) return;
    await onSubmit(trimmed);
    setText("");
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSubmit(e as unknown as React.FormEvent);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2">
      {/* AI spark icon */}
      <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-ase-gold/10 border border-ase-gold/20 flex items-center justify-center">
        <Sparkles className="w-4 h-4 text-ase-gold" />
      </div>

      {/* Input */}
      <div className="relative flex-1">
        <input
          ref={inputRef}
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          placeholder={placeholder ?? HINTS[hintIdx]}
          className={[
            "w-full h-10 rounded-xl border bg-ase-surface px-4 text-sm text-white",
            "placeholder:text-ase-subtle transition-all duration-200",
            "focus:outline-none focus:border-ase-gold/50 focus:ring-2 focus:ring-ase-gold/10",
            isLoading ? "border-ase-border opacity-60 cursor-not-allowed" : "border-ase-border hover:border-ase-border-2",
          ].join(" ")}
        />
        {/* Subtle gradient overlay on right when text is present */}
        {text && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-ase-subtle">
            Enter
          </div>
        )}
      </div>

      {/* Submit button */}
      <button
        type="submit"
        disabled={isLoading || !text.trim()}
        className={[
          "flex-shrink-0 h-10 px-4 rounded-xl border text-sm font-medium",
          "flex items-center gap-1.5 transition-all duration-150",
          text.trim() && !isLoading
            ? "bg-ase-gold/20 border-ase-gold/40 text-ase-gold hover:bg-ase-gold/30"
            : "bg-transparent border-ase-border text-ase-subtle cursor-not-allowed opacity-50",
        ].join(" ")}
      >
        {isLoading ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <Plus className="w-4 h-4" />
        )}
        Add
      </button>
    </form>
  );
}
