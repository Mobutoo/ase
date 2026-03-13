"""Bidirectional Google Calendar sync via the gws CLI.

This module executes the ``gws`` binary as a subprocess to list, create, and
update events in Google Calendar.  Incremental sync is supported through
Google's ``syncToken`` mechanism — the token is persisted on the
``GoogleCalendarSync`` model between runs so only changed events are fetched.

Sync-loop prevention
--------------------
Events that originate from Google (``google_event_id`` is set) are never pushed
back.  Events pushed to Google receive a ``google_event_id`` on creation so
subsequent pulls recognise them as already-synced.

Error handling
--------------
If the ``gws`` binary is not installed or not on ``$PATH``, every call raises a
clear ``GwsNotFoundError`` instead of a generic ``FileNotFoundError``.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from datetime import datetime, timezone
from typing import Any

from django.db import transaction
from django.utils import timezone as dj_timezone

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class GwsNotFoundError(RuntimeError):
    """Raised when the ``gws`` CLI binary cannot be found on the system."""


class GwsSyncError(RuntimeError):
    """Raised when the ``gws`` subprocess returns a non-zero exit code."""


# ---------------------------------------------------------------------------
# Low-level gws wrapper
# ---------------------------------------------------------------------------

_GWS_TIMEOUT_SECONDS = 30


def _ensure_gws_available() -> str:
    """Return the absolute path to the ``gws`` binary, or raise ``GwsNotFoundError``."""
    path = shutil.which("gws")
    if path is None:
        raise GwsNotFoundError(
            "The 'gws' CLI binary is not installed or not on $PATH. "
            "Install it to enable Google Calendar sync."
        )
    return path


def _run_gws(args: list[str]) -> dict[str, Any]:
    """Execute ``gws calendar <args> --output json`` and return parsed JSON.

    Raises
    ------
    GwsNotFoundError
        If the ``gws`` binary is missing.
    GwsSyncError
        If the subprocess exits with a non-zero return code.
    """
    gws_path = _ensure_gws_available()
    cmd = [gws_path, "calendar"] + args + ["--output", "json"]
    logger.debug("Running gws: %s", " ".join(cmd))

    result = subprocess.run(  # noqa: S603
        cmd,
        capture_output=True,
        text=True,
        timeout=_GWS_TIMEOUT_SECONDS,
    )

    if result.returncode != 0:
        raise GwsSyncError(
            f"gws exited with code {result.returncode}: {result.stderr.strip()}"
        )

    if not result.stdout.strip():
        return {}

    return json.loads(result.stdout)


# ---------------------------------------------------------------------------
# Pull: Google -> Ase
# ---------------------------------------------------------------------------


def _parse_google_datetime(raw: str | None) -> datetime | None:
    """Parse an ISO-8601 datetime string returned by gws into a tz-aware datetime.

    Returns ``None`` if ``raw`` is falsy.
    """
    if not raw:
        return None
    # Google may return with or without timezone offset.  If no offset, assume UTC.
    cleaned = raw.replace("Z", "+00:00")
    return datetime.fromisoformat(cleaned)


def _pull_from_google(sync_config: Any) -> int:
    """Pull new / updated events from Google Calendar into Ase.

    Uses incremental sync (``--sync-token``) when available.  Returns the number
    of events created or updated.
    """
    from calendars.models import Event  # local import to avoid circular deps

    args = [
        "events", "list",
        "--calendar", sync_config.google_calendar_id,
        "--account", sync_config.google_account_email,
    ]

    if sync_config.sync_token:
        args += ["--sync-token", sync_config.sync_token]

    data = _run_gws(args)

    items: list[dict[str, Any]] = data.get("items", [])
    next_sync_token: str = data.get("nextSyncToken", "")

    count = 0
    for item in items:
        google_id: str = item.get("id", "")
        if not google_id:
            continue

        summary = item.get("summary", "(no title)")
        description = item.get("description", "")
        location = item.get("location", "")
        updated_raw = item.get("updated", "")

        # Parse start / end.  Google uses "dateTime" for timed events,
        # "date" for all-day events.
        start_info = item.get("start", {})
        end_info = item.get("end", {})
        all_day = "date" in start_info and "dateTime" not in start_info

        if all_day:
            start_at = _parse_google_datetime(start_info.get("date") + "T00:00:00Z")
            end_at = _parse_google_datetime(end_info.get("date") + "T00:00:00Z")
        else:
            start_at = _parse_google_datetime(
                start_info.get("dateTime") or start_info.get("date")
            )
            end_at = _parse_google_datetime(
                end_info.get("dateTime") or end_info.get("date")
            )

        if start_at is None or end_at is None:
            logger.warning(
                "Skipping Google event %s — missing start/end times.", google_id
            )
            continue

        # Check if this event already exists in Ase
        existing = Event.objects.filter(
            calendar=sync_config.ase_calendar,
            google_event_id=google_id,
        ).first()

        if existing is not None:
            # Update only if Google's version is newer
            google_updated = _parse_google_datetime(updated_raw)
            if google_updated and google_updated <= existing.updated_at:
                continue
            Event.objects.filter(pk=existing.pk).update(
                title=summary,
                description=description,
                location=location,
                start_at=start_at,
                end_at=end_at,
                all_day=all_day,
            )
            count += 1
        else:
            # Cancelled events have status "cancelled" — skip creating new ones
            if item.get("status") == "cancelled":
                continue
            Event.objects.create(
                calendar=sync_config.ase_calendar,
                title=summary,
                description=description,
                location=location,
                start_at=start_at,
                end_at=end_at,
                all_day=all_day,
                google_event_id=google_id,
                event_type="event",
            )
            count += 1

    # Persist the sync token for incremental polling
    if next_sync_token:
        type(sync_config).objects.filter(pk=sync_config.pk).update(
            sync_token=next_sync_token,
        )

    return count


# ---------------------------------------------------------------------------
# Push: Ase -> Google
# ---------------------------------------------------------------------------


def _push_to_google(sync_config: Any) -> int:
    """Push Ase events that have no ``google_event_id`` to Google Calendar.

    Only events belonging to the linked ``ase_calendar`` are considered.
    Events that already have a ``google_event_id`` (i.e. came *from* Google
    or were already pushed) are skipped to prevent sync loops.

    Returns the number of events pushed.
    """
    from calendars.models import Event  # local import

    new_events = Event.objects.filter(
        calendar=sync_config.ase_calendar,
        google_event_id="",
    )

    count = 0
    for event in new_events:
        start_iso = event.start_at.isoformat()
        end_iso = event.end_at.isoformat()

        args = [
            "events", "create",
            "--calendar", sync_config.google_calendar_id,
            "--account", sync_config.google_account_email,
            "--summary", event.title,
            "--start", start_iso,
            "--end", end_iso,
        ]
        if event.description:
            args += ["--description", event.description]
        if event.location:
            args += ["--location", event.location]

        try:
            result = _run_gws(args)
        except (GwsSyncError, GwsNotFoundError):
            logger.exception(
                "Failed to push event %s to Google Calendar.", event.pk
            )
            continue

        # Store the returned Google event ID to prevent re-pushing
        google_id = result.get("id", "")
        if google_id:
            Event.objects.filter(pk=event.pk).update(google_event_id=google_id)
            count += 1
        else:
            logger.warning(
                "gws returned no ID for pushed event %s; event may be duplicated "
                "on next sync.",
                event.pk,
            )

    return count


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def sync_calendar(sync_config: Any) -> dict[str, int | str]:
    """Run a full sync cycle for one ``GoogleCalendarSync`` configuration.

    Depending on ``sync_direction``:
    - ``"both"`` — pull then push
    - ``"pull"`` — pull only
    - ``"push"`` — push only

    Returns a stats dict with keys ``pulled``, ``pushed``, ``direction``.
    """
    direction = sync_config.sync_direction
    pulled = 0
    pushed = 0

    with transaction.atomic():
        if direction in ("both", "pull"):
            pulled = _pull_from_google(sync_config)

        if direction in ("both", "push"):
            pushed = _push_to_google(sync_config)

    # Update last_synced_at outside the per-event transaction
    type(sync_config).objects.filter(pk=sync_config.pk).update(
        last_synced_at=dj_timezone.now(),
    )

    return {"pulled": pulled, "pushed": pushed, "direction": direction}
