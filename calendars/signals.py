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

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)

# Fields that, when changed, should re-trigger event graph analysis
_TRIGGER_FIELDS = frozenset(["title", "location", "start_at", "end_at", "event_type"])


@receiver(post_save, sender="calendars.Event")
def on_event_save_trigger_graph(sender, instance, created, update_fields, **kwargs):
    """Fire process_event_graph when a relevant event is saved."""
    event = instance

    # Guard: skip background and dependent events
    if event.event_type in ("background", "dependent"):
        return

    # Guard: skip all-day events (no transport timing possible)
    if event.all_day:
        return

    # Guard: skip subscribed (imported) events
    if getattr(event, "is_subscribed", False):
        return

    # Guard: on update, only trigger if relevant fields changed
    if not created and update_fields is not None:
        changed = set(update_fields) if update_fields else set()
        if not changed.intersection(_TRIGGER_FIELDS):
            return

    # Fire the async task
    try:
        from agents.tasks import process_event_graph
        process_event_graph.delay(event.pk)
        logger.info(
            "Event Graph triggered for event %s (%s) — created=%s",
            event.pk, event.title, created,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to trigger event graph for event %s: %s", event.pk, exc)
