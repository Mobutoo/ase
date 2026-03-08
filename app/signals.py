"""
Django signals for the app module.

Auto-sends webhook to n8n when a session is completed.
Errors in the webhook call never crash the save — all exceptions are caught
inside send_session_event itself.
"""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Session
from .webhooks import send_session_event

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Session)
def on_session_save(sender, instance, created, **kwargs):
    """Fire n8n webhook when a session is completed."""
    if instance.completed and instance.ended_at:
        result = send_session_event(instance)
        if result is True:
            logger.info(
                "Session webhook sent successfully for session_id=%s user=%s",
                instance.pk,
                instance.user.username,
            )
        elif result is False:
            logger.warning(
                "Session webhook failed for session_id=%s user=%s",
                instance.pk,
                instance.user.username,
            )
        # result is None → webhook not configured, no action needed
