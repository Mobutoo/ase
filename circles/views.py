from __future__ import annotations

"""
ViewSets for the circles app.

Endpoints
---------
CircleViewSet
  GET    /circles/                    list all circles for the current tenant
  POST   /circles/                    create a new circle
  GET    /circles/{id}/               retrieve a circle
  PATCH  /circles/{id}/               update a circle (admin only)
  DELETE /circles/{id}/               delete a circle (admin only)
  POST   /circles/{id}/invite/        generate an invite token
  POST   /circles/{id}/accept_invite/ accept an invite token

CircleMemberViewSet  (nested under /circles/{circle_pk}/members/)
  GET    /circles/{circle_pk}/members/             list members
  GET    /circles/{circle_pk}/members/{id}/        retrieve member
  PATCH  /circles/{circle_pk}/members/{id}/        update role / display_name
  DELETE /circles/{circle_pk}/members/{id}/        remove member
"""

import hashlib
import hmac
import logging
import secrets
import time

from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from circles.models import Circle, CircleMember
from circles.permissions import (
    IsCircleAdmin,
    IsCircleAdult,
    IsCircleGuest,
    IsCircleMemberOrAdmin,
)
from circles.serializers import (
    CircleCreateSerializer,
    CircleMemberSerializer,
    CircleMemberUpdateRoleSerializer,
    CircleSerializer,
    InviteAcceptSerializer,
    InviteCreateSerializer,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Invite token helpers
# ---------------------------------------------------------------------------

_INVITE_TTL_SECONDS = 7 * 24 * 3600  # 7 days


def _build_invite_token(circle_id: int, role: str) -> str:
    """Generate a time-scoped HMAC invite token."""
    secret = settings.SECRET_KEY.encode()
    nonce = secrets.token_hex(8)
    timestamp = int(time.time())
    message = f"{circle_id}:{role}:{timestamp}:{nonce}".encode()
    sig = hmac.new(secret, message, hashlib.sha256).hexdigest()
    return f"{circle_id}.{role}.{timestamp}.{nonce}.{sig}"


def _verify_invite_token(token: str) -> tuple[int, str] | None:
    """
    Verify the HMAC invite token.

    Returns ``(circle_id, role)`` on success, ``None`` on failure / expiry.
    """
    try:
        parts = token.split(".")
        if len(parts) != 5:
            return None
        circle_id_str, role, timestamp_str, nonce, sig = parts
        timestamp = int(timestamp_str)
    except (ValueError, AttributeError):
        return None

    # Expiry check
    if int(time.time()) - timestamp > _INVITE_TTL_SECONDS:
        return None

    # Signature check (constant-time comparison)
    secret = settings.SECRET_KEY.encode()
    message = f"{circle_id_str}:{role}:{timestamp_str}:{nonce}".encode()
    expected_sig = hmac.new(secret, message, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected_sig):
        return None

    return int(circle_id_str), role


# ---------------------------------------------------------------------------
# CircleViewSet
# ---------------------------------------------------------------------------

class CircleViewSet(viewsets.ModelViewSet):
    """
    CRUD for circles. The current user's tenant_id is derived from their
    User PK — every user is implicitly a tenant.

    Permission matrix:
      list / retrieve  → any authenticated user (filtered to own tenant)
      create           → any authenticated user
      update / partial → IsCircleAdmin
      destroy          → IsCircleAdmin
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return CircleCreateSerializer
        return CircleSerializer

    def get_queryset(self):
        # A user can only see circles where they are a member (the tenant
        # relationship is mediated by CircleMember, not tenant_id alone,
        # because federated members from other tenants may join).
        user = self.request.user
        return Circle.objects.filter(members__user=user).distinct()

    def get_object(self) -> Circle:
        circle = super().get_object()
        return circle

    def _assert_admin(self, circle: Circle) -> None:
        """Raise PermissionDenied if the requesting user is not an admin."""
        perm = IsCircleAdmin()
        if not perm.has_object_permission(self.request, self, circle):
            raise PermissionDenied("Only circle admins can perform this action.")

    def update(self, request: Request, *args, **kwargs) -> Response:
        circle = self.get_object()
        self._assert_admin(circle)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        circle = self.get_object()
        self._assert_admin(circle)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        circle = self.get_object()
        self._assert_admin(circle)
        return super().destroy(request, *args, **kwargs)

    # ------------------------------------------------------------------
    # Custom actions
    # ------------------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="invite")
    def invite(self, request: Request, pk: str | None = None) -> Response:
        """
        Generate an HMAC invite token for a new member.

        Only circle admins can generate invites.
        """
        circle = self.get_object()
        self._assert_admin(circle)

        serializer = InviteCreateSerializer(
            data=request.data,
            context={"request": request, "circle": circle},
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        token = _build_invite_token(circle.pk, data["role"])

        # Pre-create the CircleMember with invite_token set (no user yet).
        # The user field is required, so we store it linked to a sentinel
        # approach: create a placeholder and update on accept.
        # Simpler approach: just return the token and let accept_invite create the member.
        return Response(
            {
                "invite_token": token,
                "circle_id": circle.pk,
                "circle_name": circle.name,
                "role": data["role"],
                "display_name": data["display_name"],
                "avatar_color": data["avatar_color"],
                "avatar_emoji": data["avatar_emoji"],
                "expires_in_seconds": _INVITE_TTL_SECONDS,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="accept_invite")
    def accept_invite(self, request: Request, pk: str | None = None) -> Response:
        """
        Accept an invite token — creates a CircleMember for the current user.

        The token encodes: circle_id, role, timestamp, nonce, HMAC sig.
        """
        serializer = InviteAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]

        result = _verify_invite_token(token)
        if result is None:
            raise ValidationError({"token": "Invalid or expired invite token."})

        circle_id, role = result

        # Verify circle exists and matches the URL pk
        try:
            circle = Circle.objects.get(pk=circle_id)
        except Circle.DoesNotExist:
            raise NotFound("Circle not found.")

        if str(circle.pk) != str(pk):
            raise ValidationError({"token": "Token does not match this circle."})

        user: User = request.user

        if CircleMember.objects.filter(user=user, circle=circle).exists():
            raise ValidationError(
                {"detail": "You are already a member of this circle."}
            )

        display_name = request.data.get("display_name") or user.get_full_name() or user.username
        avatar_color = request.data.get("avatar_color", "#E76F51")
        avatar_emoji = request.data.get("avatar_emoji", "")

        member = CircleMember.objects.create(
            user=user,
            circle=circle,
            role=role,
            display_name=display_name,
            avatar_color=avatar_color,
            avatar_emoji=avatar_emoji,
            invite_token=token,
            invite_accepted_at=timezone.now(),
            membership_type="local",
        )

        return Response(
            CircleMemberSerializer(member).data,
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# CircleMemberViewSet
# ---------------------------------------------------------------------------

class CircleMemberViewSet(viewsets.ModelViewSet):
    """
    Manage members of a specific circle.

    Nested under: /circles/{circle_pk}/members/

    Permission matrix:
      list / retrieve  → IsCircleGuest  (any member, filtered by role)
      update_role      → IsCircleAdmin
      remove           → IsCircleMemberOrAdmin
    """

    http_method_names = ["get", "patch", "delete", "head", "options"]
    permission_classes = [IsAuthenticated]

    def _get_circle(self) -> Circle:
        circle_pk = self.kwargs.get("circle_pk")
        try:
            return Circle.objects.get(pk=circle_pk)
        except Circle.DoesNotExist:
            raise NotFound("Circle not found.")

    def get_queryset(self):
        circle = self._get_circle()

        # Ensure requesting user is at least a guest in this circle
        if not CircleMember.objects.filter(user=self.request.user, circle=circle).exists():
            raise PermissionDenied("You are not a member of this circle.")

        return CircleMember.objects.filter(circle=circle).select_related("user", "circle")

    def get_serializer_class(self):
        if self.action in ("partial_update", "update"):
            return CircleMemberUpdateRoleSerializer
        return CircleMemberSerializer

    def get_serializer_context(self) -> dict:
        ctx = super().get_serializer_context()
        ctx["circle"] = self._get_circle()
        return ctx

    # ------------------------------------------------------------------
    # Override update to enforce admin check
    # ------------------------------------------------------------------

    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        member = self.get_object()
        circle = member.circle

        # Only admins can change roles; a member can change their own display_name
        perm = IsCircleAdmin()
        role_change = "role" in request.data
        if role_change and not perm.has_object_permission(request, self, circle):
            raise PermissionDenied("Only circle admins can change member roles.")

        # Self or admin can update display_name / avatar
        own_member_perm = IsCircleMemberOrAdmin()
        if not own_member_perm.has_object_permission(request, self, member):
            raise PermissionDenied("You can only update your own member profile.")

        return super().partial_update(request, *args, **kwargs)

    # ------------------------------------------------------------------
    # Override destroy to enforce self-or-admin check
    # ------------------------------------------------------------------

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        member = self.get_object()
        perm = IsCircleMemberOrAdmin()
        if not perm.has_object_permission(request, self, member):
            raise PermissionDenied(
                "Only circle admins or the member themselves can remove a membership."
            )
        return super().destroy(request, *args, **kwargs)

    # ------------------------------------------------------------------
    # Custom action: update_role (explicit endpoint for clarity)
    # ------------------------------------------------------------------

    @action(detail=True, methods=["patch"], url_path="role")
    def update_role(self, request: Request, circle_pk: str | None = None, pk: str | None = None) -> Response:
        """
        Dedicated endpoint to change a member's role.  Admin-only.
        """
        member = self.get_object()
        circle = member.circle

        perm = IsCircleAdmin()
        if not perm.has_object_permission(request, self, circle):
            raise PermissionDenied("Only circle admins can change member roles.")

        serializer = CircleMemberUpdateRoleSerializer(
            member,
            data=request.data,
            partial=True,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        updated_member = serializer.save()

        return Response(CircleMemberSerializer(updated_member).data)
