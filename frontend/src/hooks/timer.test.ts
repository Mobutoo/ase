import { beforeEach, describe, expect, it, vi } from "vitest";
import { useTimerStore } from "./useTimer";
import { sessions } from "../api/client";
import type { Session } from "../types";

vi.mock("../api/client", () => ({ sessions: { create: vi.fn(), cancel: vi.fn(), complete: vi.fn() } }));
vi.mock("./useSound", () => ({ playStartSound: vi.fn(), playCompleteSound: vi.fn(), playBreakOverSound: vi.fn() }));

const postMessage = vi.fn();
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => { resolve = done; });
  return { promise, resolve };
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.stubGlobal("Notification", undefined);
  vi.mocked(sessions.create).mockResolvedValue({ id: 1 } as Session);
  vi.mocked(sessions.cancel).mockResolvedValue({} as Session);
  vi.mocked(sessions.complete).mockResolvedValue({} as Session);
  useTimerStore.setState({
    mode: "pomodoro", phase: "idle", status: "idle", remainingMs: 1500000,
    elapsedMs: 0, totalDurationMs: 1500000, pomodoroCount: 0, activeSessionId: null,
    energyBefore: null, _worker: { postMessage } as unknown as Worker,
    _workerRunId: 0, _pendingSession: null,
  });
});

describe("timer session lifecycle", () => {
  it("starts immediately and ignores duplicate starts while API creation is pending", async () => {
    const pending = deferred<Session>();
    vi.mocked(sessions.create).mockReturnValue(pending.promise);
    const first = useTimerStore.getState().start();
    await useTimerStore.getState().start();
    expect(useTimerStore.getState().status).toBe("running");
    expect(sessions.create).toHaveBeenCalledTimes(1);
    expect(postMessage).toHaveBeenCalledWith(expect.objectContaining({ type: "start" }));
    pending.resolve({ id: 3 } as Session);
    await first;
    expect(useTimerStore.getState().activeSessionId).toBe(3);
  });

  it("cancels a session created after stop without resetting a newer timer", async () => {
    const pending = deferred<Session>();
    vi.mocked(sessions.create).mockReturnValueOnce(pending.promise);
    const first = useTimerStore.getState().start();
    const stopping = useTimerStore.getState().stop();
    await useTimerStore.getState().start();
    pending.resolve({ id: 9 } as Session);
    await Promise.all([first, stopping]);
    expect(sessions.cancel).toHaveBeenCalledWith(9);
    expect(useTimerStore.getState().phase).toBe("focus");
    expect(useTimerStore.getState().activeSessionId).toBe(1);
  });

  it("starts a break without waiting for completion and ignores stale worker replies", async () => {
    const pending = deferred<Session>();
    vi.mocked(sessions.complete).mockReturnValue(pending.promise);
    await useTimerStore.getState().start();
    const oldRun = useTimerStore.getState()._workerRunId;
    useTimerStore.getState()._onWorkerMessage({ type: "complete", runId: oldRun });
    expect(useTimerStore.getState().phase).toBe("short_break");
    useTimerStore.getState()._onWorkerMessage({ type: "stopped", runId: oldRun });
    useTimerStore.getState()._onWorkerMessage({ type: "complete", runId: oldRun });
    expect(useTimerStore.getState().phase).toBe("short_break");
    expect(useTimerStore.getState().pomodoroCount).toBe(1);
    expect(sessions.complete).toHaveBeenCalledTimes(1);
    await useTimerStore.getState().stop();
    await useTimerStore.getState().start();
    pending.resolve({ id: 1 } as Session);
    await pending.promise;
    expect(useTimerStore.getState().phase).toBe("focus");
  });

  it("completes a pending session once and uses elapsed free flow time for its break", async () => {
    const pending = deferred<Session>();
    vi.mocked(sessions.create).mockReturnValue(pending.promise);
    useTimerStore.getState().setMode("free_flow");
    const starting = useTimerStore.getState().start();
    useTimerStore.setState({ elapsedMs: 10 * 60000 });
    const completing = useTimerStore.getState().complete();
    await useTimerStore.getState().complete();
    expect(useTimerStore.getState().remainingMs).toBe(2 * 60000);
    expect(useTimerStore.getState().phase).toBe("short_break");
    pending.resolve({ id: 4 } as Session);
    await Promise.all([starting, completing]);
    expect(sessions.complete).toHaveBeenCalledTimes(1);
    expect(sessions.complete).toHaveBeenCalledWith(4, { energyAfter: undefined, notes: undefined });
  });

  it("keeps idle when pause/resume are called without a session", () => {
    useTimerStore.getState().pause();
    useTimerStore.getState().resume();
    expect(useTimerStore.getState().status).toBe("idle");
    expect(postMessage).not.toHaveBeenCalled();
  });
});
