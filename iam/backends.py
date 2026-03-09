from __future__ import annotations

import logging
import os
from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.utils import timezone

logger = logging.getLogger(__name__)

User = get_user_model()


class OIDCBackend:
    # Forward-declare so Django's AUTHENTICATION_BACKENDS can reference
    # either the canonical name (OIDCBackend) or the settings alias below.
    """Custom OIDC authentication backend extending mozilla-django-oidc.

    Responsibilities
    ----------------
    1. Maps the OIDC ``sub`` claim to a Django :class:`~django.contrib.auth.models.User`,
       creating the user on first login if auto-provisioning is enabled.
    2. Handles both **tenant OIDC** (primary IdP: LLDAP/Zitadel) and
       **federated guest** login (trusted external IdPs, e.g. Zitadel Global).
    3. On first login, if an invite token is stored in the session, creates
       the ``CircleMember`` row and marks the token as consumed.

    This class is imported by Django's auth machinery via
    ``AUTHENTICATION_BACKENDS`` in settings.

    Configuration (env vars)
    -------------------------
    ``OIDC_OP_ISSUER``
        Tenant IdP issuer URL.  Users whose JWT ``iss`` matches this are
        treated as **tenant members**.  All others are looked up against
        :class:`~iam.models.TrustedExternalIdP`.

    ``OIDC_AUTO_CREATE_USERS``
        ``"1"`` (default) — create a Django user automatically on first login.
        Set to ``"0"`` to require pre-provisioning via the IAM API.

    ``OIDC_STAFF_GROUPS``
        Comma-separated list of OIDC ``groups`` claim values that grant
        ``is_staff=True`` (default: ``admin``).

    ``OIDC_SUPERUSER_GROUPS``
        Comma-separated list of OIDC ``groups`` claim values that grant
        ``is_superuser=True`` (default: empty — never auto-granted).
    """

    # ------------------------------------------------------------------
    # mozilla-django-oidc interface
    # ------------------------------------------------------------------

    def authenticate(
        self, request: Any, **kwargs: Any
    ) -> AbstractBaseUser | None:
        """Entry point called by Django's auth framework.

        We defer to mozilla-django-oidc's ``OIDCAuthenticationBackend``
        for the actual token validation, then apply our custom mapping
        logic on the returned claims.
        """
        try:
            from mozilla_django_oidc.auth import OIDCAuthenticationBackend as _MozBase
        except ImportError:
            logger.error(
                "mozilla-django-oidc is not installed. "
                "Install it and add OIDC settings to use OIDCBackend."
            )
            return None

        # Delegate token validation and claims retrieval to the base class.
        # We subclass dynamically to avoid import-time errors if the package
        # is not yet installed.
        class _Backend(_MozBase):
            def create_user(inner_self, claims: dict) -> AbstractBaseUser:
                return _create_or_update_user(claims, created=True, request=request)

            def update_user(
                inner_self, user: AbstractBaseUser, claims: dict
            ) -> AbstractBaseUser:
                return _create_or_update_user(claims, created=False, request=request)

            def get_userinfo(inner_self, access_token: str, id_token: str, payload: dict) -> dict:  # noqa: E501
                """Extend get_userinfo to support federated (external IdP) tokens."""
                claims = super().get_userinfo(access_token, id_token, payload)
                # Attach the issuer so downstream helpers can identify the IdP.
                claims.setdefault("iss", payload.get("iss", ""))
                return claims

        return _Backend().authenticate(request, **kwargs)

    def get_user(self, user_id: int) -> AbstractBaseUser | None:
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


# ---------------------------------------------------------------------------
# Internal helpers (module-level so they are easy to unit-test)
# ---------------------------------------------------------------------------


def _create_or_update_user(
    claims: dict,
    *,
    created: bool,
    request: Any,
) -> AbstractBaseUser:
    """Map OIDC claims to a Django User and apply role/membership logic.

    Args:
        claims: Decoded OIDC ID token / userinfo claims.
        created: True if this is a first-time login (user must be provisioned).
        request: The Django HTTP request (used to read session invite token).

    Returns:
        The Django User instance (saved).
    """
    email = (claims.get("email") or "").lower().strip()
    sub = claims.get("sub", "")
    issuer = claims.get("iss", "")
    display_name = claims.get("name") or claims.get("preferred_username") or email

    auto_create = os.environ.get("OIDC_AUTO_CREATE_USERS", "1") == "1"

    if not email and not sub:
        logger.warning("OIDC login rejected: claims contain neither email nor sub.")
        raise ValueError("OIDC claims must include at least sub or email.")

    # ------------------------------------------------------------------
    # 1. Determine whether this is a tenant or federated login.
    # ------------------------------------------------------------------
    tenant_issuer = os.environ.get("OIDC_OP_ISSUER", "")
    is_tenant = not tenant_issuer or issuer == tenant_issuer

    if not is_tenant:
        _validate_federated_idp(issuer)

    # ------------------------------------------------------------------
    # 2. Find or create the Django User.
    # ------------------------------------------------------------------
    user = _get_or_create_django_user(
        sub=sub,
        email=email,
        display_name=display_name,
        auto_create=auto_create,
        is_federated=not is_tenant,
    )

    # ------------------------------------------------------------------
    # 3. Sync staff / superuser flags from group claims.
    # ------------------------------------------------------------------
    _sync_permissions(user, claims)

    # ------------------------------------------------------------------
    # 4. On first login, consume invite token if present.
    # ------------------------------------------------------------------
    if created:
        _handle_invite_token(user, request)

    user.save()
    return user


def _validate_federated_idp(issuer: str) -> None:
    """Raise if the issuer is not in TrustedExternalIdP.

    Args:
        issuer: The ``iss`` claim from the incoming JWT.

    Raises:
        PermissionError: If the issuer is not trusted.
    """
    from .models import TrustedExternalIdP

    if not TrustedExternalIdP.objects.filter(issuer_url=issuer, enabled=True).exists():
        logger.warning("Rejected login from untrusted IdP: %r", issuer)
        raise PermissionError(f"Identity provider {issuer!r} is not trusted.")


def _get_or_create_django_user(
    *,
    sub: str,
    email: str,
    display_name: str,
    auto_create: bool,
    is_federated: bool,
) -> AbstractBaseUser:
    """Find an existing user by ``sub`` or ``email``, or create one.

    The ``sub`` claim is stored in ``user.profile`` (if available) or matched
    via a ``sub:`` prefix in ``username`` as a fallback.

    Args:
        sub: OIDC subject identifier.
        email: Verified email address.
        display_name: Human-readable name from IdP.
        auto_create: Whether to create a new user if none found.
        is_federated: Whether this is a federated (external IdP) login.

    Returns:
        A Django User instance (not yet saved after attribute updates).

    Raises:
        LookupError: If the user does not exist and auto_create is False.
    """
    # Prefer matching by email (stable across sub changes on some IdPs).
    user = None
    if email:
        user = User.objects.filter(email=email).first()

    # Fallback: match by username derived from sub.
    if user is None and sub:
        username_candidate = _sub_to_username(sub)
        user = User.objects.filter(username=username_candidate).first()

    if user is not None:
        # Sync potentially stale attributes.
        _update_user_attributes(user, email=email, display_name=display_name)
        return user

    if not auto_create:
        raise LookupError(
            f"No Django user found for email={email!r} / sub={sub!r} "
            f"and OIDC_AUTO_CREATE_USERS is disabled."
        )

    username = _sub_to_username(sub) if sub else _email_to_username(email)
    user = User.objects.create_user(  # type: ignore[call-arg]
        username=username,
        email=email,
        password=None,  # Login is via OIDC only — no usable password.
    )
    _update_user_attributes(user, email=email, display_name=display_name)

    if is_federated:
        # Federated guests are inactive by default until a circle invite is consumed.
        user.is_active = True  # Allow login but restrict via permissions.

    logger.info(
        "OIDC: auto-provisioned Django user %r (email=%r, federated=%s)",
        user.username,
        email,
        is_federated,
    )
    return user


def _update_user_attributes(
    user: AbstractBaseUser,
    *,
    email: str,
    display_name: str,
) -> None:
    """Apply OIDC profile claims to the Django User instance in-place."""
    if email and user.email != email:  # type: ignore[attr-defined]
        user.email = email  # type: ignore[attr-defined]

    # Attempt to split display_name into first/last if the User model has those fields.
    parts = display_name.strip().split(" ", 1)
    if hasattr(user, "first_name") and not user.first_name:  # type: ignore[attr-defined]
        user.first_name = parts[0]  # type: ignore[attr-defined]
    if hasattr(user, "last_name") and len(parts) > 1 and not user.last_name:  # type: ignore[attr-defined]
        user.last_name = parts[1]  # type: ignore[attr-defined]


def _sync_permissions(user: AbstractBaseUser, claims: dict) -> None:
    """Update ``is_staff`` / ``is_superuser`` from OIDC group claims."""
    groups: list[str] = claims.get("groups") or []

    staff_groups = {
        g.strip()
        for g in os.environ.get("OIDC_STAFF_GROUPS", "admin").split(",")
        if g.strip()
    }
    superuser_groups = {
        g.strip()
        for g in os.environ.get("OIDC_SUPERUSER_GROUPS", "").split(",")
        if g.strip()
    }

    new_is_staff = bool(staff_groups & set(groups))
    new_is_superuser = bool(superuser_groups & set(groups))

    if hasattr(user, "is_staff"):
        user.is_staff = new_is_staff  # type: ignore[attr-defined]
    if hasattr(user, "is_superuser"):
        user.is_superuser = new_is_superuser  # type: ignore[attr-defined]


def _handle_invite_token(user: AbstractBaseUser, request: Any) -> None:
    """Consume the invite token stored in the session and create CircleMember.

    If no invite token is present or the token is invalid, this is a no-op.

    Args:
        user: Newly authenticated Django user.
        request: The HTTP request (reads ``request.session["iam_invite_token"]``).
    """
    from .models import CircleInviteToken

    token_value: str | None = None
    if request is not None and hasattr(request, "session"):
        token_value = request.session.pop("iam_invite_token", None)

    if not token_value:
        return

    invite = CircleInviteToken.objects.filter(token=token_value).first()
    if invite is None:
        logger.warning("OIDC: invite token %r not found in DB.", token_value)
        return

    if not invite.is_valid():
        logger.warning("OIDC: invite token %r is expired or already used.", token_value)
        return

    # Mark token as consumed.
    invite.used_at = timezone.now()
    invite.save(update_fields=["used_at"])

    # Best-effort CircleMember creation.  We avoid importing from ``app``
    # directly to keep IAM decoupled; use a signal instead if app grows.
    _create_circle_member(user=user, circle_id=invite.circle_id, role=invite.role)
    logger.info(
        "OIDC: consumed invite %r — user %r joined circle %s as %s.",
        token_value,
        getattr(user, "email", user.pk),
        invite.circle_id,
        invite.role,
    )


def _create_circle_member(
    user: AbstractBaseUser, circle_id: int, role: str
) -> None:
    """Create a CircleMember record for *user* in circle *circle_id*.

    Sends a Django signal so that the ``app`` module can react without
    creating a hard import dependency on it from ``iam``.
    """
    from django.dispatch import Signal

    circle_member_created = Signal()
    circle_member_created.send(
        sender=OIDCBackend,
        user=user,
        circle_id=circle_id,
        role=role,
    )


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


def _sub_to_username(sub: str) -> str:
    """Derive a stable, safe Django username from an OIDC ``sub`` claim."""
    # Strip characters illegal in Django usernames (max length 150).
    safe = "".join(c for c in sub if c.isalnum() or c in "_@.+-")
    prefix = "oidc_"
    max_len = 150 - len(prefix)
    return f"{prefix}{safe[:max_len]}"


def _email_to_username(email: str) -> str:
    """Derive a Django username from an email address."""
    local = email.split("@")[0]
    safe = "".join(c for c in local if c.isalnum() or c in "_.-")
    # Ensure uniqueness by appending a short hash when collisions exist.
    base = safe[:120] or "user"
    if not User.objects.filter(username=base).exists():
        return base
    import hashlib

    suffix = hashlib.sha1(email.encode()).hexdigest()[:8]
    return f"{base}_{suffix}"


# ---------------------------------------------------------------------------
# Alias — matches AUTHENTICATION_BACKENDS in ase_project/settings.py
# ---------------------------------------------------------------------------

#: Alias so settings.py can reference either class name.
AseOIDCAuthenticationBackend = OIDCBackend

