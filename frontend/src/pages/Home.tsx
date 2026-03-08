import { useEffect } from "react";
import { FlowTimer } from "../components/Timer/FlowTimer";

export function Home() {
  // Request notification permission on mount
  useEffect(() => {
    if ("Notification" in window && Notification.permission === "default") {
      Notification.requestPermission();
    }
  }, []);

  return (
    <div className="max-w-2xl mx-auto text-center py-12">
      <h2 className="text-4xl font-bold text-ase-gold mb-2">Ase</h2>
      <p className="text-ase-muted text-sm mb-12">
        The power to make things happen.
      </p>

      <FlowTimer />
    </div>
  );
}
