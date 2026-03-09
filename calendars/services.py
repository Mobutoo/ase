from __future__ import annotations

"""Business logic for the calendars app.

All functions are pure / side-effect-free where possible and operate on
model querysets returned from the database.  No mutations are performed on
the objects passed in; new objects are created explicitly.

Public API
----------
find_free_slot(member, duration_minutes, before_date) -> datetime | None
detect_conflicts(event, calendar_scope) -> QuerySet[Event]
create_pomodoro_slots(task, member) -> list[Event]
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from django.db.models import Q, QuerySet
from django.utils import timezone as dj_timezone

if TYPE_CHECKING:
    from circles.models import CircleMember
    from app.models import LocalTask
    from .models import Event

logger = logging.getLogger(__name__)

# Default working-hours window used by the slot finder
_WORK_START_HOUR = 8
_WORK_END_HOUR = 20

# Pomodoro defaults
_POMODORO_DURATION_MINUTES = 25
_POMODORO_BREAK_MINUTES = 5


# ---------------------------------------------------------------------------
# find_free_slot
# ---------------------------------------------------------------------------


def find_free_slot(
    member: CircleMember,
    duration_minutes: int,
    before_date: datetime,
    *,
    work_start_hour: int = _WORK_START_HOUR,
    work_end_hour: int = _WORK_END_HOUR,
) -> datetime | None:
    """Find the earliest contiguous free time slot for *member*.

    Scans forward from now until *before_date* in 15-minute increments and
    returns the first candidate that does not overlap with any existing event
    on the member's calendars.

    Parameters
    ----------
    member:
        The ``CircleMember`` whose calendars are inspected.
    duration_minutes:
        Required slot length in minutes.
    before_date:
        Upper search bound (exclusive).
    work_start_hour / work_end_hour:
        Constrain candidates to working hours (local naive UTC convention).

    Returns
    -------
    The start of the first free slot as a UTC-aware ``datetime``, or ``None``
    if no slot was found before *before_date*.
    """
    from .models import Event

    now = dj_timezone.now()
    step = timedelta(minutes=15)
    duration = timedelta(minutes=duration_minutes)

    # Collect all events for this member within the search window
    busy_events = Event.objects.filter(
        Q(calendar__owner=member) | Q(members=member),
        start_at__lt=before_date,
        end_at__gt=now,
    ).values_list("start_at", "end_at").order_by("start_at")

    busy: list[tuple[datetime, datetime]] = list(busy_events)

    candidate = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

    while candidate + duration <= before_date:
        local_hour = candidate.hour
        if not (work_start_hour <= local_hour < work_end_hour):
            # Jump to next working-hours window
            if local_hour >= work_end_hour:
                candidate = (candidate + timedelta(days=1)).replace(
                    hour=work_start_hour, minute=0, second=0, microsecond=0
                )
            else:
                candidate = candidate.replace(
                    hour=work_start_hour, minute=0, second=0, microsecond=0
                )
            continue

        slot_end = candidate + duration
        if slot_end.hour > work_end_hour:
            # Would overflow working hours; try next day
            candidate = (candidate + timedelta(days=1)).replace(
                hour=work_start_hour, minute=0, second=0, microsecond=0
            )
            continue

        conflict = _has_overlap(candidate, slot_end, busy)
        if not conflict:
            return candidate

        candidate += step

    return None


def _has_overlap(
    start: datetime,
    end: datetime,
    busy: list[tuple[datetime, datetime]],
) -> bool:
    for busy_start, busy_end in busy:
        if start < busy_end and end > busy_start:
            return True
    return False


# ---------------------------------------------------------------------------
# detect_conflicts
# ---------------------------------------------------------------------------


def detect_conflicts(
    event: Event,
    calendar_scope: int | None = ...,  # type: ignore[assignment]
) -> QuerySet:
    """Return events that overlap with *event*'s time range.

    Parameters
    ----------
    event:
        The event to check.  May be an unsaved instance.
    calendar_scope:
        If an integer, restrict conflicts to that calendar's events.
        If ``None``, search across all calendars.
        If the sentinel ``...`` (default), restrict to the same calendar as
        *event* (``event.calendar_id``).

    Returns
    -------
    A QuerySet of overlapping ``Event`` objects, excluding *event* itself.
    """
    from .models import Event as EventModel

    qs = EventModel.objects.filter(
        start_at__lt=event.end_at,
        end_at__gt=event.start_at,
    )

    if calendar_scope is ...:
        if event.calendar_id:
            qs = qs.filter(calendar_id=event.calendar_id)
    elif calendar_scope is not None:
        qs = qs.filter(calendar_id=calendar_scope)

    if event.pk:
        qs = qs.exclude(pk=event.pk)

    return qs


# ---------------------------------------------------------------------------
# create_pomodoro_slots
# ---------------------------------------------------------------------------


def create_pomodoro_slots(
    task: LocalTask,
    member: CircleMember,
    *,
    pomodoro_minutes: int = _POMODORO_DURATION_MINUTES,
    break_minutes: int = _POMODORO_BREAK_MINUTES,
    calendar: object | None = None,
) -> list[Event]:
    """Create calendar events from a task's estimated pomodoros.

    Given a ``LocalTask`` with an ``estimated_minutes`` value, this function
    splits the work into pomodoro-sized chunks and schedules them into the
    member's first available free slots.

    Parameters
    ----------
    task:
        The ``LocalTask`` to schedule.
    member:
        The ``CircleMember`` who owns the work slots.
    pomodoro_minutes:
        Length of a single pomodoro in minutes (default 25).
    break_minutes:
        Break length between pomodoros (default 5).
    calendar:
        Target ``Calendar`` instance.  If ``None``, uses the member's first
        CalDAV-enabled calendar.

    Returns
    -------
    A list of newly created ``Event`` instances (one per pomodoro).
    """
    from .models import Calendar, Event

    if task.estimated_minutes is None or task.estimated_minutes <= 0:
        logger.warning(
            "create_pomodoro_slots: task %s has no estimated_minutes, skipping.", task.pk
        )
        return []

    target_calendar = calendar
    if target_calendar is None:
        target_calendar = (
            Calendar.objects.filter(owner=member, caldav_enabled=True)
            .order_by("created_at")
            .first()
        )
    if target_calendar is None:
        logger.warning(
            "create_pomodoro_slots: no calendar found for member %s.", member.pk
        )
        return []

    total_minutes = task.estimated_minutes
    pomodoro_count = max(1, -(-total_minutes // pomodoro_minutes))  # ceiling division

    # Search bound: 14 days from now
    search_bound = dj_timezone.now() + timedelta(days=14)

    created_events: list[Event] = []
    slot_start = dj_timezone.now()

    for i in range(pomodoro_count):
        free_start = find_free_slot(
            member,
            pomodoro_minutes,
            before_date=search_bound,
        )
        if free_start is None:
            logger.warning(
                "create_pomodoro_slots: no free slot found for pomodoro %d of task %s.",
                i + 1,
                task.pk,
            )
            break

        free_end = free_start + timedelta(minutes=pomodoro_minutes)
        event = Event.objects.create(
            calendar=target_calendar,
            title=f"[Pomodoro {i + 1}/{pomodoro_count}] {task.title}",
            description=task.description,
            start_at=free_start,
            end_at=free_end,
            event_type="task",
            linked_task=task,
        )
        created_events.append(event)

        # Advance search start past the just-created slot + break so the next
        # call to find_free_slot skips it.
        slot_start = free_end + timedelta(minutes=break_minutes)
        # Temporarily block this slot by advancing the internal cursor — the
        # next find_free_slot call will see the newly created event in the DB.

    logger.info(
        "create_pomodoro_slots: created %d event(s) for task %s.",
        len(created_events),
        task.pk,
    )
    return created_events
