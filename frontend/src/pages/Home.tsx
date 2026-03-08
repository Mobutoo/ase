export function Home() {
  return (
    <div className="max-w-2xl mx-auto text-center py-20">
      <h2 className="text-4xl font-bold text-ase-gold mb-4">Ase</h2>
      <p className="text-ase-muted text-lg mb-2">
        The power to make things happen.
      </p>
      <p className="text-ase-muted/60 text-sm">
        Flow engine &bull; Task bridge &bull; Energy tracking
      </p>

      {/* Timer placeholder */}
      <div className="mt-16 flex flex-col items-center gap-8">
        <div className="w-64 h-64 rounded-full border-4 border-ase-gold/30 flex items-center justify-center">
          <span className="text-5xl font-mono text-ase-gold">25:00</span>
        </div>
        <div className="flex gap-3">
          {["Deep Work", "Pomodoro", "Sprint", "Free Flow"].map((mode) => (
            <button
              key={mode}
              className="px-4 py-2 rounded-lg text-sm bg-ase-surface border border-ase-border text-ase-muted hover:text-ase-gold hover:border-ase-gold/50 transition-colors"
            >
              {mode}
            </button>
          ))}
        </div>
        <button className="px-8 py-3 rounded-xl bg-ase-gold text-ase-bg font-semibold hover:bg-ase-amber transition-colors">
          Start Focus
        </button>
      </div>
    </div>
  );
}
