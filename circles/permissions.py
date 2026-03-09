from __future__ import annotations

"""
RBAC permission classes for the circles app.

Permission matrix
-----------------

Role        | Read circle | Create events | Manage own | Validate agent | Full control
------------|-------------|---------------|------------|----------------|-------------
admin       |     yes     |      yes      |    yes     |      yes       |    yes
adult       |     yes     |      yes      |    yes     |      yes       |     no
parent      |     yes     |      yes      |    yes     |      yes       |     no
coach       |     yes     |      yes      |    yes     |       no       |     no
child       |  filtered   |    personal   |     no     |       no       |     no
guest       |  filtered   |       no      |     no     |       no       |     no
roommate    |     yes     |      yes      |    yes     |       no       |     no
member      |     yes     |      yes      |    yes     |       no       |     no
player      |     yes     |      yes      |    yes     |       no       |     no
intern      |  filtered   |    personal   |     no     |       no       |     no

Preset-specific notes
---------------------
- family   : admin/adult/parent = full managers; child = limited; guest = read-only
- colocation: admin/adult/roommate = managers; guest = read-only
- team     : admin/adult/member = managers; intern = limited; guest = read-only
- club     : admin/coach = managers; player/member = standard; guest = read-only
- custom   : only admin has full control; all others get member-level access
"""

import logging

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from circles.models import Circle, CircleMember

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Role constants
# ---------------------------------------------------------------------------

ADMIN_ROLES: frozenset[str] = frozenset({"admin"})

MANAGER_ROLES: frozenset[str] = frozenset(
    {"admin", "adult", "parent", "coach", "roommate", "member"}
)

STANDARD_ROLES: frozenset[str] = frozenset(
    {"admin", "adult", "parent", "coach", "roommate", "member", "player"}
)

LIMITED_ROLES: frozenset[str] = frozenset({"child", "guest", "intern"})

# Roles that can validate / enable the AI agent for a circle
AGENT_VALIDATOR_ROLES: frozenset[str] = frozenset({"admin", "adult", "parent"})


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_member(request: Request, circle: Circle) -> CircleMember | None:
    """Return the CircleMember linking the current user to *circle*, or None."""
    try:
        return CircleMember.objects.get(user=request.user, circle=circle)
    except CircleMember.DoesNotExist:
        return None


def _resolve_circle(view: APIView) -> Circle | None:
    """Try to resolve the Circle instance from the view's kwargs."""
    circle_pk = view.kwargs.get("circle_pk") or view.kwargs.get("pk")
    if circle_pk is None:
        return None
    try:
        return Circle.objects.get(pk=circle_pk)
    except Circle.DoesNotExist:
        return None


# ---------------------------------------------------------------------------
# Base mixin
# ---------------------------------------------------------------------------

class _CircleMemberPermission(BasePermission):
    """
    Abstract base: resolves the current membership and stores it as
    ``request._circle_member`` for downstream re-use (avoids double DB hit).
    """

    required_roles: frozenset[str] = frozenset()

    def has_permission(self, request: Request, view: APIView) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        return True  # object-level check does the heavy lifting

    def has_object_permission(
        self, request: Request, view: APIView, obj: object
    ) -> bool:
        # Resolve the circle (obj may be Circle or CircleMember)
        circle: Circle | None = None
        if isinstance(obj, Circle):
            circle = obj
        elif isinstance(obj, CircleMember):
            circle = obj.circle

        if circle is None:
            return False

        member = _get_member(request, circle)
        if member is None:
            logger.debug(
                "User %s has no membership in circle %s",
                request.user,
                circle.pk,
            )
            return False

        # Cache on request for views that call get_permissions() + check
        request._circle_member = member  # type: ignore[attr-defined]

        return member.role in self.required_roles


# ---------------------------------------------------------------------------
# Public permission classes
# ---------------------------------------------------------------------------

class IsCircleAdmin(BasePermission):
    """Full control — only members with role ``admin``."""

    message = "You must be an admin of this circle."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(
        self, request: Request, view: APIView, obj: object
    ) -> bool:
        circle: Circle | None = None
        if isinstance(obj, Circle):
            circle = obj
        elif isinstance(obj, CircleMember):
            circle = obj.circle

        if circle is None:
            return False

        member = _get_member(request, circle)
        if member is None:
            return False

        request._circle_member = member  # type: ignore[attr-defined]
        return member.role in ADMIN_ROLES


class IsCircleAdult(BasePermission):
    """
    Can create events, manage their own data, and validate the AI agent.

    Granted to: admin, adult, parent, coach, roommate, member.
    """

    message = "You must be an adult-level member of this circle."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(
        self, request: Request, view: APIView, obj: object
    ) -> bool:
        circle: Circle | None = None
        if isinstance(obj, Circle):
            circle = obj
        elif isinstance(obj, CircleMember):
            circle = obj.circle

        if circle is None:
            return False

        member = _get_member(request, circle)
        if member is None:
            return False

        request._circle_member = member  # type: ignore[attr-defined]
        return member.role in MANAGER_ROLES


class IsCircleChild(BasePermission):
    """
    Read-only access (filtered) + can create personal events.

    Granted to: child, intern — and all higher roles (they are a superset).
    """

    message = "You must be a member of this circle."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(
        self, request: Request, view: APIView, obj: object
    ) -> bool:
        circle: Circle | None = None
        if isinstance(obj, Circle):
            circle = obj
        elif isinstance(obj, CircleMember):
            circle = obj.circle

        if circle is None:
            return False

        member = _get_member(request, circle)
        if member is None:
            return False

        request._circle_member = member  # type: ignore[attr-defined]
        # child / intern AND all higher roles can access
        return member.role in (STANDARD_ROLES | LIMITED_ROLES)


class IsCircleGuest(BasePermission):
    """
    Read-only filtered access.

    Granted to: any member of the circle (including guest).
    """

    message = "You must be a member (including guest) of this circle."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(
        self, request: Request, view: APIView, obj: object
    ) -> bool:
        circle: Circle | None = None
        if isinstance(obj, Circle):
            circle = obj
        elif isinstance(obj, CircleMember):
            circle = obj.circle

        if circle is None:
            return False

        member = _get_member(request, circle)
        if member is None:
            return False

        request._circle_member = member  # type: ignore[attr-defined]
        # All roles (guest included) can read
        return True


class IsCircleMemberOrAdmin(BasePermission):
    """
    Composite: allows access if the user is an admin OR the CircleMember
    being acted upon is themselves.

    Useful for endpoints like "remove member" or "update own display_name".
    """

    message = "You must be an admin or the member yourself."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(
        self, request: Request, view: APIView, obj: object
    ) -> bool:
        if isinstance(obj, CircleMember):
            circle = obj.circle
            member = _get_member(request, circle)
            if member is None:
                return False
            request._circle_member = member  # type: ignore[attr-defined]
            return member.role in ADMIN_ROLES or obj.user == request.user

        if isinstance(obj, Circle):
            member = _get_member(request, obj)
            if member is None:
                return False
            request._circle_member = member  # type: ignore[attr-defined]
            return member.role in ADMIN_ROLES

        return False


# ---------------------------------------------------------------------------
# Utility: role-based check helper used in views
# ---------------------------------------------------------------------------

def user_can_validate_agent(request: Request, circle: Circle) -> bool:
    """Return True if the requesting user can enable/disable the AI agent."""
    member = _get_member(request, circle)
    return member is not None and member.role in AGENT_VALIDATOR_ROLES


def get_user_role_in_circle(request: Request, circle: Circle) -> str | None:
    """Return the user's role string in the given circle, or None."""
    member = _get_member(request, circle)
    return member.role if member else None
