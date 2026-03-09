import { useState } from "react";
import { UserPlus, Globe, Mail, Loader2 } from "lucide-react";
import type { InviteMemberPayload } from "../../stores/circleStore";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface InviteFormProps {
  onInvite: (payload: InviteMemberPayload) => Promise<void>;
  isLoading?: boolean;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function InviteForm({ onInvite, isLoading = false }: InviteFormProps) {
  const [mode, setMode] = useState<"local" | "federated">("local");
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [role, setRole] = useState("member");
  const [federatedServer, setFederatedServer] = useState("");

  const isValid = email.trim() && (mode === "local" || federatedServer.trim());

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValid || isLoading) return;

    await onInvite({
      email: email.trim(),
      role,
      displayName: displayName.trim() || undefined,
      membershipType: mode,
      federatedServer: mode === "federated" ? federatedServer.trim() : undefined,
    });

    setEmail("");
    setDisplayName("");
    setFederatedServer("");
  };

  return (
    <div className="rounded-xl border border-ase-border bg-ase-surface p-5">
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <div className="w-7 h-7 rounded-lg bg-ase-gold/10 border border-ase-gold/20 flex items-center justify-center">
          <UserPlus className="w-3.5 h-3.5 text-ase-gold" />
        </div>
        <h3 className="text-sm font-semibold text-white">Invite member</h3>
      </div>

      {/* Mode toggle */}
      <div className="flex gap-1 p-1 rounded-lg bg-ase-bg border border-ase-border mb-4">
        {(["local", "federated"] as const).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => setMode(m)}
            className={[
              "flex-1 flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-md text-xs font-medium transition-all duration-150",
              mode === m
                ? "bg-ase-surface border border-ase-border-2 text-white"
                : "text-ase-subtle hover:text-ase-muted",
            ].join(" ")}
          >
            {m === "local" ? (
              <><Mail className="w-3 h-3" /> Local</>
            ) : (
              <><Globe className="w-3 h-3" /> Federated</>
            )}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        {/* Email */}
        <div>
          <label className="text-xs font-medium text-ase-subtle block mb-1">
            Email address <span className="text-red-400">*</span>
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="colleague@example.com"
            required
            className="w-full h-9 rounded-lg border border-ase-border bg-ase-bg px-3 text-sm text-white placeholder:text-ase-subtle focus:outline-none focus:border-ase-gold/50"
          />
        </div>

        {/* Federated server */}
        {mode === "federated" && (
          <div>
            <label className="text-xs font-medium text-ase-subtle block mb-1">
              Federation server <span className="text-red-400">*</span>
            </label>
            <input
              type="url"
              value={federatedServer}
              onChange={(e) => setFederatedServer(e.target.value)}
              placeholder="https://their-server.example.com"
              required
              className="w-full h-9 rounded-lg border border-ase-border bg-ase-bg px-3 text-sm text-white placeholder:text-ase-subtle focus:outline-none focus:border-ase-gold/50"
            />
            <p className="text-[10px] text-ase-subtle mt-1">
              CalDAV / ActivityPub compatible endpoint
            </p>
          </div>
        )}

        {/* Display name + role row */}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs font-medium text-ase-subtle block mb-1">Display name</label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Optional"
              className="w-full h-9 rounded-lg border border-ase-border bg-ase-bg px-3 text-sm text-white placeholder:text-ase-subtle focus:outline-none focus:border-ase-gold/50"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-ase-subtle block mb-1">Role</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full h-9 rounded-lg border border-ase-border bg-ase-bg px-3 text-sm text-white focus:outline-none focus:border-ase-gold/50"
            >
              <option value="member">Member</option>
              <option value="admin">Admin</option>
              <option value="viewer">Viewer</option>
            </select>
          </div>
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={!isValid || isLoading}
          className={[
            "flex items-center justify-center gap-1.5 w-full py-2.5 rounded-xl text-sm font-medium border transition-all duration-150 mt-1",
            isValid && !isLoading
              ? "bg-ase-gold/20 border-ase-gold/40 text-ase-gold hover:bg-ase-gold/30"
              : "bg-transparent border-ase-border text-ase-subtle cursor-not-allowed opacity-50",
          ].join(" ")}
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <UserPlus className="w-4 h-4" />
          )}
          {isLoading ? "Sending…" : "Send invitation"}
        </button>
      </form>
    </div>
  );
}
