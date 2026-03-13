import { useEffect, useState, useCallback } from "react";
import {
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  LayoutGrid,
  List,
  AlignJustify,
  Clock4,
  AlertCircle,
  Filter,
  Loader2,
} from "lucide-react";
import { useCalendarStore } from "../stores/calendarStore";
import { useCircleStore } from "../stores/circleStore";
import type { CalendarView } from "../types/calendar";
import type { CalendarEvent } from "../types/calendar";
import { WeekView } from "../components/calendar/WeekView";
import { DayView } from "../components/calendar/DayView";
import { MonthView } from "../components/calendar/MonthView";
import { QuickAddBar } from "../components/calendar/QuickAddBar";
import { EventCreateModal } from "../components/calendar/EventCreateModal";
import { RecurringEditDialog } from "../components/calendar/RecurringEditDialog";
import type { RecurringEditScope } from "../components/calendar/RecurringEditDialog";
import { ConflictDialog } from "../components/calendar/ConflictDialog";

// ---------------------------------------------------------------------------
// View toggle config
// ---------------------------------------------------------------------------

const VIEW_OPTIONS: { value: CalendarView; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { value: "day", label: "Day", icon: Clock4 },
  { value: "week", label: "Week", icon: AlignJustify },
  { value: "month", label: "Month", icon: LayoutGrid },
  { value: "agenda", label: "Agenda", icon: List },
];

// ---------------------------------------------------------------------------
// Date navigation helpers
// ---------------------------------------------------------------------------

function addDays(dateStr: string, delta: number): string {
  const d = new Date(dateStr + "T12:00:00");
  d.setDate(d.getDate() + delta);
  return d.toISOString().slice(0, 10);
}

function addWeeks(dateStr: string, delta: number): string {
  return addDays(dateStr, delta * 7);
}

function addMonths(dateStr: string, delta: number): string {
  const d = new Date(dateStr + "T12:00:00");
  d.setMonth(d.getMonth() + delta);
  return d.toISOString().slice(0, 10);
}

function formatHeaderLabel(dateStr: string, view: CalendarView): string {
  const d = new Date(dateStr + "T12:00:00");
  if (view === "day") {
    return d.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric", year: "numeric" });
  }
  if (view === "month") {
    return d.toLocaleDateString(undefined, { month: "long", year: "numeric" });
  }
  // week / agenda
  const monday = new Date(d);
  monday.setDate(d.getDate() - ((d.getDay() + 6) % 7));
  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);
  const fmtMon = monday.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  const fmtSun = sunday.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  return `${fmtMon} – ${fmtSun}`;
}

function navigate(date: string, view: CalendarView, delta: number): string {
  if (view === "day") return addDays(date, delta);
  if (view === "week" || view === "agenda") return addWeeks(date, delta);
  return addMonths(date, delta);
}

// ---------------------------------------------------------------------------
// Agenda view (simple list)
// ---------------------------------------------------------------------------

interface AgendaViewProps {
  events: CalendarEvent[];
  anchorDate: string;
  onEventClick?: (e: CalendarEvent) => void;
}

function toLocalDateKey(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function AgendaView({ events, anchorDate, onEventClick }: AgendaViewProps) {
  const anchor = new Date(anchorDate + "T00:00:00");
  const days = Array.from({ length: 14 }, (_, i) => {
    const d = new Date(anchor);
    d.setDate(anchor.getDate() + i);
    return d;
  });

  const toKey = (d: Date) => toLocalDateKey(d);

  return (
    <div className="flex flex-col gap-3 p-4 overflow-y-auto">
      {days.map((day) => {
        const key = toKey(day);
        const dayEvents = events.filter(
          (e) => toLocalDateKey(new Date(e.startAt)) === key
        );
        if (dayEvents.length === 0) return null;

        return (
          <div key={key}>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-xs font-semibold text-ase-muted uppercase tracking-wider">
                {day.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })}
              </span>
              <div className="flex-1 border-t border-ase-border/40" />
            </div>
            <div className="flex flex-col gap-1.5">
              {dayEvents.map((e) => (
                <button
                  key={e.id}
                  type="button"
                  onClick={() => onEventClick?.(e)}
                  className="w-full text-left rounded-xl border border-ase-border bg-ase-surface px-4 py-2.5 hover:border-ase-gold/30 hover:bg-ase-surface-2 transition-all duration-150"
                >
                  <p className="text-sm font-medium text-white">{e.title}</p>
                  {!e.allDay && (
                    <p className="text-xs text-ase-subtle mt-0.5">
                      {new Date(e.startAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      {" – "}
                      {new Date(e.endAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </p>
                  )}
                  {e.location && (
                    <p className="text-xs text-ase-subtle mt-0.5 truncate">{e.location}</p>
                  )}
                </button>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export function CalendarPage() {
  const {
    events,
    currentView,
    selectedDate,
    loading,
    error,
    fetchEvents,
    fetchCalendars,
    createEvent,
    deleteEvent,
    setView,
    navigateDate,
    clearError,
  } = useCalendarStore();

  const { members, currentCircle, fetchMembers } = useCircleStore();

  // Modals state
  const [createOpen, setCreateOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [selectedMemberFilter, setSelectedMemberFilter] = useState<string | null>(null);
  const [filterOpen, setFilterOpen] = useState(false);

  // Recurring & conflict dialog state
  const [recurringDialog, setRecurringDialog] = useState<{
    open: boolean;
    eventId: string;
    action: "edit" | "delete";
  }>({ open: false, eventId: "", action: "delete" });

  const [conflictDialog, setConflictDialog] = useState<{
    open: boolean;
    incoming: Partial<CalendarEvent> | null;
    conflicts: CalendarEvent[];
    onForce: (() => void) | null;
  }>({ open: false, incoming: null, conflicts: [], onForce: null });

  // Initial fetch — events + calendars (needed for auto-selecting calendar on create)
  useEffect(() => {
    void fetchEvents();
    void fetchCalendars();
  }, [fetchEvents, fetchCalendars]);

  // Fetch circle members for filter sidebar
  useEffect(() => {
    if (currentCircle) void fetchMembers(currentCircle.id);
  }, [currentCircle, fetchMembers]);

  // NLP quick-add: sends raw text to backend for parsing
  const handleQuickAdd = useCallback(
    async (text: string) => {
      setIsSaving(true);
      try {
        await createEvent({ title: text, eventType: "event", description: "" });
      } finally {
        setIsSaving(false);
      }
    },
    [createEvent]
  );

  // Save from modal
  const handleSaveEvent = useCallback(
    async (payload: Partial<CalendarEvent>) => {
      setIsSaving(true);
      try {
        // Conflict detection (client-side for UX speed)
        if (payload.startAt && payload.endAt) {
          const start = new Date(payload.startAt).getTime();
          const end = new Date(payload.endAt).getTime();
          const conflicts = events.filter((e) => {
            if (e.allDay || payload.allDay) return false;
            const eStart = new Date(e.startAt).getTime();
            const eEnd = new Date(e.endAt).getTime();
            return start < eEnd && end > eStart;
          });

          if (conflicts.length > 0) {
            setConflictDialog({
              open: true,
              incoming: payload,
              conflicts,
              onForce: async () => {
                setConflictDialog((p) => ({ ...p, open: false }));
                await createEvent(payload);
              },
            });
            setIsSaving(false);
            return;
          }
        }
        await createEvent(payload);
        setCreateOpen(false);
      } finally {
        setIsSaving(false);
      }
    },
    [createEvent, events]
  );

  const handleRecurringConfirm = useCallback(
    async (scope: RecurringEditScope) => {
      setRecurringDialog((p) => ({ ...p, open: false }));
      // scope passed to backend via query param
      await deleteEvent(recurringDialog.eventId + `?scope=${scope}`);
    },
    [deleteEvent, recurringDialog.eventId]
  );

  // Filtered events
  const filteredEvents = selectedMemberFilter
    ? events.filter((e) => e.members.some((m) => m.id === selectedMemberFilter))
    : events;

  const headerLabel = formatHeaderLabel(selectedDate, currentView);

  // Today shortcut (local date, not UTC)
  const today = toLocalDateKey(new Date());

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-ase-bg">
      {/* ── Top bar ──────────────────────────────────────────────── */}
      <div className="flex-shrink-0 px-5 pt-5 pb-3 border-b border-ase-border bg-ase-bg">
        {/* Title row */}
        <div className="flex items-center gap-3 mb-3">
          <div className="w-8 h-8 rounded-lg bg-ase-gold/10 border border-ase-gold/20 flex items-center justify-center flex-shrink-0">
            <CalendarDays className="w-4 h-4 text-ase-gold" />
          </div>
          <h1 className="text-xl font-bold text-white tracking-tight">Calendar</h1>

          {loading && <Loader2 className="w-4 h-4 text-ase-gold animate-spin ml-1" />}

          {/* Spacer */}
          <div className="flex-1" />

          {/* View toggle */}
          <div className="flex gap-0.5 p-0.5 rounded-lg bg-ase-surface border border-ase-border">
            {VIEW_OPTIONS.map(({ value, label, icon: Icon }) => (
              <button
                key={value}
                type="button"
                onClick={() => setView(value)}
                title={label}
                className={[
                  "flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-all duration-150",
                  currentView === value
                    ? "bg-ase-gold/20 text-ase-gold"
                    : "text-ase-subtle hover:text-ase-muted",
                ].join(" ")}
              >
                <Icon className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">{label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Nav row */}
        <div className="flex items-center gap-2 mb-3">
          <button
            type="button"
            onClick={() => navigateDate(navigate(selectedDate, currentView, -1))}
            className="w-8 h-8 flex items-center justify-center rounded-lg border border-ase-border text-ase-muted hover:text-white hover:border-ase-border-2 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={() => navigateDate(today)}
            className={[
              "px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors",
              selectedDate === today
                ? "border-ase-gold/40 text-ase-gold bg-ase-gold/10"
                : "border-ase-border text-ase-muted hover:text-white hover:border-ase-border-2",
            ].join(" ")}
          >
            Today
          </button>

          <button
            type="button"
            onClick={() => navigateDate(navigate(selectedDate, currentView, 1))}
            className="w-8 h-8 flex items-center justify-center rounded-lg border border-ase-border text-ase-muted hover:text-white hover:border-ase-border-2 transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>

          <span className="text-sm font-semibold text-white ml-1 flex-1 truncate">
            {headerLabel}
          </span>

          {/* Member filter toggle */}
          {members.length > 0 && (
            <button
              type="button"
              onClick={() => setFilterOpen((p) => !p)}
              className={[
                "w-8 h-8 flex items-center justify-center rounded-lg border text-ase-muted transition-colors",
                filterOpen || selectedMemberFilter
                  ? "border-ase-gold/40 text-ase-gold bg-ase-gold/10"
                  : "border-ase-border hover:text-white hover:border-ase-border-2",
              ].join(" ")}
              title="Filter by member"
            >
              <Filter className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Quick-add bar */}
        <QuickAddBar onSubmit={handleQuickAdd} isLoading={isSaving} />

        {/* Error banner */}
        {error && (
          <div className="mt-2 flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400">
            <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
            <span>{error}</span>
            <button type="button" onClick={clearError} className="ml-auto hover:text-red-300">
              Dismiss
            </button>
          </div>
        )}
      </div>

      {/* ── Content area ─────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">
        {/* Member filter sidebar */}
        {filterOpen && members.length > 0 && (
          <div className="flex-shrink-0 w-44 border-r border-ase-border bg-ase-surface overflow-y-auto p-3">
            <p className="text-[10px] font-semibold text-ase-subtle uppercase tracking-wider mb-2">
              Filter by member
            </p>
            <button
              type="button"
              onClick={() => setSelectedMemberFilter(null)}
              className={[
                "w-full text-left rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors mb-1",
                !selectedMemberFilter
                  ? "bg-ase-gold/20 text-ase-gold"
                  : "text-ase-muted hover:text-white hover:bg-ase-surface-2",
              ].join(" ")}
            >
              All members
            </button>
            {members.map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={() =>
                  setSelectedMemberFilter(selectedMemberFilter === m.id ? null : m.id)
                }
                className={[
                  "w-full text-left flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors",
                  selectedMemberFilter === m.id
                    ? "bg-ase-gold/20 text-ase-gold"
                    : "text-ase-muted hover:text-white hover:bg-ase-surface-2",
                ].join(" ")}
              >
                <span
                  className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0"
                  style={{ backgroundColor: m.avatarColor + "40", color: m.avatarColor }}
                >
                  {m.avatarEmoji || m.displayName[0]?.toUpperCase()}
                </span>
                <span className="truncate">{m.displayName}</span>
              </button>
            ))}
          </div>
        )}

        {/* Calendar view */}
        <div className="flex-1 overflow-hidden">
          {currentView === "day" && (
            <DayView
              date={selectedDate}
              events={filteredEvents}
              onEventClick={() => {}}
            />
          )}
          {currentView === "week" && (
            <WeekView
              anchorDate={selectedDate}
              events={filteredEvents}
              onEventClick={() => {}}
              onDayClick={(date) => { navigateDate(date); setView("day"); }}
            />
          )}
          {currentView === "month" && (
            <MonthView
              anchorDate={selectedDate}
              events={filteredEvents}
              onEventClick={() => {}}
              onDayClick={(date) => { navigateDate(date); setView("day"); }}
            />
          )}
          {currentView === "agenda" && (
            <AgendaView
              events={filteredEvents}
              anchorDate={selectedDate}
              onEventClick={() => {}}
            />
          )}
        </div>
      </div>

      {/* ── FAB — New event ───────────────────────────────────────── */}
      <button
        type="button"
        onClick={() => setCreateOpen(true)}
        className="fixed bottom-20 right-6 z-50 flex items-center gap-2 px-4 py-3 rounded-2xl bg-ase-gold text-black font-semibold text-sm shadow-glow-lg hover:bg-ase-gold/90 active:scale-95 transition-all duration-150"
      >
        <CalendarDays className="w-4 h-4" />
        New event
      </button>

      {/* ── Modals ────────────────────────────────────────────────── */}
      <EventCreateModal
        isOpen={createOpen}
        onClose={() => setCreateOpen(false)}
        onSave={handleSaveEvent}
        initialDate={selectedDate}
        availableMembers={members}
        isSaving={isSaving}
      />

      <RecurringEditDialog
        isOpen={recurringDialog.open}
        onClose={() => setRecurringDialog((p) => ({ ...p, open: false }))}
        onConfirm={handleRecurringConfirm}
        action={recurringDialog.action}
      />

      <ConflictDialog
        isOpen={conflictDialog.open}
        incoming={conflictDialog.incoming}
        conflicts={conflictDialog.conflicts}
        onForce={() => {
          conflictDialog.onForce?.();
          setConflictDialog((p) => ({ ...p, open: false }));
        }}
        onCancel={() => setConflictDialog((p) => ({ ...p, open: false }))}
      />
    </div>
  );
}
