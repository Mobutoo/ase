"""Privacy regressions for the compatibility API used by legacy clients."""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings

from app.models import Pomodoro, Tag, UserSettings


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
)
class LegacyProfilePrivacyTests(TestCase):
    personal_endpoints = ("alltags", "alldates", "allpomodoros")

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user(username="private-owner")
        cls.other = User.objects.create_user(username="another-user")
        cls.public = User.objects.create_user(username="public-owner")
        cls.without_settings = User.objects.create_user(username="no-settings")
        cls.private_settings = UserSettings.objects.create(
            user=cls.owner, profile_public=False, token="original-api-token"
        )
        cls.public_settings = UserSettings.objects.create(
            user=cls.public, profile_public=True
        )
        tag = Tag.objects.create(tag="PRIVATE_ACTIVITY")
        Pomodoro.objects.create(user=cls.owner, tag=tag)
        Pomodoro.objects.create(user=cls.public, tag=tag)

    def setUp(self):
        cache.clear()

    def profile_url(self, username, endpoint):
        return f"/api/{username}/{endpoint}"

    def test_anonymous_cannot_read_private_profiles(self):
        for endpoint in self.personal_endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(self.profile_url(self.owner.username, endpoint))
                self.assertEqual(response.status_code, 404)
                self.assertNotContains(response, "PRIVATE_ACTIVITY", status_code=404)

    def test_other_authenticated_user_cannot_read_private_profiles(self):
        self.client.force_login(self.other)
        for endpoint in self.personal_endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(self.profile_url(self.owner.username, endpoint))
                self.assertEqual(response.status_code, 404)

    def test_owner_can_read_private_profiles_without_sharing_cached_response(self):
        self.client.force_login(self.owner)
        anonymous = Client()
        for endpoint in self.personal_endpoints:
            with self.subTest(endpoint=endpoint):
                url = self.profile_url(self.owner.username, endpoint)
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertIn("no-store", response.headers["Cache-Control"])
                self.assertIn("private", response.headers["Cache-Control"])
                self.assertEqual(anonymous.get(url).status_code, 404)

    def test_public_profiles_remain_readable(self):
        for endpoint in self.personal_endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(self.profile_url(self.public.username, endpoint))
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.json())

    def test_privacy_change_takes_effect_on_next_request(self):
        for endpoint in self.personal_endpoints:
            self.assertEqual(
                self.client.get(self.profile_url(self.public.username, endpoint)).status_code,
                200,
            )
        UserSettings.objects.filter(pk=self.public_settings.pk).update(profile_public=False)
        for endpoint in self.personal_endpoints:
            with self.subTest(endpoint=endpoint):
                self.assertEqual(
                    self.client.get(self.profile_url(self.public.username, endpoint)).status_code,
                    404,
                )

    def test_missing_settings_does_not_make_a_profile_public(self):
        for endpoint in self.personal_endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(
                    self.profile_url(self.without_settings.username, endpoint)
                )
                self.assertEqual(response.status_code, 404)

    def test_leaderboard_only_includes_public_profiles_and_respects_opt_out(self):
        response = self.client.get("/api/leaderboard")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {self.public.username})
        self.assertIn("no-store", response.headers["Cache-Control"])
        UserSettings.objects.filter(pk=self.public_settings.pk).update(profile_public=False)
        self.assertEqual(self.client.get("/api/leaderboard").json(), {})

    def test_rotated_legacy_token_cannot_read_cached_settings(self):
        url = "/api/original-api-token/getSettings"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response.headers["Cache-Control"])
        UserSettings.objects.filter(pk=self.private_settings.pk).update(token="rotated-api-token")
        self.assertEqual(self.client.get(url).status_code, 401)
