from __future__ import annotations

"""Celery tasks for the agents app.

All tasks follow the human-in-the-loop constraint:
- process_event_graph creates PENDING AgentAction proposals only.
- execute_agent_action executes an action ONLY after it has been approved.
- send_weekly_digest runs Sunday evenings for all agent-enabled circles.

Rate limiting: AGENT_RATE_LIMIT env var (default "20/h").
"""

import logging
import os
from datetime import date, timedelta

logger = logging.getLogger(__name__)

# Rate limit for agent proposal creation
AGENT_RATE_LIMIT = os.environ.get("AGENT_RATE_LIMIT", "20/h")

try:
    from celery import shared_task
    _celery_available = True
except ImportError:
    _celery_available = False
    logger.warning(
        "Celery not installed — tasks are defined as no-ops. "
        "Install celery to enable async processing."
    )

    def shared_task(*args, **kwargs):  # type: ignore[misc]
        """Fallback decorator when Celery is not available."""
        def decorator(fn):
            def wrapper(*a, **kw):
                logger.warning("Celery not available, running task synchronously: %s", fn.__name__)
                return fn(*a, **kw)
            wrapper.__name__ = fn.__name__
            wrapper.delay = wrapper
            wrapper.apply_async = lambda args=(), kwargs=None, **kw: wrapper(*args, **(kwargs or {}))
            return wrapper
        return decorator if not args else decorator(args[0])


@shared_task(
    bind=True,
    name="agents.tasks.process_event_graph",
    rate_limit=AGENT_RATE_LIMIT,
    max_retries=3,
    default_retry_delay=60,
    ignore_result=False,
)
def process_event_graph(self, event_id: int) -> dict:
    """Analyse an event and create PENDING AgentAction proposals for dependents.

    This task NEVER creates events directly. It only creates AgentAction
    records in PENDING state which require human approval via Telegram or API.

    Args:
        event_id: PK of a calendars.Event instance.

    Returns:
        dict with keys: event_id, proposals_created (int), skipped (int).
    """
    from calendars.models import Event
    from agents.models import AgentAction
    from agents.services.event_graph import generate_dependents
    from agents.services.integrity import compute_hash
    from agents.services.telegram import send_proposal

    try:
        event = Event.objects.select_related(
            "calendar", "calendar__owner", "calendar__owner__circle"
        ).prefetch_related("members").get(pk=event_id)
    except Event.DoesNotExist:
        logger.error("process_event_graph: Event %s not found.", event_id)
        return {"event_id": event_id, "proposals_created": 0, "skipped": 0, "error": "not_found"}

    circle = event.calendar.owner.circle

    if not getattr(circle, "agent_enabled", False):
        logger.info("Agent disabled for circle %s — skipping event graph for event %s.", circle.pk, event_id)
        return {"event_id": event_id, "proposals_created": 0, "skipped": 1}

    proposals = generate_dependents(event)
    created_count = 0

    for payload in proposals:
        try:
            integrity_hash = compute_hash(payload)
            action_type = payload.get("action_type", "event_create")
            action = AgentAction.objects.create(
                circle=circle,
                action_type=action_type,
                payload=payload,
                integrity_hash=integrity_hash,
            )
            created_count += 1
            logger.info("Created AgentAction %s (type=%s) for event %s.", action.pk, action_type, event_id)

            # Send Telegram proposal (fire-and-forget, non-blocking)
            try:
                send_proposal(circle, action)
            except Exception as tg_exc:  # noqa: BLE001
                logger.warning("Telegram send_proposal failed for action %s: %s", action.pk, tg_exc)

        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to create AgentAction for event %s: %s", event_id, exc)

    return {
        "event_id": event_id,
        "proposals_created": created_count,
        "skipped": len(proposals) - created_count,
    }


@shared_task(
    bind=True,
    name="agents.tasks.execute_agent_action",
    max_retries=3,
    default_retry_delay=30,
    ignore_result=False,
)
def execute_agent_action(self, action_id: int) -> dict:
    """Execute an approved AgentAction.

    Guards:
    - Action must be in approved (not pending, not rejected) state.
    - Integrity hash is verified before execution.
    - executed_at is set only after successful execution.
    - On failure, error is stored and the action remains approved (not re-executed).

    Args:
        action_id: PK of an agents.AgentAction instance.
    """
    from django.utils import timezone
    from agents.models import AgentAction
    from agents.services.integrity import verify_action

    try:
        action = AgentAction.objects.select_related("circle").get(pk=action_id)
    except AgentAction.DoesNotExist:
        logger.error("execute_agent_action: AgentAction %s not found.", action_id)
        return {"action_id": action_id, "status": "not_found"}

    if not action.is_approved:
        logger.warning(
            "execute_agent_action: Action %s is not in approved state (state check).",
            action_id,
        )
        return {"action_id": action_id, "status": "not_approved"}

    if action.is_executed:
        logger.info("execute_agent_action: Action %s already executed.", action_id)
        return {"action_id": action_id, "status": "already_executed"}

    # Integrity check
    if not verify_action(action):
        error_msg = f"Integrity check failed for action {action_id} — execution aborted."
        logger.error(error_msg)
        action.error = error_msg
        action.save(update_fields=["error"])
        return {"action_id": action_id, "status": "integrity_error"}

    # Dispatch to correct executor
    action_type = action.action_type
    try:
        if action_type == "event_create":
            _execute_event_create(action)
        elif action_type == "booking_propose":
            _execute_booking_propose(action)
        elif action_type == "event_suggest":
            _execute_event_suggest(action)
        elif action_type == "digest_send":
            _execute_digest_send(action)
        else:
            raise ValueError(f"Unknown action_type: {action_type}")

        action.executed_at = timezone.now()
        action.save(update_fields=["executed_at"])
        logger.info("AgentAction %s executed successfully.", action_id)
        return {"action_id": action_id, "status": "executed"}

    except Exception as exc:  # noqa: BLE001
        error_msg = f"{type(exc).__name__}: {exc}"
        logger.error("execute_agent_action %s failed: %s", action_id, error_msg)
        action.error = error_msg
        action.save(update_fields=["error"])
        try:
            raise self.retry(exc=exc)
        except Exception:
            return {"action_id": action_id, "status": "error", "error": error_msg}


def _execute_event_create(action: object) -> None:
    """Create a calendar Event from an approved event_create AgentAction."""
    from calendars.models import Event, Calendar
    from django.utils import timezone

    payload = action.payload
    calendar = Calendar.objects.get(pk=payload["calendar_id"])
    member_ids = payload.get("members", [])

    from datetime import datetime as _dt
    start_at = _dt.fromisoformat(payload["start_at"])
    end_at_raw = payload.get("end_at")
    end_at = _dt.fromisoformat(end_at_raw) if end_at_raw else None

    event = Event.objects.create(
        calendar=calendar,
        title=payload.get("title", "Agent Event"),
        location=payload.get("location", ""),
        start_at=start_at,
        end_at=end_at or start_at,
        event_type="dependent",
        dependent_type=payload.get("dependent_type"),
    )
    if member_ids:
        event.members.set(member_ids)

    logger.info("Created Event %s (dependent_type=%s) from AgentAction %s.", event.pk, event.dependent_type, action.pk)


def _execute_booking_propose(action: object) -> None:
    """Handle a booking_propose action — currently logs and stores reference."""
    logger.info(
        "Booking proposal noted for action %s — payload: %s",
        action.pk,
        action.payload,
    )
    # Future: integrate with booking APIs (OpenTable, Google Places, etc.)


def _execute_event_suggest(action: object) -> None:
    """Handle an event_suggest action — currently logs."""
    logger.info(
        "Event suggestion noted for action %s — payload: %s",
        action.pk,
        action.payload,
    )


def _execute_digest_send(action: object) -> None:
    """Handle a digest_send action — calls telegram.send_digest."""
    from agents.services.telegram import send_digest
    digest_data = action.payload.get("digest_data", {})
    send_digest(action.circle, digest_data)


@shared_task(
    name="agents.tasks.send_weekly_digest",
    max_retries=2,
    default_retry_delay=300,
    ignore_result=False,
)
def send_weekly_digest() -> dict:
    """Generate and send the weekly digest for all agent-enabled circles.

    Scheduled: Sunday evenings (configure in Celery beat schedule).
    Generates digest for the current week (Mon–Sun) and dispatches
    send_proposal tasks per circle.

    Returns:
        dict with keys: circles_processed, circles_skipped.
    """
    from circles.models import Circle
    from agents.services.digest import generate_digest
    from agents.services.telegram import send_digest as tg_send_digest

    today = date.today()
    # Go back to Monday of the current week
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    circles = Circle.objects.filter(agent_enabled=True)
    processed = 0
    skipped = 0

    for circle in circles:
        try:
            digest_data = generate_digest(circle, week_start, week_end)
            sent = tg_send_digest(circle, digest_data)
            if sent:
                processed += 1
                logger.info("Weekly digest sent for circle %s.", circle.pk)
            else:
                skipped += 1
                logger.info("Weekly digest skipped for circle %s (no Telegram chat).", circle.pk)
        except Exception as exc:  # noqa: BLE001
            logger.error("Weekly digest failed for circle %s: %s", circle.pk, exc)
            skipped += 1

    logger.info(
        "send_weekly_digest complete: %d processed, %d skipped.",
        processed,
        skipped,
    )
    return {"circles_processed": processed, "circles_skipped": skipped}
