import { Globe } from "lucide-react";

// ---------------------------------------------------------------------------
// SubscriptionBadge — visual indicator for imported iCal events
// ---------------------------------------------------------------------------

interface SubscriptionBadgeProps {
  /** Source name to show in tooltip (e.g. "Doctolib", "Google Calendar") */
  source?: string;
  /** Size variant */
  size?: "sm" | "md";
}

export function SubscriptionBadge({ source, size = "sm" }: SubscriptionBadgeProps) {
  const iconSize = size === "sm" ? "w-3 h-3" : "w-3.5 h-3.5";
  const badgeSize = size === "sm" ? "w-4 h-4" : "w-5 h-5";

  return (
    <span
      className={`${badgeSize} inline-flex items-center justify-center rounded-full bg-zinc-700/60 border border-zinc-600/40 flex-shrink-0`}
      title={source ? `Imported from ${source}` : "Imported event"}
    >
      <Globe className={`${iconSize} text-zinc-400`} />
    </span>
  );
}
