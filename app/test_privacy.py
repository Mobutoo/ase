"""Regression coverage for legacy profile visibility and logout CSRF."""
from django.contrib.auth import SESSION_KEY, get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from app.models import UserSettings


class LegacyPagePrivacyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user(username="private-profile")
        cls.other = User.objects.create_user(username="other-profile")
        cls.public = User.objects.create_user(username="public-profile")
        UserSettings.objects.create(user=cls.owner, profile_public=False)
        UserSettings.objects.create(user=cls.public, profile_public=True)

    def test_private_profile_is_hidden_from_anonymous_and_other_users(self):
        url = reverse("profile", kwargs={"username": self.owner.username})
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_owner_can_view_private_profile(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("profile", kwargs={"username": self.owner.username}))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["display"])
        self.assertIn("private", response.headers["Cache-Control"])
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_public_profile_is_readable_until_owner_opts_out(self):
        url = reverse("profile", kwargs={"username": self.public.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["userProfile"], self.public)
        UserSettings.objects.filter(user=self.public).update(profile_public=False)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_unknown_and_missing_settings_profiles_are_not_public(self):
        for username in ("unknown-profile", self.other.username):
            with self.subTest(username=username):
                response = self.client.get(reverse("profile", kwargs={"username": username}))
                self.assertEqual(response.status_code, 404)


class LegacyLogoutTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="logout-user")
        UserSettings.objects.create(user=cls.user)

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.user)

    def test_get_cannot_log_a_user_out(self):
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 405)
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))

    def test_post_without_csrf_cannot_log_a_user_out(self):
        response = self.client.post(reverse("logout"))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))

    def test_navigation_forms_support_csrf_protected_logout(self):
        response = self.client.get(reverse("profile", kwargs={"username": self.user.username}))
        self.assertContains(response, f'method="post" action="{reverse("logout")}"', count=2)
        response = self.client.post(
            reverse("logout"),
            {"csrfmiddlewaretoken": self.client.cookies["csrftoken"].value},
        )
        self.assertRedirects(response, reverse("index"))
        self.assertNotIn(SESSION_KEY, self.client.session)


class UsernameAccountTests(TestCase):
    def test_login_and_signup_pages_render_without_social_providers(self):
        for route in ("account_login", "account_signup"):
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'name="csrfmiddlewaretoken"')
                self.assertNotContains(response, "Sign in with Google")

    def test_username_and_password_login(self):
        user = get_user_model().objects.create_user(
            username="login-account", password="Ase-account-test-2026!"
        )
        response = self.client.post(
            reverse("account_login"),
            {"login": user.username, "password": "Ase-account-test-2026!"},
        )
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.assertEqual(self.client.session[SESSION_KEY], str(user.pk))

    def test_signup_with_username_and_password_without_email(self):
        response = self.client.post(
            reverse("account_signup"),
            {
                "username": "new-account",
                "password1": "Ase-account-test-2026!",
                "password2": "Ase-account-test-2026!",
            },
        )
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        user = get_user_model().objects.get(username="new-account")
        self.assertEqual(self.client.session[SESSION_KEY], str(user.pk))
