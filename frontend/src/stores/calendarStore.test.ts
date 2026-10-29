import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useCalendarStore } from "./calendarStore";
import type { Calendar } from "../types/calendar";

beforeEach(() => useCalendarStore.setState({ events: [], calendars: [{ id: "first" } as Calendar], error: null }));
afterEach(() => vi.unstubAllGlobals());

describe("calendar writes", () => {
  it("does not move an event to the first calendar when editing its title", async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: "event", title: "New" }), {
      headers: { "Content-Type": "application/json" },
    }));
    vi.stubGlobal("fetch", fetch);
    await useCalendarStore.getState().updateEvent("event", { title: "New" });
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ title: "New" });
  });

  it("returns failure without adding an event when the API rejects a creation", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ title: ["Required"] }), {
      status: 400, headers: { "Content-Type": "application/json" },
    })));
    expect(await useCalendarStore.getState().createEvent({ title: "" })).toBeNull();
    expect(useCalendarStore.getState().events).toEqual([]);
    expect(useCalendarStore.getState().error).toContain("Required");
  });
});
