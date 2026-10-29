/** Timer worker: elapsed wall time stays accurate when a tab is throttled. */
let intervalId: ReturnType<typeof setInterval> | null = null;
let startTime = 0;
let pausedElapsed = 0;
let totalDurationMs = 0;
let paused = false;
let active = false;
let runId = 0;

const TICK_INTERVAL = 250;

function clearTimer() {
  if (intervalId !== null) {
    clearInterval(intervalId);
    intervalId = null;
  }
}

function sendTick() {
  const elapsed = pausedElapsed + Math.max(0, Date.now() - startTime);
  const remaining = Math.max(0, totalDurationMs - elapsed);
  self.postMessage({ type: "tick", remainingMs: remaining, elapsedMs: elapsed, runId });

  // Zero duration means an open-ended Free Flow session.
  if (totalDurationMs > 0 && remaining <= 0) {
    clearTimer();
    active = false;
    self.postMessage({ type: "complete", runId });
  }
}

function run() {
  startTime = Date.now();
  // Install the interval first so an immediate completion can clear it.
  intervalId = setInterval(sendTick, TICK_INTERVAL);
  sendTick();
}

self.onmessage = (e: MessageEvent) => {
  const msg = e.data;
  switch (msg.type) {
    case "start":
      if (!Number.isFinite(msg.durationMs) || msg.durationMs < 0) return;
      clearTimer();
      totalDurationMs = msg.durationMs;
      runId = msg.runId ?? 0;
      pausedElapsed = 0;
      paused = false;
      active = true;
      run();
      break;
    case "pause":
      if (active && !paused) {
        pausedElapsed += Math.max(0, Date.now() - startTime);
        paused = true;
        clearTimer();
      }
      break;
    case "resume":
      if (active && paused) {
        paused = false;
        run();
      }
      break;
    case "stop":
      clearTimer();
      active = false;
      paused = false;
      pausedElapsed = 0;
      totalDurationMs = 0;
      self.postMessage({ type: "stopped", runId });
      break;
  }
};
