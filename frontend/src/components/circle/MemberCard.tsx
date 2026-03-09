import type { CircleMember } from "../../types/circle";
import { Globe, MoreHorizontal, ShieldCheck, User } from "lucide-react";
import { useState } from "react";

// ---------------------------------------------------------------------------
// Role badge config
// ---------------------------------------------------------------------------

const ROLE_STYLES: Record<string, string> = {
  admin: "bg-ase-gold/20 text-ase-gold border-ase-gold/30",
  owner: "bg-purple-500/20 text-purple-300 border-purple-500/30",
  member: "bg-zinc-700/50 text-ase-muted border-zinc-600/30",
  viewer: "bg-blue-500/10 text-blue-400 border-blue-500/20",
};

const ROLE_ICON: Record<string, React.ComponentType<{ className?: string }>> = {
  admin: ShieldCheck,
  owner: ShieldCheck,
  member: User,
  viewer: User,
};

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface MemberCardProps {
  member: CircleMember;
  onRoleChange?: (memberId: string, role: string) => void;
  onRemove?: (memberId: string) => void;
  canManage?: boolean;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function MemberCard({
  member,
  onRoleChange,
  onRemove,
  canManage = false,
}: MemberCardProps) {
  const [menuOpen, setMenuOpen] = useState(false);

  const roleStyle = ROLE_STYLES[member.role] ?? ROLE_STYLES.member;
  const RoleIcon = ROLE_ICON[member.role] ?? User;

  const roleLabel = member.role.charAt(0).toUpperCase() + member.role.slice(1);

  const ROLE_OPTIONS = ["admin", "member", "viewer"];

  return (
    <div className="group flex items-center gap-3 rounded-xl border border-ase-border bg-ase-surface px-4 py-3 transition-all duration-150 hover:border-ase-border-2 hover:shadow-card">
      {/* Avatar */}
      <div
        className="w-10 h-10 rounded-full flex items-center justify-center text-base font-bold flex-shrink-0 border-2"
        style={{
          backgroundColor: member.avatarColor + "30",
          color: member.avatarColor,
          borderColor: member.avatarColor + "50",
        }}
      >
        {member.avatarEmoji || member.displayName[0]?.toUpperCase()}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 min-w-0">
          <p className="text-sm font-medium text-white truncate">{member.displayName}</p>
          {member.membershipType === "federated" && (
            <Globe className="w-3 h-3 text-ase-subtle flex-shrink-0" aria-label="Federated member" />
          )}
        </div>
        <div className="flex items-center gap-1.5 mt-0.5">
          <span
            className={[
              "inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full border",
              roleStyle,
            ].join(" ")}
          >
            <RoleIcon className="w-2.5 h-2.5" />
            {roleLabel}
          </span>
          {member.inviteAcceptedAt === undefined && (
            <span className="text-[11px] text-orange-400 border border-orange-400/30 bg-orange-400/10 px-1.5 py-0.5 rounded-full">
              Pending
            </span>
          )}
        </div>
      </div>

      {/* Actions (visible on hover when canManage) */}
      {canManage && (
        <div className="relative flex-shrink-0">
          <button
            type="button"
            onClick={() => setMenuOpen((prev) => !prev)}
            className="w-7 h-7 rounded-lg flex items-center justify-center text-ase-subtle opacity-0 group-hover:opacity-100 hover:text-white hover:bg-ase-surface-2 transition-all duration-150"
          >
            <MoreHorizontal className="w-4 h-4" />
          </button>

          {menuOpen && (
            <>
              {/* Backdrop */}
              <div
                className="fixed inset-0 z-10"
                onClick={() => setMenuOpen(false)}
              />
              <div className="absolute right-0 top-8 z-20 w-36 rounded-xl border border-ase-border bg-ase-surface shadow-2xl py-1 animate-scale-in">
                {ROLE_OPTIONS.filter((r) => r !== member.role).map((role) => (
                  <button
                    key={role}
                    type="button"
                    onClick={() => {
                      onRoleChange?.(member.id, role);
                      setMenuOpen(false);
                    }}
                    className="w-full text-left px-3 py-1.5 text-xs text-ase-muted hover:text-white hover:bg-ase-surface-2 transition-colors"
                  >
                    Make {role}
                  </button>
                ))}
                <div className="border-t border-ase-border my-1" />
                <button
                  type="button"
                  onClick={() => {
                    onRemove?.(member.id);
                    setMenuOpen(false);
                  }}
                  className="w-full text-left px-3 py-1.5 text-xs text-red-400 hover:bg-red-500/10 transition-colors"
                >
                  Remove member
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
