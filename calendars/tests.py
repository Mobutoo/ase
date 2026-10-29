from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from app.models import LocalTask
from circles.models import Circle, CircleMember
from .models import Calendar, CalendarSubscription, Event


@override_settings(AGENT_ENABLED=False)
class CalendarIsolationTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.user = users.objects.create_user(username="alice")
        self.other = users.objects.create_user(username="bob")
        self.circle = Circle.objects.create(name="Home", tenant_id="alice")
        other_circle = Circle.objects.create(name="Other", tenant_id="bob")
        self.member = CircleMember.objects.create(user=self.user, circle=self.circle, role="admin", display_name="Alice")
        self.other_member = CircleMember.objects.create(user=self.other, circle=other_circle, role="admin", display_name="Bob")
        self.calendar = Calendar.objects.create(owner=self.member, name="Mine")
        self.other_calendar = Calendar.objects.create(owner=self.other_member, name="Other")
        self.start = datetime(2026, 11, 1, 9, tzinfo=timezone.utc)
        self.event = Event.objects.create(calendar=self.calendar, title="Mine", start_at=self.start, end_at=self.start + timedelta(hours=1))
        self.other_event = Event.objects.create(calendar=self.other_calendar, title="Other", start_at=self.start, end_at=self.start + timedelta(hours=1))
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def payload(self, **overrides):
        data = {"calendar": self.calendar.pk, "title": "New", "start_at": self.start.isoformat(), "end_at": (self.start + timedelta(hours=1)).isoformat()}
        data.update(overrides)
        return data

    def test_create_and_update_cannot_target_another_users_calendar(self):
        response = self.client.post("/api/calendar/events/", self.payload(calendar=self.other_calendar.pk), format="json")
        self.assertEqual(response.status_code, 400)
        response = self.client.patch(f"/api/calendar/events/{self.event.pk}/", {"calendar": self.other_calendar.pk}, format="json")
        self.assertEqual(response.status_code, 400)
        self.event.refresh_from_db()
        self.assertEqual(self.event.calendar, self.calendar)

    def test_related_objects_cannot_cross_users_or_circles(self):
        task = LocalTask.objects.create(user=self.other, title="Private task")
        for relation in ({"parent_event": self.other_event.pk}, {"linked_task": task.pk}, {"members": [self.other_member.pk]}, {"reminders": [{"member": self.other_member.pk, "offset_minutes": 5, "channel": "email"}]}):
            with self.subTest(relation=relation):
                response = self.client.post("/api/calendar/events/", self.payload(**relation), format="json")
                self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(Event.objects.count(), 2)

    def test_calendar_owner_cannot_be_transferred(self):
        response = self.client.patch(f"/api/calendar/calendars/{self.calendar.pk}/", {"owner": self.other_member.pk}, format="json")
        self.assertEqual(response.status_code, 400)
        self.calendar.refresh_from_db()
        self.assertEqual(self.calendar.owner, self.member)

    def test_multicircle_user_can_create_calendar_and_sync(self):
        extra = Circle.objects.create(name="Team", tenant_id="team")
        member = CircleMember.objects.create(user=self.user, circle=extra, role="member", display_name="Alice")
        response = self.client.post("/api/calendar/calendars/", {"name": "Work", "owner": member.pk}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        calendar = Calendar.objects.get(pk=response.data["id"])
        self.assertEqual(calendar.owner, member)
        response = self.client.post("/api/calendar/google-syncs/", {"ase_calendar": calendar.pk, "google_calendar_id": "primary", "google_account_email": "alice@example.com"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["member"], member.pk)
        response = self.client.post("/api/calendar/google-syncs/", {"ase_calendar": self.other_calendar.pk, "google_calendar_id": "primary"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_subscription_events_are_read_only_in_all_edit_actions(self):
        subscription = CalendarSubscription.objects.create(member=self.member, display_name="Feed", ical_url="https://example.com/feed.ics")
        self.event.subscription = subscription
        self.event.recurrence_rule = "FREQ=DAILY"
        self.event.save()
        for action, method in (("edit-this", "post"), ("edit-following", "post"), ("edit-all", "patch")):
            with self.subTest(action=action):
                response = getattr(self.client, method)(f"/api/calendar/events/{self.event.pk}/{action}/", self.payload(original_start=self.start.isoformat()), format="json")
                self.assertEqual(response.status_code, 403)
        self.assertEqual(Event.objects.count(), 2)

    def test_custom_edit_actions_keep_relation_scope(self):
        self.event.recurrence_rule = "FREQ=DAILY"
        self.event.save()
        for action, method in (("edit-this", "post"), ("edit-following", "post"), ("edit-all", "patch")):
            with self.subTest(action=action):
                response = getattr(self.client, method)(f"/api/calendar/events/{self.event.pk}/{action}/", self.payload(calendar=self.other_calendar.pk, original_start=(self.start + timedelta(days=1)).isoformat()), format="json")
                self.assertEqual(response.status_code, 400, response.data)
        self.event.refresh_from_db()
        self.assertEqual(self.event.recurrence_rule, "FREQ=DAILY")

    def test_split_recurrence_uses_exclusive_utc_until(self):
        self.event.recurrence_rule = "FREQ=DAILY;COUNT=10"
        self.event.save()
        response = self.client.post(f"/api/calendar/events/{self.event.pk}/edit-following/", self.payload(original_start="2026-11-02T10:00:00+01:00", recurrence_rule="FREQ=DAILY"), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.event.refresh_from_db()
        self.assertEqual(self.event.recurrence_rule, "FREQ=DAILY;UNTIL=20261102T085959Z")

    def test_invalid_occurrence_timestamp_is_validation_error(self):
        self.event.recurrence_rule = "FREQ=DAILY"
        self.event.save()
        response = self.client.post(f"/api/calendar/events/{self.event.pk}/edit-this/", self.payload(original_start="invalid"), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Event.objects.count(), 2)

    def ics(self):
        return "\r\n".join(["BEGIN:VCALENDAR", "VERSION:2.0", "BEGIN:VEVENT", "UID:test-import", "DTSTART:20261101T090000Z", "DTEND:20261101T100000Z", "SUMMARY:Imported", "END:VEVENT", "END:VCALENDAR", ""])

    def test_json_import_confirmation_works(self):
        response = self.client.post("/api/calendar/ics/import/", {"calendar_id": self.calendar.pk, "uids": ["test-import"], "ics_payload": self.ics()}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(Event.objects.filter(calendar=self.calendar, title="Imported").exists())

    def test_import_preview_does_not_disclose_other_users_busy_times(self):
        self.event.delete()
        response = self.client.post("/api/calendar/ics/import/", {"ics_file": SimpleUploadedFile("events.ics", self.ics().encode())}, format="multipart")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data["preview"][0]["conflict"])

    @override_settings(AGENT_ENABLED=True)
    @patch("agents.tasks.process_event_graph.delay")
    def test_graph_task_is_deferred_until_commit_and_honors_circle_flag(self, delay):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            Event.objects.create(calendar=self.calendar, title="Pending", start_at=self.start, end_at=self.start + timedelta(hours=1))
            delay.assert_not_called()
        self.assertEqual(len(callbacks), 1)
        delay.assert_called_once()
        delay.reset_mock()
        self.circle.agent_enabled = False
        self.circle.save()
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            Event.objects.create(calendar=self.calendar, title="Disabled", start_at=self.start, end_at=self.start + timedelta(hours=1))
        self.assertEqual(callbacks, [])
        delay.assert_not_called()

    @override_settings(AGENT_ENABLED=True)
    @patch("agents.tasks.process_event_graph.delay")
    def test_rolled_back_event_does_not_trigger_graph(self, delay):
        with self.captureOnCommitCallbacks(execute=True):
            try:
                with transaction.atomic():
                    Event.objects.create(calendar=self.calendar, title="Rollback", start_at=self.start, end_at=self.start + timedelta(hours=1))
                    raise ValueError("rollback")
            except ValueError:
                pass
        delay.assert_not_called()

    def caldav_request(self, method, event=None, body=None, **headers):
        from django.test import RequestFactory
        from .caldav.views import CalDavEventView

        event = event or self.event
        request = RequestFactory().generic(method, "/caldav/", data=body or b"", content_type="text/calendar", **headers)
        with patch("calendars.caldav.auth.authenticate_caldav", return_value=self.user):
            return CalDavEventView.as_view()(request, username=self.user.username, calendar_id=event.calendar_id, uid=str(event.uid))

    def test_caldav_cannot_modify_or_delete_subscribed_events(self):
        from .caldav.ical import event_to_ics
        from .caldav.views import _wrap_vcalendar

        sub = CalendarSubscription.objects.create(member=self.member, display_name="Feed", ical_url="https://example.com/feed.ics")
        self.event.subscription = sub
        self.event.save()
        self.assertEqual(self.caldav_request("DELETE").status_code, 403)
        payload = _wrap_vcalendar(event_to_ics(self.event)).encode()
        self.assertEqual(self.caldav_request("PUT", body=payload).status_code, 403)
        self.assertTrue(Event.objects.filter(pk=self.event.pk).exists())

    def test_caldav_update_changes_etag_and_rejects_stale_delete(self):
        from .caldav.ical import event_to_ics
        from .caldav.views import _wrap_vcalendar

        self.event.etag = "original"
        self.event.save(update_fields=["etag"])
        self.event.title = "Updated"
        response = self.caldav_request("PUT", body=_wrap_vcalendar(event_to_ics(self.event)).encode(), HTTP_IF_MATCH='"original"')
        self.assertEqual(response.status_code, 204)
        self.event.refresh_from_db()
        first_etag = self.event.etag
        self.event.title = "Updated again"
        self.event.caldav_raw = ""
        response = self.caldav_request("PUT", body=_wrap_vcalendar(event_to_ics(self.event)).encode(), HTTP_IF_MATCH=f'"{first_etag}"')
        self.assertEqual(response.status_code, 204)
        self.event.refresh_from_db()
        self.assertNotEqual(first_etag, self.event.etag)
        self.assertEqual(self.caldav_request("DELETE", HTTP_IF_MATCH=f'"{first_etag}"').status_code, 412)
        self.assertTrue(Event.objects.filter(pk=self.event.pk).exists())

    def test_caldav_rejects_mismatched_payload_uid(self):
        from .caldav.ical import event_to_ics
        from .caldav.views import _wrap_vcalendar

        response = self.caldav_request("PUT", body=_wrap_vcalendar(event_to_ics(self.other_event)).encode())
        self.assertEqual(response.status_code, 409)
        self.assertEqual(Event.objects.count(), 2)

    def test_ics_export_normalizes_timezone_and_reflects_rest_edits(self):
        from .caldav.ical import event_to_ics

        self.event.start_at = self.start.astimezone(timezone(timedelta(hours=2)))
        self.event.end_at = (self.start + timedelta(hours=1)).astimezone(timezone(timedelta(hours=2)))
        raw = event_to_ics(self.event)
        self.assertIn("DTSTART:20261101T090000Z", raw)
        self.event.caldav_raw = raw
        self.event.save()
        response = self.client.patch(f"/api/calendar/events/{self.event.pk}/", {"title": "Changed in REST"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.event.refresh_from_db()
        self.assertIn("SUMMARY:Changed in REST", event_to_ics(self.event))

    def test_invalid_event_query_filters_return_400(self):
        for params in ({"start": "not-a-date"}, {"end": "2026-99-99"}, {"calendar": "not-an-id"}, {"calendar": -1}, {"start": "2026-11-02T10:00:00Z", "end": "2026-11-01T10:00:00Z"}):
            with self.subTest(params=params):
                response = self.client.get("/api/calendar/events/", params)
                self.assertEqual(response.status_code, 400, response.data)
        response = self.client.get("/api/calendar/events/", {"start": "2026-11-01T08:00:00Z", "end": "2026-11-01T11:00:00Z", "calendar": self.calendar.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def basic_request(self, password):
        import base64
        from django.test import RequestFactory

        encoded = base64.b64encode(f"{self.user.username}:{password}".encode()).decode()
        return RequestFactory().get("/caldav/", HTTP_AUTHORIZATION=f"Basic {encoded}")

    def test_caldav_application_password_supports_oidc_users_and_records_usage(self):
        from django.contrib.auth.hashers import make_password
        from iam.models import AppSpecificPassword
        from .caldav.auth import authenticate_caldav

        self.assertFalse(self.user.has_usable_password())
        app_password = AppSpecificPassword.objects.create(user=self.user, name="Calendar", password_hash=make_password("application-password"))
        self.assertEqual(authenticate_caldav(self.basic_request("application-password")), self.user)
        app_password.refresh_from_db()
        self.assertIsNotNone(app_password.last_used_at)
        app_password.delete()
        self.assertIsNone(authenticate_caldav(self.basic_request("application-password")))

    def test_caldav_rejects_expired_passwords_and_disabled_users(self):
        from django.contrib.auth.hashers import make_password
        from django.utils import timezone as django_timezone
        from iam.models import AppSpecificPassword
        from .caldav.auth import authenticate_caldav

        app_password = AppSpecificPassword.objects.create(user=self.user, name="Expired", password_hash=make_password("application-password"), expires_at=django_timezone.now() - timedelta(seconds=1))
        self.assertIsNone(authenticate_caldav(self.basic_request("application-password")))
        app_password.expires_at = None
        app_password.save()
        self.user.is_active = False
        self.user.save()
        self.assertIsNone(authenticate_caldav(self.basic_request("application-password")))

    def test_caldav_keeps_local_password_support_and_rejects_malformed_basic(self):
        from django.test import RequestFactory
        from .caldav.auth import authenticate_caldav, parse_basic_auth

        self.user.set_password("local-password")
        self.user.save()
        self.assertEqual(authenticate_caldav(self.basic_request("local-password")), self.user)
        for header in ("Basic !!!", "Basic YWxpY2U=", "Bearer token", "Basic " + "a" * 2000):
            with self.subTest(header=header[:20]):
                request = RequestFactory().get("/caldav/", HTTP_AUTHORIZATION=header)
                self.assertIsNone(parse_basic_auth(request))
