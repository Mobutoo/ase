"""Send completion webhooks after the database transaction commits."""
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Session
from .webhooks import send_session_event


@receiver(pre_save, sender=Session)
def remember_completion(sender, instance, using, raw=False, **kwargs):
    if raw:
        return
    instance._was_complete = bool(instance.pk and sender.objects.using(using).filter(
        pk=instance.pk, completed=True, ended_at__isnull=False,
    ).exists())


@receiver(post_save, sender=Session)
def on_session_save(sender, instance, using, raw=False, **kwargs):
    if raw or getattr(instance, "_was_complete", False):
        return
    if not instance.completed or not instance.ended_at:
        return
    session_pk = instance.pk

    def notify():
        session = sender.objects.using(using).filter(
            pk=session_pk, completed=True, ended_at__isnull=False,
        ).select_related("user").first()
        if session is not None:
            send_session_event(session)

    transaction.on_commit(notify, using=using)
