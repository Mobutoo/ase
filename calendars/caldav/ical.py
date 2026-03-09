from __future__ import annotations

"""iCalendar conversion helpers using vobject.

Converts between the ``Event`` model and RFC 5545 iCalendar text.

Dependencies:
    pip install vobject

All datetimes are stored in UTC.  The helpers normalise incoming
iCalendar data to UTC before returning parsed dicts.
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy import so that the app can load even without vobject installed (the
# CalDAV feature is optional / additive).
# ---------------------------------------------------------------------------


def _vobject():
    try:
        import vobject
        return vobject
    except ImportError as exc:
        raise ImportError(
            "vobject is required for CalDAV/iCalendar support. "
            "Install it with: pip install vobject"
        ) from exc


# ---------------------------------------------------------------------------
# iCalendar → dict
# ---------------------------------------------------------------------------


def _to_utc(dt: Any) -> datetime:
    """Normalise a datetime-like value (date or datetime) to a UTC datetime."""
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            # Treat naive datetimes as UTC
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    # date without time — treat as midnight UTC
    return datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc)


def events_from_ics(raw: str) -> list[dict]:
    """Parse a VCALENDAR string and return a list of event dicts.

    Each dict contains keys matching the ``Event`` model fields plus a
    ``raw`` key with the original VEVENT text for CalDAV round-tripping.
    """
    vobject = _vobject()
    try:
        cal = vobject.readOne(raw)
    except Exception as exc:
        raise ValueError(f"Invalid iCalendar data: {exc}") from exc

    results: list[dict] = []
    for component in cal.components():
        if component.name != "VEVENT":
            continue
        try:
            result = _vevent_to_dict(component)
            results.append(result)
        except Exception as exc:
            logger.warning("Skipping malformed VEVENT: %s", exc)

    return results


def _vevent_to_dict(vevent: Any) -> dict:
    """Convert a single vobject VEVENT component to a plain dict."""
    uid = getattr(vevent, "uid", None)
    uid_value = uid.value if uid else ""

    dtstart = vevent.dtstart.value
    dtend_obj = getattr(vevent, "dtend", None)
    if dtend_obj is None:
        # All-day events may have DURATION instead
        from datetime import timedelta
        duration_obj = getattr(vevent, "duration", None)
        if duration_obj is not None:
            dtend = _to_utc(dtstart) + duration_obj.value
        else:
            dtend = _to_utc(dtstart)
    else:
        dtend = _to_utc(dtend_obj.value)

    all_day = not isinstance(dtstart, datetime)
    dtstart = _to_utc(dtstart)

    summary = getattr(vevent, "summary", None)
    description = getattr(vevent, "description", None)
    location = getattr(vevent, "location", None)
    rrule = getattr(vevent, "rrule", None)

    return {
        "uid": uid_value,
        "title": summary.value if summary else "",
        "description": description.value if description else "",
        "location": location.value if location else "",
        "start_at": dtstart,
        "end_at": dtend,
        "all_day": all_day,
        "recurrence_rule": rrule.value if rrule else None,
        "raw": vevent.serialize(),
    }


# ---------------------------------------------------------------------------
# Event model → iCalendar text
# ---------------------------------------------------------------------------


def event_to_ics(event: Any) -> str:
    """Serialise an ``Event`` model instance to a VEVENT iCalendar block.

    Returns the VEVENT text (without the surrounding VCALENDAR wrapper)
    so that callers can embed it inside a VCALENDAR container.

    If the event already has ``caldav_raw`` stored (from a previous sync),
    that is returned verbatim to preserve round-trip fidelity.
    """
    if event.caldav_raw:
        return event.caldav_raw.strip()

    vobject = _vobject()
    cal = vobject.iCalendar()
    vevent = vobject.newFromBehavior("vevent")

    # UID
    vevent.add("uid").value = str(event.uid)

    # SUMMARY
    vevent.add("summary").value = event.title

    # DESCRIPTION
    if event.description:
        vevent.add("description").value = event.description

    # LOCATION
    if event.location:
        vevent.add("location").value = event.location

    # DTSTART / DTEND
    if event.all_day:
        from datetime import date as date_type
        vevent.add("dtstart").value = event.start_at.date()
        vevent.add("dtend").value = event.end_at.date()
    else:
        vevent.add("dtstart").value = event.start_at.replace(tzinfo=timezone.utc)
        vevent.add("dtend").value = event.end_at.replace(tzinfo=timezone.utc)

    # DTSTAMP
    vevent.add("dtstamp").value = datetime.now(tz=timezone.utc)

    # RRULE
    if event.recurrence_rule:
        vevent.add("rrule").value = event.recurrence_rule

    cal.add(vevent)
    # Return just the VEVENT block (strip VCALENDAR wrapper for embedding)
    serialised = cal.serialize()
    # Extract VEVENT lines
    lines = serialised.splitlines()
    in_vevent = False
    vevent_lines: list[str] = []
    for line in lines:
        if line.startswith("BEGIN:VEVENT"):
            in_vevent = True
        if in_vevent:
            vevent_lines.append(line)
        if line.startswith("END:VEVENT"):
            in_vevent = False

    return "\r\n".join(vevent_lines)
