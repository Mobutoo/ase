import { useState } from "react";
import { Link } from "react-router-dom";
import { request } from "../api/request";

export function InvitePage() {
  const params = new URLSearchParams(window.location.hash.slice(1));
  const circle = params.get("circle") ?? "";
  const token = params.get("token") ?? "";
  const valid = /^\d+$/.test(circle) && token.length > 0;
  const [busy, setBusy] = useState(false);
  const [joined, setJoined] = useState(false);
  const [error, setError] = useState("");

  const accept = async () => {
    if (busy || !valid) return;
    setBusy(true);
    setError("");
    try {
      await request(`/api/circles/${circle}/accept_invite/`, { method: "POST", body: JSON.stringify({ token }) });
      window.history.replaceState(null, "", "/invite");
      setJoined(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not accept invitation");
    } finally {
      setBusy(false);
    }
  };

  return <section className="p-6 space-y-4 max-w-lg">
    <h1 className="text-xl font-semibold text-white">Circle invitation</h1>
    {joined ? <><p role="status">You joined the circle.</p><Link to="/circle" className="text-ase-gold">Open circles</Link></> :
      !valid ? <p role="alert">This invitation link is incomplete.</p> : <>
        <p className="text-ase-muted">Sign in to your account, then accept this invitation to join the circle.</p>
        <a href="/accounts/login/" target="_blank" rel="noopener noreferrer" className="block text-ase-gold">Sign in (opens a new tab)</a>
        <button disabled={busy} onClick={accept} className="rounded-xl border border-ase-gold/40 bg-ase-gold/10 p-3 text-ase-gold disabled:opacity-50">
          {busy ? "Joining…" : "Accept invitation"}
        </button>
        {error && <p role="alert" className="text-sm text-red-400">{error}</p>}
      </>}
  </section>;
}
