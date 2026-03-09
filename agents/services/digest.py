from __future__ import annotations

"""Weekly digest generation service.

Generates a personalized summary of the week's events per circle member.
Output is a structured dict consumed by telegram.send_digest() and/or
the REST API for in-app display.
"""

import logging
from datetime import date, datetime, timedelta, timezone

logger = logging.getLogger(__name__)


def _format_date(dt: datetime) -> str:
    """Return a human-readable short date string."""
    try:
        return dt.strftime("%A %d/%m %H:%M")
    except Exception:  # noqa: BLE001
        return str(dt)


def generate_digest(circle: object, week_start: date, week_end: date) -> dict:
    """Generate a structured weekly digest for a circle.

    Args:
        circle:     circles.Circle instance.
        week_start: First day of the digest window (inclusive).
        week_end:   Last day of the digest window (inclusive).

    Returns:
        dict with keys:
            circle_id       — int
            week_label      — human-readable week label (str)
            events          — list of event summary dicts
            highlights      — list of notable plain-text strings
            per_member      — dict[member_id, {name, events, count}]
            stats           — {total_events, total_members_involved}
    """
    from calendars.models import Event

    # Convert dates to datetimes for ORM filtering
    start_dt = datetime(week_start.year, week_start.month, week_start.day, tzinfo=timezone.utc)
    end_dt = datetime(week_end.year, week_end.month, week_end.day, 23, 59, 59, tzinfo=timezone.utc)

    # Fetch all circle events in the window
    events_qs = (
        Event.objects.filter(
            calendar__owner__circle=circle,
            start_at__gte=start_dt,
            start_at__lte=end_dt,
        )
        .select_related("calendar", "calendar__owner")
        .prefetch_related("members")
        .order_by("start_at")
    )

    events_list = []
    highlights = []
    per_member: dict[int, dict] = {}
    total_members_involved: set[int] = set()

    for evt in events_qs:
        member_names = [m.display_name for m in evt.members.all()]
        member_ids = [m.pk for m in evt.members.all()]

        event_summary = {
            "id": evt.pk,
            "title": evt.title,
            "start_at": _format_date(evt.start_at),
            "end_at": _format_date(evt.end_at) if evt.end_at else None,
            "location": evt.location or "",
            "event_type": evt.event_type,
            "dependent_type": evt.dependent_type,
            "member_names": member_names,
            "member_ids": member_ids,
        }
        events_list.append(event_summary)
        total_members_involved.update(member_ids)

        # Build per-member breakdown
        for member in evt.members.all():
            if member.pk not in per_member:
                per_member[member.pk] = {
                    "name": member.display_name,
                    "events": [],
                    "count": 0,
                }
            per_member[member.pk]["events"].append(event_summary)
            per_member[member.pk]["count"] += 1

    # Generate highlights
    if events_list:
        highlights.append(f"{len(events_list)} evenement(s) cette semaine.")

    # Flag members with heavy schedule (5+ events)
    for mid, mdata in per_member.items():
        if mdata["count"] >= 5:
            highlights.append(
                f"{mdata['name']} a un planning charge : {mdata['count']} evenements."
            )

    # Flag days with multiple events
    day_counts: dict[str, int] = {}
    for evt_summary in events_list:
        day_key = evt_summary["start_at"][:10] if evt_summary["start_at"] else ""
        if day_key:
            day_counts[day_key] = day_counts.get(day_key, 0) + 1
    busy_days = [d for d, c in day_counts.items() if c >= 3]
    for d in busy_days:
        highlights.append(f"Journee chargee le {d} ({day_counts[d]} evenements).")

    week_label = f"{week_start.strftime('%d/%m')} – {week_end.strftime('%d/%m/%Y')}"

    digest = {
        "circle_id": circle.pk,
        "week_label": week_label,
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "events": events_list,
        "highlights": highlights,
        "per_member": per_member,
        "stats": {
            "total_events": len(events_list),
            "total_members_involved": len(total_members_involved),
        },
    }

    logger.info(
        "Digest generated for circle %s — week %s: %d events, %d members.",
        circle.pk,
        week_label,
        len(events_list),
        len(total_members_involved),
    )

    return digest
