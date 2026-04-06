"""Broadcast agent action updates via WebSocket channel layer."""
from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import AgentAction

logger = logging.getLogger(__name__)


@receiver(post_save, sender=AgentAction)
def broadcast_agent_action_update(
    sender: type,
    instance: AgentAction,
    created: bool,
    **kwargs: object,
) -> None:
    """Push action state to the circle's WS group after every save."""
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    group_name = f"circle_{instance.circle_id}_agents"

    payload = {
        "id": str(instance.pk),
        "action_type": instance.action_type,
        "circle_id": str(instance.circle_id),
        "is_pending": instance.is_pending,
        "is_approved": instance.is_approved,
        "is_rejected": instance.is_rejected,
        "is_executed": instance.is_executed,
        "proposed_at": instance.proposed_at.isoformat() if instance.proposed_at else None,
        "approved_at": instance.approved_at.isoformat() if instance.approved_at else None,
        "rejected_at": instance.rejected_at.isoformat() if instance.rejected_at else None,
    }

    try:
        async_to_sync(channel_layer.group_send)(
            group_name,
            {"type": "agent_action_update", "payload": payload},
        )
    except Exception:
        logger.exception("Failed to broadcast agent action update to %s", group_name)
