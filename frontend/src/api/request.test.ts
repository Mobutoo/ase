import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, request } from "./request";
import { settings } from "./client";
import { aiSuggestions } from "./ai";

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { "Content-Type": "application/json" },
});

afterEach(() => {
  vi.unstubAllGlobals();
  document.cookie = "csrftoken=; Max-Age=0";
  document.cookie = "othercsrftoken=; Max-Age=0";
});

describe("session HTTP client", () => {
  it("uses the exact CSRF cookie and preserves Headers instances", async () => {
    document.cookie = "othercsrftoken=wrong";
    document.cookie = "csrftoken=real-token";
    const fetch = vi.fn().mockResolvedValue(json({ ok: true }));
    vi.stubGlobal("fetch", fetch);
    await request("/api/test/", { method: "POST", body: "{}", headers: new Headers({ "X-Test": "yes" }) });
    const options = fetch.mock.calls[0][1];
    expect(options.credentials).toBe("same-origin");
    expect(options.headers.get("X-CSRFToken")).toBe("real-token");
    expect(options.headers.get("X-Test")).toBe("yes");
  });

  it("retains multipart boundaries and accepts an empty DELETE response", async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetch);
    expect(await request("/api/test/", { method: "DELETE", body: new FormData() })).toBeUndefined();
    expect(fetch.mock.calls[0][1].headers.has("Content-Type")).toBe(false);
  });

  it("shows validation details but does not expose server diagnostics", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(json({ endAt: ["Must be after start."] }, 400))
      .mockResolvedValueOnce(json({ detail: "private token secret" }, 500)));
    await expect(request("/api/test/")).rejects.toThrow("endAt: Must be after start.");
    await expect(request("/api/test/")).rejects.toEqual(new ApiError("Server error — please try again later", 500));
  });

  it("distinguishes permission failures from missing authentication and HTML responses", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(json({}, 403))
      .mockResolvedValueOnce(new Response("<html>Login</html>", { headers: { "Content-Type": "text/html" } })));
    await expect(request("/api/test/")).rejects.toThrow("permission");
    await expect(request("/api/test/")).rejects.toThrow("Unexpected server response");
  });

  it("preserves the backend camelCase settings and AI contract", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(json({ username: "alice", deepWorkDuration: 90, profilePublic: false }))
      .mockResolvedValueOnce(json([{ id: 1, suggestionType: "daily_plan", createdAt: "2026-10-29T00:00:00Z" }])));
    expect((await settings.get()).deepWorkDuration).toBe(90);
    expect((await aiSuggestions.list())[0].suggestionType).toBe("daily_plan");
  });
});
