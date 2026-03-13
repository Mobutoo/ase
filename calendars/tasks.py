"""Celery tasks for the calendars app.

Periodic tasks
--------------
sync_google_calendars
    Runs every 5 minutes.  Iterates over all enabled ``GoogleCalendarSync``
    configs and performs bidirectional sync via the ``gws`` CLI.

refresh_ical_subscriptions
    Runs every 5 minutes.  Fetches all enabled iCal URL subscriptions and
    upserts / prunes imported events.
"""

from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="calendars.tasks.sync_google_calendars")
def sync_google_calendars() -> dict[str, list]:
    """Sync all enabled Google Calendar configurations.

    Returns a summary dict with ``"ok"`` and ``"errors"`` lists for observability.
    """
    from calendars.models import GoogleCalendarSync
    from calendars.sync.google import GwsNotFoundError, sync_calendar

    syncs = GoogleCalendarSync.objects.filter(enabled=True).select_related(
        "ase_calendar", "member"
    )

    results: dict[str, list] = {"ok": [], "errors": []}

    for sync_config in syncs:
        try:
            stats = sync_calendar(sync_config)
            logger.info("Google sync %s: %s", sync_config.pk, stats)
            results["ok"].append({"id": sync_config.pk, **stats})
        except GwsNotFoundError:
            # Log once and bail out -- no point retrying if the binary is missing
            logger.error(
                "gws CLI not found; aborting Google Calendar sync run."
            )
            results["errors"].append(
                {"id": sync_config.pk, "error": "gws CLI not found"}
            )
            break
        except Exception as exc:
            logger.error(
                "Google sync failed for config %s: %s",
                sync_config.pk,
                exc,
                exc_info=True,
            )
            results["errors"].append({"id": sync_config.pk, "error": str(exc)})

    return results


@shared_task(name="calendars.tasks.sync_google_calendars_single")
def sync_google_calendars_single(sync_config_pk: int) -> dict[str, int | str]:
    """Run a sync cycle for a single GoogleCalendarSync by primary key.

    Used by the ``sync-now`` API action for on-demand sync.
    """
    from calendars.models import GoogleCalendarSync
    from calendars.sync.google import sync_calendar

    try:
        sync_config = GoogleCalendarSync.objects.select_related(
            "ase_calendar", "member"
        ).get(pk=sync_config_pk)
    except GoogleCalendarSync.DoesNotExist:
        logger.warning("GoogleCalendarSync %s does not exist.", sync_config_pk)
        return {"error": "not found"}

    stats = sync_calendar(sync_config)
    logger.info("Google sync (on-demand) %s: %s", sync_config.pk, stats)
    return stats


# ---------------------------------------------------------------------------
# iCal URL subscription sync
# ---------------------------------------------------------------------------


@shared_task(name="calendars.tasks.refresh_ical_subscriptions")
def refresh_ical_subscriptions() -> None:
    """Fetch all enabled iCal subscriptions and sync events.

    Runs periodically via Celery beat.  Each subscription is processed
    independently so that a single failure does not block the others.
    """
    from calendars.models import CalendarSubscription

    subs = CalendarSubscription.objects.filter(enabled=True).select_related("member")
    for sub in subs:
        try:
            _refresh_single(sub)
        except Exception as exc:
            logger.error("Failed to refresh subscription %s: %s", sub.pk, exc)


@shared_task(name="calendars.tasks.refresh_single_subscription")
def refresh_single_subscription(subscription_pk: int) -> None:
    """Refresh a single subscription by primary key (used for on-demand refresh)."""
    from calendars.models import CalendarSubscription

    try:
        sub = CalendarSubscription.objects.select_related("member").get(pk=subscription_pk)
    except CalendarSubscription.DoesNotExist:
        logger.warning("Subscription %s does not exist.", subscription_pk)
        return

    try:
        _refresh_single(sub)
    except Exception as exc:
        logger.error("Failed to refresh subscription %s: %s", sub.pk, exc)


def _refresh_single(sub) -> None:
    """Fetch the iCal feed and upsert events for a single subscription."""
    import httpx
    from django.utils import timezone

    from calendars.caldav.ical import events_from_ics
    from calendars.models import Calendar, Event

    headers: dict[str, str] = {}
    if sub.last_etag:
        headers["If-None-Match"] = sub.last_etag

    with httpx.Client(timeout=30.0) as client:
        resp = client.get(str(sub.ical_url), headers=headers, follow_redirects=True)

    if resp.status_code == 304:
        sub.last_fetched_at = timezone.now()
        sub.save(update_fields=["last_fetched_at"])
        return

    resp.raise_for_status()
    raw_ics = resp.text
    new_etag = resp.headers.get("ETag", "")

    parsed_events = events_from_ics(raw_ics)

    # Get or create a dedicated calendar for this subscription
    calendar, _ = Calendar.objects.get_or_create(
        owner=sub.member,
        name=f"[Sub] {sub.display_name}",
        defaults={
            "color": sub.color,
            "caldav_enabled": False,
            "visibility": "family",
        },
    )

    # Track external UIDs from this fetch
    fetched_uids: set[str] = set()
    for ev_data in parsed_events:
        uid = ev_data.get("uid", "")
        if not uid:
            continue
        fetched_uids.add(uid)

        Event.objects.update_or_create(
            ical_uid=uid,
            subscription=sub,
            defaults={
                "calendar": calendar,
                "title": ev_data.get("title", ""),
                "description": ev_data.get("description", ""),
                "location": ev_data.get("location", ""),
                "start_at": ev_data["start_at"],
                "end_at": ev_data["end_at"],
                "all_day": ev_data.get("all_day", False),
                "recurrence_rule": ev_data.get("recurrence_rule"),
                "event_type": "background",
                "visibility": "family",
                "caldav_raw": ev_data.get("raw", ""),
            },
        )

    # Remove events that no longer exist in the feed
    Event.objects.filter(subscription=sub).exclude(ical_uid__in=fetched_uids).delete()

    sub.last_fetched_at = timezone.now()
    sub.last_etag = new_etag
    sub.save(update_fields=["last_fetched_at", "last_etag"])
