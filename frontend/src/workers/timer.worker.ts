/**
 * Timer Web Worker — accurate timing that survives browser tab throttling.
 *
 * Messages IN  (from main thread):
 *   { type: "start", durationMs: number }  — start countdown
 *   { type: "pause" }                      — pause
 *   { type: "resume" }                     — resume
 *   { type: "stop" }                       — stop and reset
 *
 * Messages OUT (to main thread):
 *   { type: "tick", remainingMs, elapsedMs }
 *   { type: "complete" }
 *   { type: "stopped" }
 */

let intervalId: ReturnType<typeof setInterval> | null = null;
let startTime = 0;
let pausedElapsed = 0;
let totalDurationMs = 0;

const TICK_INTERVAL = 250; // 4 ticks/sec for smooth UI

function clearTimer() {
  if (intervalId !== null) {
    clearInterval(intervalId);
    intervalId = null;
  }
}

function sendTick() {
  const elapsed = pausedElapsed + (Date.now() - startTime);
  const remaining = Math.max(0, totalDurationMs - elapsed);

  self.postMessage({ type: "tick", remainingMs: remaining, elapsedMs: elapsed });

  if (remaining <= 0) {
    clearTimer();
    self.postMessage({ type: "complete" });
  }
}

self.onmessage = (e: MessageEvent) => {
  const msg = e.data;

  switch (msg.type) {
    case "start":
      clearTimer();
      totalDurationMs = msg.durationMs;
      pausedElapsed = 0;
      startTime = Date.now();
      // Send initial tick immediately
      sendTick();
      intervalId = setInterval(sendTick, TICK_INTERVAL);
      break;

    case "pause":
      if (intervalId !== null) {
        pausedElapsed += Date.now() - startTime;
        clearTimer();
      }
      break;

    case "resume":
      if (intervalId === null && totalDurationMs > 0) {
        startTime = Date.now();
        sendTick();
        intervalId = setInterval(sendTick, TICK_INTERVAL);
      }
      break;

    case "stop":
      clearTimer();
      pausedElapsed = 0;
      totalDurationMs = 0;
      self.postMessage({ type: "stopped" });
      break;
  }
};
