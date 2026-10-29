from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TestCase
from django.utils import timezone

from app.models import Session


class SessionWebhookTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="webhook-user")

    @patch("app.signals.send_session_event")
    def test_completion_waits_for_commit_and_edit_does_not_resend(self, send):
        session = Session.objects.create(user=self.user, mode="pomodoro", planned_duration=25)
        with self.captureOnCommitCallbacks(execute=True):
            session.completed = True
            session.ended_at = timezone.now()
            session.save()
            send.assert_not_called()
        send.assert_called_once()
        with self.captureOnCommitCallbacks(execute=True):
            session.save()
        send.assert_called_once()

    @patch("app.signals.send_session_event")
    def test_rollback_does_not_send(self, send):
        with self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(ValueError), transaction.atomic():
                Session.objects.create(user=self.user, mode="pomodoro", planned_duration=25,
                                       completed=True, ended_at=timezone.now())
                raise ValueError("rollback")
        send.assert_not_called()
