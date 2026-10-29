from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from app.models import AISuggestion, EnergyReading, Session, UserSettings


class EnergyOwnershipTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="energy-owner")
        other = get_user_model().objects.create_user(username="energy-other")
        self.session = Session.objects.create(user=self.user, planned_duration=25)
        self.other_session = Session.objects.create(user=other, planned_duration=25)
        self.client.force_authenticate(self.user)

    def test_energy_cannot_reference_another_users_session(self):
        response = self.client.post("/api/v1/energy/", {
            "level": 3, "session": self.other_session.pk,
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(EnergyReading.objects.exists())

    def test_energy_can_reference_own_session_or_no_session(self):
        for session_id in (self.session.pk, None):
            response = self.client.post("/api/v1/energy/", {
                "level": 3, "session": session_id,
            }, format="json")
            self.assertEqual(response.status_code, 201)
        self.assertEqual(EnergyReading.objects.filter(user=self.user).count(), 2)


class WebhookSecurityTests(APITestCase):
    def setUp(self):
        get_user_model().objects.create_user(username="webhook-owner")
        self.payload = {
            "event": "daily_plan", "user": "webhook-owner", "content": {"tasks": []},
        }

    @override_settings(N8N_WEBHOOK_SECRET="")
    def test_unconfigured_webhook_is_disabled(self):
        response = self.client.post("/api/v1/webhooks/", self.payload, format="json")
        self.assertEqual(response.status_code, 503)
        self.assertFalse(AISuggestion.objects.exists())

    @override_settings(N8N_WEBHOOK_SECRET="test-webhook-secret")
    def test_missing_and_wrong_secrets_are_rejected(self):
        for secret in ("", "wrong", "non-ascii-é"):
            response = self.client.post("/api/v1/webhooks/", self.payload, format="json",
                                        HTTP_X_WEBHOOK_SECRET=secret)
            self.assertEqual(response.status_code, 403)
        self.assertFalse(AISuggestion.objects.exists())

    @override_settings(N8N_WEBHOOK_SECRET="test-webhook-secret")
    def test_authenticated_webhook_creates_suggestion(self):
        response = self.client.post("/api/v1/webhooks/", self.payload, format="json",
                                    HTTP_X_WEBHOOK_SECRET="test-webhook-secret")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(AISuggestion.objects.get().user.username, "webhook-owner")

    @override_settings(N8N_WEBHOOK_SECRET="test-webhook-secret")
    def test_malformed_payload_returns_validation_error(self):
        for payload in ([], {**self.payload, "event": []}, {**self.payload, "user": {}},
                        {**self.payload, "content": "not structured data"}):
            response = self.client.post("/api/v1/webhooks/", payload, format="json",
                                        HTTP_X_WEBHOOK_SECRET="test-webhook-secret")
            self.assertEqual(response.status_code, 400)
        self.assertFalse(AISuggestion.objects.exists())


class SettingsCompatibilityTests(APITestCase):
    def test_settings_maps_keep_flow_identifiers_on_read_and_write(self):
        user = get_user_model().objects.create_user(username="settings-maps")
        self.client.force_authenticate(user)
        labels = {"deep_work": ["ComplexTask", "research_notes"], "free_flow": ["CreativeWork"]}
        playlists = {
            "deep_work": "https://www.youtube.com/playlist?list=deep_work",
            "free_flow": "https://www.youtube.com/playlist?list=free_flow",
        }
        saved = UserSettings.objects.create(
            user=user, mode_label_map=labels, youtube_default_playlists=playlists,
        )
        response = self.client.get("/api/v1/settings/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["modeLabelMap"], labels)
        self.assertEqual(response.json()["youtubeDefaultPlaylists"], playlists)

        labels["deep_work"] = ["UpdatedLabel"]
        playlists["free_flow"] = "https://www.youtube.com/playlist?list=updated"
        response = self.client.patch("/api/v1/settings/", {
            "modeLabelMap": labels, "youtubeDefaultPlaylists": playlists,
            "deepWorkDuration": 110, "focusTime": 40,
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["modeLabelMap"], labels)
        self.assertEqual(response.json()["youtubeDefaultPlaylists"], playlists)
        self.assertEqual(response.json()["deepWorkDuration"], 110)
        self.assertEqual(response.json()["focusTime"], 40)
        saved.refresh_from_db()
        self.assertEqual(saved.mode_label_map, labels)
        self.assertEqual(saved.youtube_default_playlists, playlists)

    def test_camel_case_settings_are_persisted(self):
        user = get_user_model().objects.create_user(username="settings-owner")
        self.client.force_authenticate(user)
        response = self.client.patch("/api/v1/settings/", {
            "focusTime": 45, "shortBreak": 7, "longBreak": 20,
            "startSound": "#ding", "stopSound": "#whoosh",
            "focusColor": "#112233", "breakColor": "#445566",
            "deepWorkDuration": 100, "profilePublic": True,
        }, format="json")
        self.assertEqual(response.status_code, 200)
        saved = UserSettings.objects.get(user=user)
        self.assertEqual(saved.focusTime, 45)
        self.assertEqual(saved.shortBreak, 7)
        self.assertEqual(saved.longBreak, 20)
        self.assertEqual(saved.focusColor, "#112233")
        self.assertEqual(saved.breakColor, "#445566")
        self.assertEqual(saved.deep_work_duration, 100)
        self.assertTrue(saved.profile_public)
