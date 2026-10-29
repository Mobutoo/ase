"""Calendar signals — trigger Event Graph processing on event save.

When a non-background, non-dependent event is created or updated, we
trigger the agent's process_event_graph task to generate dependent
proposals (transport, meal, etc.).

The signal respects the following guards:
- Skips background events (subscriptions, bookings)
- Skips dependent events (agent-generated)
- Skips all-day events (no precise timing for transport)
- Only triggers on create or meaningful field changes
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)

# Fields that, when changed, should re-trigger event graph analysis
_TRIGGER_FIELDS = frozenset(["title", "location", "start_at", "end_at", "event_type"])


@receiver(post_save, sender="calendars.Event")
def on_event_save_trigger_graph(sender, instance, created, update_fields, **kwargs):
    """Fire process_event_graph when a relevant event is saved."""
    event = instance

    if not getattr(settings, "AGENT_ENABLED", False):
        return
    if not event.calendar.owner.circle.agent_enabled:
        return

    # Guard: skip background and dependent events
    if event.event_type in ("background", "dependent"):
        return

    # Guard: skip all-day events (no transport timing possible)
    if event.all_day:
        return

    # Guard: skip subscribed (imported) events
    if event.subscription_id is not None:
        return

    # Guard: on update, only trigger if relevant fields changed
    if not created and update_fields is not None:
        changed = set(update_fields) if update_fields else set()
        if not changed.intersection(_TRIGGER_FIELDS):
            return

    # Schedule only after commit: workers must not see uncommitted/deleted events.
    transaction.on_commit(lambda: _schedule_event_graph(event.pk))


def _schedule_event_graph(event_pk):
    try:
        from agents.tasks import process_event_graph
        process_event_graph.delay(event_pk)
        logger.info(
            "Event Graph triggered for event %s", event_pk,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to trigger event graph for event %s: %s", event_pk, exc)
