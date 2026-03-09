import { useEffect, useState } from "react";
import {
  Users,
  Settings2,
  AlertCircle,
  Loader2,
  UserPlus,
  ChevronDown,
  CheckCircle2,
} from "lucide-react";
import { useCircleStore } from "../stores/circleStore";
import type { Circle } from "../types/circle";
import { MemberCard } from "../components/circle/MemberCard";
import { InviteForm } from "../components/circle/InviteForm";
import { CircleSettings } from "../components/circle/CircleSettings";

// ---------------------------------------------------------------------------
// Tabs
// ---------------------------------------------------------------------------

type Tab = "members" | "invite" | "settings";

const TABS: { value: Tab; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { value: "members", label: "Members", icon: Users },
  { value: "invite", label: "Invite", icon: UserPlus },
  { value: "settings", label: "Settings", icon: Settings2 },
];

// ---------------------------------------------------------------------------
// Preset label mapping
// ---------------------------------------------------------------------------

const PRESET_EMOJI: Record<string, string> = {
  family: "🏠",
  colocation: "🏘️",
  team: "💼",
  club: "🎯",
  custom: "⚙️",
};

// ---------------------------------------------------------------------------
// Circle selector dropdown
// ---------------------------------------------------------------------------

interface CircleSelectorProps {
  circles: Circle[];
  current: Circle | null;
  onSelect: (circle: Circle) => void;
}

function CircleSelector({ circles, current, onSelect }: CircleSelectorProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((p) => !p)}
        className="flex items-center gap-2 rounded-xl border border-ase-border bg-ase-surface px-3 py-2 text-sm font-medium text-white hover:border-ase-border-2 transition-colors"
      >
        <span className="text-base leading-none">
          {current ? PRESET_EMOJI[current.preset] ?? "⚙️" : "—"}
        </span>
        <span className="truncate max-w-[140px]">{current?.name ?? "Select circle"}</span>
        <ChevronDown className="w-3.5 h-3.5 text-ase-subtle flex-shrink-0" />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute left-0 top-[calc(100%+6px)] z-20 w-56 rounded-xl border border-ase-border bg-ase-surface shadow-2xl py-1 animate-scale-in">
            {circles.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => {
                  onSelect(c);
                  setOpen(false);
                }}
                className={[
                  "w-full text-left flex items-center gap-2.5 px-3 py-2 text-sm transition-colors",
                  current?.id === c.id
                    ? "text-ase-gold bg-ase-gold/10"
                    : "text-ase-muted hover:text-white hover:bg-ase-surface-2",
                ].join(" ")}
              >
                <span className="text-base leading-none">{PRESET_EMOJI[c.preset] ?? "⚙️"}</span>
                <span className="flex-1 truncate">{c.name}</span>
                {current?.id === c.id && <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0" />}
                {c.isPrimary && current?.id !== c.id && (
                  <span className="text-[10px] text-ase-subtle border border-ase-border px-1 rounded">
                    Primary
                  </span>
                )}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export function CirclePage() {
  const {
    circles,
    currentCircle,
    members,
    loading,
    error,
    fetchCircles,
    setCurrentCircle,
    fetchMembers,
    inviteMember,
    updateRole,
    removeMember,
    updateCircle,
    clearError,
  } = useCircleStore();

  const [activeTab, setActiveTab] = useState<Tab>("members");
  const [isSaving, setIsSaving] = useState(false);

  // Initial load
  useEffect(() => {
    void fetchCircles();
  }, [fetchCircles]);

  // Fetch members when circle changes
  useEffect(() => {
    if (currentCircle) void fetchMembers(currentCircle.id);
  }, [currentCircle, fetchMembers]);

  const handleInvite = async (payload: Parameters<typeof inviteMember>[1]) => {
    if (!currentCircle) return;
    setIsSaving(true);
    try {
      await inviteMember(currentCircle.id, payload);
      setActiveTab("members");
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveCircle = async (patch: Parameters<typeof updateCircle>[1]) => {
    if (!currentCircle) return;
    setIsSaving(true);
    try {
      await updateCircle(currentCircle.id, patch);
    } finally {
      setIsSaving(false);
    }
  };

  // Member stats
  const pendingCount = members.filter((m) => m.inviteAcceptedAt === undefined).length;
  const activeCount = members.length - pendingCount;

  return (
    <div className="flex flex-col min-h-screen bg-ase-bg">
      {/* ── Header ──────────────────────────────────────────────── */}
      <div className="px-5 pt-6 pb-4 border-b border-ase-border">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 rounded-lg bg-ase-gold/10 border border-ase-gold/20 flex items-center justify-center flex-shrink-0">
            <Users className="w-4 h-4 text-ase-gold" />
          </div>
          <h1 className="text-xl font-bold text-white tracking-tight">Circles</h1>
          {loading && <Loader2 className="w-4 h-4 text-ase-gold animate-spin ml-1" />}
          <div className="flex-1" />
          <CircleSelector
            circles={circles}
            current={currentCircle}
            onSelect={setCurrentCircle}
          />
        </div>

        {/* Stats strip */}
        {currentCircle && (
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5">
              <span className="text-2xl font-bold text-white tabular-nums">{members.length}</span>
              <span className="text-xs text-ase-subtle leading-tight">total<br />members</span>
            </div>
            <div className="w-px h-8 bg-ase-border" />
            <div className="flex items-center gap-1.5">
              <span className="text-2xl font-bold text-green-400 tabular-nums">{activeCount}</span>
              <span className="text-xs text-ase-subtle leading-tight">active</span>
            </div>
            {pendingCount > 0 && (
              <>
                <div className="w-px h-8 bg-ase-border" />
                <div className="flex items-center gap-1.5">
                  <span className="text-2xl font-bold text-orange-400 tabular-nums">{pendingCount}</span>
                  <span className="text-xs text-ase-subtle leading-tight">pending</span>
                </div>
              </>
            )}
            {currentCircle.agentEnabled && (
              <>
                <div className="w-px h-8 bg-ase-border" />
                <span className="text-xs px-2 py-1 rounded-full border border-ase-gold/30 bg-ase-gold/10 text-ase-gold font-medium">
                  AI Agent ON
                </span>
              </>
            )}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mt-3 flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400">
            <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
            <span>{error}</span>
            <button type="button" onClick={clearError} className="ml-auto hover:text-red-300 transition-colors">
              Dismiss
            </button>
          </div>
        )}
      </div>

      {/* ── Tabs ─────────────────────────────────────────────────── */}
      <div className="flex gap-0 border-b border-ase-border px-5">
        {TABS.map(({ value, label, icon: Icon }) => (
          <button
            key={value}
            type="button"
            onClick={() => setActiveTab(value)}
            className={[
              "flex items-center gap-1.5 px-4 py-3 text-sm font-medium border-b-2 transition-all duration-150",
              activeTab === value
                ? "border-ase-gold text-ase-gold"
                : "border-transparent text-ase-subtle hover:text-ase-muted",
            ].join(" ")}
          >
            <Icon className="w-3.5 h-3.5" />
            {label}
          </button>
        ))}
      </div>

      {/* ── Tab content ──────────────────────────────────────────── */}
      <div className="flex-1 p-5 max-w-2xl mx-auto w-full">
        {/* Members tab */}
        {activeTab === "members" && (
          <div className="animate-fade-in">
            {!currentCircle ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <Users className="w-10 h-10 text-ase-subtle mb-3" />
                <p className="text-sm text-ase-muted">No circle selected</p>
                <p className="text-xs text-ase-subtle mt-1">
                  Select or create a circle to see its members
                </p>
              </div>
            ) : loading && members.length === 0 ? (
              <div className="flex items-center justify-center py-16">
                <Loader2 className="w-6 h-6 text-ase-gold animate-spin" />
              </div>
            ) : members.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <Users className="w-10 h-10 text-ase-subtle mb-3" />
                <p className="text-sm text-ase-muted">No members yet</p>
                <button
                  type="button"
                  onClick={() => setActiveTab("invite")}
                  className="mt-3 px-4 py-2 rounded-xl border border-ase-gold/40 bg-ase-gold/10 text-ase-gold text-sm font-medium hover:bg-ase-gold/20 transition-colors"
                >
                  Invite first member
                </button>
              </div>
            ) : (
              <div className="flex flex-col gap-2">
                {members.map((member) => (
                  <MemberCard
                    key={member.id}
                    member={member}
                    canManage={true}
                    onRoleChange={updateRole}
                    onRemove={removeMember}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Invite tab */}
        {activeTab === "invite" && (
          <div className="animate-fade-in">
            {!currentCircle ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <UserPlus className="w-10 h-10 text-ase-subtle mb-3" />
                <p className="text-sm text-ase-muted">Select a circle to invite members</p>
              </div>
            ) : (
              <InviteForm onInvite={handleInvite} isLoading={isSaving} />
            )}
          </div>
        )}

        {/* Settings tab */}
        {activeTab === "settings" && (
          <div className="animate-fade-in">
            {!currentCircle ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <Settings2 className="w-10 h-10 text-ase-subtle mb-3" />
                <p className="text-sm text-ase-muted">Select a circle to configure settings</p>
              </div>
            ) : (
              <CircleSettings
                circle={currentCircle}
                onSave={handleSaveCircle}
                isSaving={isSaving}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
