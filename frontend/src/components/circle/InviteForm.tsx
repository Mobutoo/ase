import { useState } from "react";
import { UserPlus, Loader2 } from "lucide-react";
import type { CircleInvitation, InviteMemberPayload } from "../../stores/circleStore";
import type { CirclePreset } from "../../types/circle";

const PRESET_ROLES: Record<CirclePreset, string[]> = {
  family: ["guest", "adult", "child", "parent", "admin"],
  colocation: ["guest", "adult", "roommate", "admin"],
  team: ["guest", "adult", "member", "intern", "admin"],
  club: ["guest", "coach", "player", "member", "admin"],
  custom: ["guest", "adult", "child", "parent", "roommate", "member", "intern", "coach", "player", "admin"],
};

interface InviteFormProps {
  onInvite: (payload: InviteMemberPayload) => Promise<CircleInvitation | null>;
  preset: CirclePreset;
  isLoading?: boolean;
}

export function InviteForm({ onInvite, preset, isLoading = false }: InviteFormProps) {
  const [displayName, setDisplayName] = useState("");
  const [role, setRole] = useState("guest");
  const [link, setLink] = useState("");
  const [expiresInHours, setExpiresInHours] = useState(0);
  const [copyStatus, setCopyStatus] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!displayName.trim() || isLoading) return;
    setError("");
    const invitation = await onInvite({ role, displayName: displayName.trim() });
    if (!invitation) {
      setError("Could not create an invitation. Check the error above and try again.");
      return;
    }
    // A fragment keeps the token out of requests for the SPA document.
    const fragment = new URLSearchParams({ circle: String(invitation.circleId), token: invitation.inviteToken });
    setLink(`${window.location.origin}/invite#${fragment}`);
    setExpiresInHours(Math.round(invitation.expiresInSeconds / 3600));
    setCopyStatus("");
  };

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(link);
      setCopyStatus("Link copied");
    } catch {
      setCopyStatus("Select the link and copy it manually");
    }
  };

  return (
    <div className="rounded-xl border border-ase-border bg-ase-surface p-5 space-y-4">
      <h3 className="text-sm font-semibold text-white">Invite member</h3>
      <p className="text-sm text-ase-muted">Create a link and share it with your guest. No email is sent automatically.</p>
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <label className="text-sm text-ase-muted">Display name
          <input required maxLength={100} value={displayName} onChange={(e) => setDisplayName(e.target.value)}
            className="block w-full rounded-lg border border-ase-border bg-ase-bg px-3 py-2 text-white" />
        </label>
        <label className="text-sm text-ase-muted">Role
          <select value={role} onChange={(e) => setRole(e.target.value)}
            className="block w-full rounded-lg border border-ase-border bg-ase-bg px-3 py-2 text-white">
            {PRESET_ROLES[preset].map((value) => <option key={value} value={value}>{value}</option>)}
          </select>
        </label>
        <button type="submit" disabled={!displayName.trim() || isLoading}
          className="flex items-center justify-center gap-2 rounded-xl border border-ase-gold/40 bg-ase-gold/10 p-3 text-ase-gold disabled:opacity-50">
          {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <UserPlus className="w-4 h-4" />}
          {isLoading ? "Creating…" : "Create invitation link"}
        </button>
      </form>
      {error && <p role="alert" className="text-sm text-red-400">{error}</p>}
      {link && <div className="space-y-2">
        <label className="block text-sm text-ase-muted">Invitation link
          <input readOnly value={link} onFocus={(e) => e.target.select()}
            className="block w-full rounded-lg border border-ase-border bg-ase-bg px-3 py-2 text-white" />
        </label>
        <p className="text-xs text-ase-muted">Expires in {expiresInHours} hours.</p>
        <button type="button" onClick={copy} className="rounded-lg border border-ase-border px-3 py-2 text-sm text-ase-gold">Copy link</button>
        <p role="status" className="text-sm text-ase-muted">{copyStatus}</p>
      </div>}
    </div>
  );
}
