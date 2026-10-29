import time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from circles.models import Circle, CircleMember
from circles.views import _build_invite_token, _INVITE_TTL_SECONDS


class CircleAccessTests(APITestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="circle-owner")
        self.other = get_user_model().objects.create_user(username="circle-other")
        self.client.force_authenticate(self.owner)

    def create_circle(self, **extra):
        response = self.client.post("/api/circles/", {"name": "Family", **extra}, format="json")
        self.assertEqual(response.status_code, 201)
        return Circle.objects.get(pk=response.data["id"])

    def test_creator_is_admin_and_circle_remains_accessible(self):
        circle = self.create_circle(tenantId="spoofed")
        self.assertEqual(circle.tenant_id, str(self.owner.pk))
        self.assertEqual(circle.members.get(user=self.owner).role, "admin")
        self.assertEqual(self.client.get(f"/api/circles/{circle.pk}/").status_code, 200)
        self.assertEqual(self.client.patch(f"/api/circles/{circle.pk}/", {
            "name": "Updated", "tenantId": str(self.other.pk),
        }, format="json").status_code, 200)
        circle.refresh_from_db()
        self.assertEqual(circle.tenant_id, str(self.owner.pk))

    def test_duplicate_primary_returns_validation_error(self):
        self.create_circle(isPrimary=True)
        response = self.client.post("/api/circles/", {
            "name": "Duplicate", "isPrimary": True,
        }, format="json")
        self.assertEqual(response.status_code, 400)

    def test_outsider_cannot_read_or_change_circle(self):
        circle = self.create_circle()
        self.client.force_authenticate(self.other)
        for method in (self.client.get, self.client.patch, self.client.delete):
            self.assertEqual(method(f"/api/circles/{circle.pk}/").status_code, 404)

    def test_member_list_does_not_disclose_invitation_credentials(self):
        circle = self.create_circle()
        member = CircleMember.objects.create(
            user=self.other, circle=circle, role="guest", display_name="Guest",
            invite_token=_build_invite_token(circle.pk, "guest"),
        )
        response = self.client.get(f"/api/circles/{circle.pk}/members/{member.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("invite_token", response.data)
        self.assertNotIn(member.invite_token, response.content.decode())

    def test_valid_invite_can_be_accepted(self):
        circle = self.create_circle()
        token = _build_invite_token(circle.pk, "guest")
        self.client.force_authenticate(self.other)
        response = self.client.post(f"/api/circles/{circle.pk}/accept_invite/", {
            "token": token, "displayName": "Invited", "avatarColor": "#12abEF",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        member = circle.members.get(user=self.other)
        self.assertEqual(member.display_name, "Invited")
        self.assertEqual(member.role, "guest")

    def test_invalid_expired_future_and_obsolete_invites_are_rejected(self):
        circle = self.create_circle()
        tokens = [f"{circle.pk}.guest.{int(time.time())}.nonce.é", "malformed"]
        for offset in (-_INVITE_TTL_SECONDS - 60, 60):
            with patch("circles.views.time.time", return_value=time.time() + offset):
                tokens.append(_build_invite_token(circle.pk, "guest"))
        tokens.append(_build_invite_token(circle.pk, "player"))
        self.client.force_authenticate(self.other)
        for token in tokens:
            response = self.client.post(f"/api/circles/{circle.pk}/accept_invite/",
                                        {"token": token}, format="json")
            self.assertEqual(response.status_code, 400)
        self.assertFalse(circle.members.filter(user=self.other).exists())

    def test_invalid_invite_profile_is_rejected(self):
        circle = self.create_circle()
        token = _build_invite_token(circle.pk, "guest")
        self.client.force_authenticate(self.other)
        for profile in ({"avatarColor": "#zzzzzz"}, {"displayName": "x" * 101},
                        {"avatarEmoji": "x" * 11}):
            response = self.client.post(f"/api/circles/{circle.pk}/accept_invite/",
                                        {"token": token, **profile}, format="json")
            self.assertEqual(response.status_code, 400)

    def test_guest_cannot_change_role_or_another_profile(self):
        circle = self.create_circle()
        guest = CircleMember.objects.create(user=self.other, circle=circle, role="guest",
                                            display_name="Guest")
        self.client.force_authenticate(self.other)
        response = self.client.patch(f"/api/circles/{circle.pk}/members/{guest.pk}/",
                                    {"role": "admin"}, format="json")
        self.assertEqual(response.status_code, 403)
        response = self.client.patch(f"/api/circles/{circle.pk}/members/{guest.pk}/",
                                    {"avatarColor": "#zzzzzz"}, format="json")
        self.assertEqual(response.status_code, 400)
        admin = circle.members.get(user=self.owner)
        response = self.client.patch(f"/api/circles/{circle.pk}/members/{admin.pk}/",
                                    {"displayName": "Hijacked"}, format="json")
        self.assertEqual(response.status_code, 403)
