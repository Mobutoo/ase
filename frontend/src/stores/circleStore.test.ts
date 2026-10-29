import { afterEach, expect, it, vi } from "vitest";
import { useCircleStore } from "./circleStore";
import type { Circle, CircleMember } from "../types/circle";

afterEach(() => vi.unstubAllGlobals());

it("uses circle-scoped member role and removal endpoints", async () => {
  useCircleStore.setState({ currentCircle: { id: "12" } as Circle, members: [{ id: "34" } as CircleMember] });
  const fetch = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ id: "34", role: "adult" }), {
    headers: { "Content-Type": "application/json" },
  })).mockResolvedValueOnce(new Response(null, { status: 204 }));
  vi.stubGlobal("fetch", fetch);
  await useCircleStore.getState().updateRole("34", "adult");
  expect(fetch.mock.calls[0][0]).toBe("/api/circles/12/members/34/role/");
  expect(useCircleStore.getState().members[0].role).toBe("adult");
  await useCircleStore.getState().removeMember("34");
  expect(fetch.mock.calls[1][0]).toBe("/api/circles/12/members/34/");
  expect(useCircleStore.getState().members).toEqual([]);
});

it("creates an invitation token without adding a nonexistent member", async () => {
  useCircleStore.setState({ members: [] });
  const invitation = { inviteToken: "signed-token", circleId: 12, circleName: "Family", expiresInSeconds: 3600 };
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(invitation), {
    headers: { "Content-Type": "application/json" },
  }));
  vi.stubGlobal("fetch", fetch);
  const result = await useCircleStore.getState().inviteMember("12", { role: "guest", displayName: "Alex" });
  expect(fetch.mock.calls[0][0]).toBe("/api/circles/12/invite/");
  expect(result).toEqual(invitation);
  expect(useCircleStore.getState().members).toEqual([]);
});
