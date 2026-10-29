import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { EventCreateModal } from "./EventCreateModal";

afterEach(cleanup);

describe("event creation form", () => {
  it("keeps the draft open after an API failure", async () => {
    const onSave = vi.fn().mockResolvedValue(false);
    const onClose = vi.fn();
    render(<EventCreateModal isOpen initialDate="2026-10-29" onSave={onSave} onClose={onClose} />);
    fireEvent.change(screen.getByRole("textbox", { name: "Title" }), { target: { value: "Dentist" } });
    fireEvent.click(screen.getByRole("button", { name: "Create event" }));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("not been saved"));
    expect(onClose).not.toHaveBeenCalled();
    expect((screen.getByRole("textbox", { name: "Title" }) as HTMLInputElement).value).toBe("Dentist");
  });

  it("allows clearing dates and validates the interval before submission", async () => {
    const onSave = vi.fn().mockResolvedValue(true);
    render(<EventCreateModal isOpen initialDate="2026-10-29" onSave={onSave} onClose={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Dentist" } });
    fireEvent.change(screen.getByLabelText("Start time"), { target: { value: "" } });
    expect((screen.getByLabelText("Start time") as HTMLInputElement).value).toBe("");
    fireEvent.change(screen.getByLabelText("Start time"), { target: { value: "2026-10-29T12:00" } });
    fireEvent.change(screen.getByLabelText("End time"), { target: { value: "2026-10-29T11:00" } });
    fireEvent.click(screen.getByRole("button", { name: "Create event" }));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("End time"));
    expect(onSave).not.toHaveBeenCalled();
  });
});
