import { useEffect } from "react";
import { useEnergyStore } from "../../hooks/useEnergy";
import { Zap } from "lucide-react";

const DAYS_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function formatHour(h: number): string {
  if (h === 0) return "12:00 AM";
  if (h === 12) return "12:00 PM";
  return h < 12 ? `${h}:00 AM` : `${h - 12}:00 PM`;
}

function confidenceLabel(confidence: number): string {
  if (confidence >= 0.8) return "High";
  if (confidence >= 0.5) return "Medium";
  return "Low";
}

function confidenceColor(confidence: number): string {
  if (confidence >= 0.8) return "text-ase-gold";
  if (confidence >= 0.5) return "text-amber-400";
  return "text-ase-muted";
}

export function EnergyPrediction() {
  const prediction = useEnergyStore((s) => s.prediction);
  const fetchPrediction = useEnergyStore((s) => s.fetchPrediction);

  useEffect(() => {
    const now = new Date();
    // dayOfWeek: JS getDay() = 0=Sun, backend expects 0=Mon
    const jsDow = now.getDay();
    const dayOfWeek = jsDow === 0 ? 6 : jsDow - 1;
    fetchPrediction(now.getHours(), dayOfWeek);
  }, [fetchPrediction]);

  if (!prediction) return null;

  const { hour, dayOfWeek, predictedLevel, confidence } = prediction;
  const dayName = DAYS_SHORT[dayOfWeek] ?? "—";
  const confLabel = confidenceLabel(confidence);
  const confColor = confidenceColor(confidence);

  return (
    <div className="flex items-start gap-3">
      <div className="w-8 h-8 rounded-lg bg-ase-gold/10 border border-ase-gold/20 flex items-center justify-center flex-shrink-0">
        <Zap className="w-4 h-4 text-ase-gold" />
      </div>
      <div className="flex flex-col gap-0.5">
        <p className="text-xs font-semibold text-ase-gold uppercase tracking-wider">
          Peak Energy Forecast
        </p>
        <p className="text-xs text-ase-muted leading-relaxed">
          Best focus window:{" "}
          <span className="text-white font-medium">
            {dayName} at {formatHour(hour)}
          </span>{" "}
          — predicted level{" "}
          <span className="text-ase-gold font-medium">
            {predictedLevel.toFixed(1)}/5
          </span>
        </p>
        <p className={`text-[10px] ${confColor}`}>
          Confidence: {confLabel} ({Math.round(confidence * 100)}%)
        </p>
      </div>
    </div>
  );
}
