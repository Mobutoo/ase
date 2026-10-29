import { afterEach, expect, it, vi } from "vitest";
import { playlists } from "./phase2";

const wire = { id: 7, name: "Focus", url: "https://www.youtube.com/watch?v=abcdefghijk", mode: "", isDefault: true };
const json = (body: unknown) => new Response(JSON.stringify(body), { headers: { "Content-Type": "application/json" } });
afterEach(() => vi.unstubAllGlobals());

it("maps API playlist URLs into playable frontend playlists", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json({ count: 1, next: null, previous: null, results: [wire] })));
  const result = await playlists.list();
  expect(result.results[0]).toEqual({ id: "7", name: "Focus", youtubeUrl: wire.url, mode: "custom", isDefault: true, isCustom: true });
});

it("writes URL under the backend field and leaves omitted patch fields untouched", async () => {
  const fetch = vi.fn().mockImplementation(() => Promise.resolve(json(wire)));
  vi.stubGlobal("fetch", fetch);
  await playlists.create({ name: "Focus", youtubeUrl: wire.url, mode: "custom" });
  expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ name: "Focus", url: wire.url, mode: "", source: "youtube" });
  await playlists.update("7", { name: "Renamed" });
  expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual({ name: "Renamed" });
});
