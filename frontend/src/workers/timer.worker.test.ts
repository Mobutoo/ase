import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const postMessage = vi.fn();
let worker: { postMessage: typeof postMessage; onmessage: (event: { data: unknown }) => void };
const command = (data: unknown) => worker.onmessage({ data });

beforeEach(async () => {
  vi.resetModules();
  vi.useFakeTimers();
  vi.setSystemTime(0);
  postMessage.mockReset();
  worker = { postMessage, onmessage: () => {} };
  vi.stubGlobal("self", worker);
  await import("./timer.worker");
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("timer worker", () => {
  it("counts elapsed time indefinitely in free flow and excludes paused time", () => {
    command({ type: "start", durationMs: 0, runId: 1 });
    vi.advanceTimersByTime(2000);
    expect(postMessage).toHaveBeenLastCalledWith({ type: "tick", elapsedMs: 2000, remainingMs: 0, runId: 1 });
    command({ type: "pause" });
    vi.advanceTimersByTime(10000);
    command({ type: "resume" });
    vi.advanceTimersByTime(1000);
    expect(postMessage).toHaveBeenLastCalledWith({ type: "tick", elapsedMs: 3000, remainingMs: 0, runId: 1 });
    expect(postMessage.mock.calls.some(([message]) => message.type === "complete")).toBe(false);
  });

  it("emits one completion and cannot resume an expired timer", () => {
    command({ type: "start", durationMs: 1000, runId: 3 });
    vi.advanceTimersByTime(5000);
    command({ type: "resume" });
    vi.advanceTimersByTime(5000);
    expect(postMessage.mock.calls.filter(([message]) => message.type === "complete")).toEqual([[{ type: "complete", runId: 3 }]]);
    expect(vi.getTimerCount()).toBe(0);
  });

  it("does not leave a repeating interval when a resumed countdown already elapsed", () => {
    command({ type: "start", durationMs: 100, runId: 2 });
    vi.setSystemTime(200);
    command({ type: "pause" });
    command({ type: "resume" });
    vi.advanceTimersByTime(5000);
    expect(postMessage.mock.calls.filter(([message]) => message.type === "complete")).toHaveLength(1);
    expect(vi.getTimerCount()).toBe(0);
  });
});
