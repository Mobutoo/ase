from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import SuspiciousOperation
from django.test import TestCase, override_settings
from django.utils import timezone
from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from rest_framework.test import APIClient

from circles.models import Circle, CircleMember
from .backends import OIDCBackend, _create_or_update_user, _validate_token_claims
from .models import AppSpecificPassword, CircleInviteToken, OIDCIdentity, TrustedExternalIdP
from .serializers import AppSpecificPasswordCreateSerializer

User = get_user_model()


@override_settings(OIDC_OP_ISSUER="https://tenant.example", OIDC_RP_CLIENT_ID="ase")
class OIDCIdentityTests(TestCase):
    def setUp(self):
        self.claims = {"iss": "https://tenant.example", "sub": "subject/1",
                       "email": "member@example.com", "email_verified": True, "name": "Test Member"}
        self.request = SimpleNamespace(session={})
        self.env = patch.dict("os.environ", {"OIDC_AUTO_CREATE_USERS": "1", "OIDC_STAFF_GROUPS": "admin",
                                             "OIDC_SUPERUSER_GROUPS": "superadmin"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def login(self, claims=None, created=True):
        return _create_or_update_user(claims or self.claims, created=created, request=self.request)

    def test_email_does_not_link_existing_local_account(self):
        local = User.objects.create_user(username="local", email=self.claims["email"])
        oidc = self.login()
        self.assertNotEqual(local.pk, oidc.pk)
        self.assertEqual(OIDCIdentity.objects.get(user=oidc).subject, self.claims["sub"])
        self.assertFalse(oidc.has_usable_password())

    def test_subject_is_stable_when_profile_email_changes(self):
        original = self.login()
        claims = {**self.claims, "email": "changed@example.com"}
        updated = self.login(claims, created=False)
        self.assertEqual(original.pk, updated.pk)
        self.assertEqual(updated.email, "changed@example.com")
        self.assertEqual(User.objects.count(), 1)

    def test_same_subject_at_other_issuer_is_a_separate_non_admin_account(self):
        tenant = self.login()
        TrustedExternalIdP.objects.create(issuer_url="https://guest.example", client_id="guest", display_name="Guest")
        external = self.login({**self.claims, "iss": "https://guest.example", "groups": ["admin", "superadmin"]})
        self.assertNotEqual(tenant.pk, external.pk)
        self.assertFalse(external.is_staff)
        self.assertFalse(external.is_superuser)

    def test_similar_subjects_do_not_collide(self):
        first = self.login()
        second = self.login({**self.claims, "sub": "subject1"})
        self.assertNotEqual(first.pk, second.pk)

    def test_unknown_or_missing_issuer_is_rejected(self):
        for issuer in ("", "https://attacker.example"):
            with self.subTest(issuer=issuer), self.assertRaises(SuspiciousOperation):
                self.login({**self.claims, "iss": issuer})
        self.assertEqual(User.objects.count(), 0)

    def test_tenant_roles_are_synced_and_removed(self):
        user = self.login({**self.claims, "groups": ["admin", "superadmin"]})
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        user = self.login(created=False)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_disabled_account_cannot_login_or_restore_session(self):
        user = self.login()
        user.is_active = False
        user.save()
        with self.assertRaises(SuspiciousOperation):
            self.login(created=False)
        self.assertIsNone(OIDCBackend().get_user(user.pk))

    def test_existing_account_can_be_linked_explicitly(self):
        local = User.objects.create_user(username="existing", email=self.claims["email"])
        OIDCIdentity.objects.create(user=local, issuer=self.claims["iss"], subject=self.claims["sub"])
        self.assertEqual(self.login(created=False).pk, local.pk)
        backend = OIDCBackend()
        self.assertEqual(list(backend.filter_users_by_claims(self.claims)), [local])

    def test_invite_joins_existing_account_and_is_consumed_once(self):
        user = self.login()
        circle = Circle.objects.create(name="Team", preset="team", tenant_id="test")
        invite = CircleInviteToken.objects.create(token="invitation", circle_id=circle.pk, role="member",
                                                  email=self.claims["email"], expires_at=timezone.now()+timedelta(hours=1))
        self.request.session["iam_invite_token"] = invite.token
        self.login(created=False)
        member = CircleMember.objects.get(user=user, circle=circle)
        self.assertEqual(member.role, "member")
        invite.refresh_from_db()
        self.assertIsNotNone(invite.used_at)
        self.assertNotIn("iam_invite_token", self.request.session)
        self.request.session["iam_invite_token"] = invite.token
        self.login(created=False)
        self.assertEqual(CircleMember.objects.filter(user=user, circle=circle).count(), 1)

    def test_invite_rejects_mismatched_or_unverified_email(self):
        circle = Circle.objects.create(name="Team", preset="team", tenant_id="test")
        invite = CircleInviteToken.objects.create(token="invitation", circle_id=circle.pk, role="member",
                                                  email="someoneelse@example.com", expires_at=timezone.now()+timedelta(hours=1))
        self.request.session["iam_invite_token"] = invite.token
        with self.assertRaises(SuspiciousOperation):
            self.login()
        invite.refresh_from_db()
        self.assertIsNone(invite.used_at)
        self.assertFalse(CircleMember.objects.exists())
        self.login({**self.claims, "email": invite.email, "email_verified": False})
        invite.refresh_from_db()
        self.assertIsNone(invite.used_at)
        self.assertFalse(CircleMember.objects.exists())

    def test_userinfo_subject_must_match_token_and_cannot_override_issuer(self):
        backend = OIDCBackend()
        with patch.object(OIDCAuthenticationBackend, "get_userinfo", return_value={"sub": "wrong"}):
            with self.assertRaises(SuspiciousOperation):
                backend.get_userinfo("access", "token", self.claims)
        with patch.object(OIDCAuthenticationBackend, "get_userinfo", return_value={"sub": self.claims["sub"], "iss": "attacker"}):
            self.assertEqual(backend.get_userinfo("access", "token", self.claims)["iss"], self.claims["iss"])

    def test_token_claims_validate_issuer_audience_lifetime_and_authorized_party(self):
        now = timezone.now().timestamp()
        token = {**self.claims, "aud": "ase", "iat": now - 10, "exp": now + 300}
        _validate_token_claims(token)
        invalid = [{"iss": "https://attacker.example"}, {"aud": "another-app"}, {"exp": now-1},
                   {"iat": now+120}, {"sub": ""}, {"exp": "tomorrow"}, {"exp": float("nan")},
                   {"aud": ["ase", "other"]}, {"azp": "other"}, {"nbf": now+120}]
        for change in invalid:
            with self.subTest(change=change), self.assertRaises(SuspiciousOperation):
                _validate_token_claims({**token, **change})
        _validate_token_claims({**token, "aud": ["ase", "other"], "azp": "ase"})


class AppPasswordTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="member")
        self.password = "a-long-application-password"
        serializer = AppSpecificPasswordCreateSerializer(data={"name": "Calendar", "password": self.password},
                                                         context={"request": SimpleNamespace(user=self.user)})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.app_password = serializer.save()
        self.client = APIClient()

    def verify(self, **overrides):
        return self.client.post("/iam/app-passwords/verify/",
                                {"username": self.user.username, "password": self.password, **overrides}, format="json")

    def test_created_password_works_without_optional_bcrypt_hasher(self):
        self.assertTrue(self.app_password.check_password(self.password))
        self.assertEqual(self.verify().status_code, 200)
        self.app_password.refresh_from_db()
        self.assertIsNotNone(self.app_password.last_used_at)

    def test_disabled_and_expired_credentials_are_rejected(self):
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.verify().status_code, 401)
        self.user.is_active = True
        self.user.save()
        self.app_password.expires_at = timezone.now()-timedelta(seconds=1)
        self.app_password.save()
        self.assertEqual(self.verify().status_code, 401)

    def test_malformed_input_is_a_validation_error(self):
        self.assertEqual(self.verify(username=["unexpected"]).status_code, 400)

    def test_verification_is_rate_limited(self):
        for _ in range(10):
            self.assertEqual(self.verify(password="incorrect").status_code, 401)
        self.assertEqual(self.verify(password="incorrect").status_code, 429)


class AdminSecretTests(TestCase):
    def test_staff_admin_forms_do_not_render_client_secrets(self):
        from django.contrib import admin
        from .admin import OIDCConfigAdmin, TrustedExternalIdPAdmin
        from .models import OIDCConfig

        staff = User.objects.create_user(username="staff", is_staff=True)
        request = SimpleNamespace(user=staff)
        for model, model_admin in ((OIDCConfig, OIDCConfigAdmin), (TrustedExternalIdP, TrustedExternalIdPAdmin)):
            with self.subTest(model=model.__name__):
                fieldsets = model_admin(model, admin.site).get_fieldsets(request)
                fields = [field for _, options in fieldsets for field in options["fields"]]
                self.assertNotIn("client_secret", fields)
