import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { InviteForm } from "./InviteForm";
import { InvitePage } from "../../pages/InvitePage";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); window.history.replaceState(null, "", "/"); });

it("generates a copyable invitation link with only valid preset roles", async () => {
  const onInvite = vi.fn().mockResolvedValue({ inviteToken: "signed:token", circleId: 12, circleName: "Family", expiresInSeconds: 3600 });
  render(<InviteForm onInvite={onInvite} preset="family" />);
  expect(screen.queryByRole("option", { name: "member" })).toBeNull();
  fireEvent.change(screen.getByLabelText("Display name"), { target: { value: "Alex" } });
  fireEvent.click(screen.getByRole("button", { name: "Create invitation link" }));
  const input = await screen.findByLabelText("Invitation link") as HTMLInputElement;
  const url = new URL(input.value);
  expect(url.pathname).toBe("/invite");
  expect(url.search).toBe("");
  expect(new URLSearchParams(url.hash.slice(1)).get("token")).toBe("signed:token");
  expect(screen.getByText(/No email is sent automatically/)).toBeTruthy();
});

it("accepts the link only after the recipient confirms, then removes the token", async () => {
  window.history.replaceState(null, "", "/invite#circle=12&token=signed-token");
  const fetch = vi.fn().mockResolvedValue(new Response("{}", { headers: { "Content-Type": "application/json" } }));
  vi.stubGlobal("fetch", fetch);
  render(<MemoryRouter><InvitePage /></MemoryRouter>);
  expect(fetch).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Accept invitation" }));
  await waitFor(() => expect(screen.getByRole("status").textContent).toContain("joined"));
  expect(fetch.mock.calls[0][0]).toBe("/api/circles/12/accept_invite/");
  expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ token: "signed-token" });
  expect(window.location.hash).toBe("");
});
