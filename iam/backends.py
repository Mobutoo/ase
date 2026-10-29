from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import SuspiciousOperation
from django.db import transaction
from django.utils import timezone
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

from .models import OIDCIdentity

logger = logging.getLogger(__name__)
User = get_user_model()


class OIDCBackend(OIDCAuthenticationBackend):
    """Validate OIDC tokens and bind accounts to an issuer/subject pair.

    Email addresses and display names are profile data, never account keys.
    Existing accounts must be linked explicitly through OIDCIdentity by an admin.
    """

    def verify_token(self, token, **kwargs):
        payload = super().verify_token(token, **kwargs)
        _validate_token_claims(payload)
        return payload

    def get_userinfo(self, access_token, id_token, payload):
        claims = super().get_userinfo(access_token, id_token, payload)
        if claims.get("sub") != payload.get("sub"):
            raise SuspiciousOperation("OIDC UserInfo subject does not match ID token.")
        # The issuer comes exclusively from the validated ID token.
        claims["iss"] = payload["iss"]
        return claims

    def filter_users_by_claims(self, claims):
        _validate_identity_claims(claims)
        return User.objects.filter(
            oidc_identities__issuer=claims["iss"],
            oidc_identities__subject=claims["sub"],
        )

    def create_user(self, claims):
        return _create_or_update_user(claims, created=True, request=self.request)

    def update_user(self, user, claims):
        return _create_or_update_user(claims, created=False, request=self.request)

    def get_user(self, user_id):
        return User.objects.filter(pk=user_id, is_active=True).first()


def _validate_token_claims(payload):
    """Check claims not validated by mozilla-django-oidc's signature verifier."""
    issuer = getattr(settings, "OIDC_OP_ISSUER", "")
    client_id = getattr(settings, "OIDC_RP_CLIENT_ID", "")
    if not issuer or payload.get("iss") != issuer:
        raise SuspiciousOperation("OIDC issuer mismatch.")
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject or len(subject) > 255:
        raise SuspiciousOperation("OIDC subject is required.")
    audiences = payload.get("aud")
    if isinstance(audiences, str):
        audiences = [audiences]
    if not client_id or not isinstance(audiences, list) or client_id not in audiences:
        raise SuspiciousOperation("OIDC audience mismatch.")
    if (len(audiences) > 1 or "azp" in payload) and payload.get("azp") != client_id:
        raise SuspiciousOperation("OIDC authorized party mismatch.")
    now = timezone.now().timestamp()
    for claim in ("exp", "iat"):
        value = payload.get(claim)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise SuspiciousOperation(f"OIDC {claim} must be a numeric date.")
    if not payload["exp"] > now or not payload["iat"] <= now + 60:
        raise SuspiciousOperation("OIDC token is expired or issued in the future.")
    if "nbf" in payload:
        nbf = payload["nbf"]
        if isinstance(nbf, bool) or not isinstance(nbf, (int, float)) or not nbf <= now + 60:
            raise SuspiciousOperation("OIDC token is not yet valid.")


def _validate_identity_claims(claims):
    issuer, subject = claims.get("iss"), claims.get("sub")
    if not isinstance(issuer, str) or not issuer or len(issuer) > 500:
        raise SuspiciousOperation("OIDC issuer is required.")
    if not isinstance(subject, str) or not subject or len(subject) > 255:
        raise SuspiciousOperation("OIDC subject is required.")
    tenant_issuer = getattr(settings, "OIDC_OP_ISSUER", "")
    if issuer != tenant_issuer:
        from .models import TrustedExternalIdP
        if not TrustedExternalIdP.objects.filter(issuer_url=issuer, enabled=True).exists():
            raise SuspiciousOperation("Untrusted OIDC issuer.")
    return issuer == tenant_issuer


@transaction.atomic
def _create_or_update_user(claims, *, created, request):
    is_tenant = _validate_identity_claims(claims)
    email = (claims.get("email") or "").strip().lower()
    identity = OIDCIdentity.objects.select_related("user").filter(
        issuer=claims["iss"], subject=claims["sub"],
    ).first()
    if identity is None:
        if os.environ.get("OIDC_AUTO_CREATE_USERS", "1") != "1":
            raise SuspiciousOperation("OIDC account must be provisioned by an administrator.")
        username = "oidc_" + hashlib.sha256(
            json.dumps([claims["iss"], claims["sub"]]).encode()
        ).hexdigest()
        user = User.objects.create_user(username=username, email=email, password=None)
        OIDCIdentity.objects.create(user=user, issuer=claims["iss"], subject=claims["sub"])
    else:
        user = identity.user
    if not user.is_active:
        raise SuspiciousOperation("Inactive OIDC account.")
    if claims.get("email_verified") is True:
        user.email = email
    display_name = claims.get("name") or claims.get("preferred_username") or ""
    parts = display_name.strip().split(" ", 1)
    if not user.first_name:
        user.first_name = parts[0][:150]
    if len(parts) > 1 and not user.last_name:
        user.last_name = parts[1][:150]
    # External IdPs may authenticate guests, but cannot grant deployment privileges.
    _sync_permissions(user, claims if is_tenant else {})
    user.save()
    if claims.get("email_verified") is True:
        _handle_invite_token(user, request)
    return user


def _sync_permissions(user: AbstractBaseUser, claims: dict) -> None:
    """Update ``is_staff`` / ``is_superuser`` from OIDC group claims.

    Supports two claim formats:

    1. **LLDAP / generic**: ``groups`` — a flat list of group names.
    2. **Zitadel**: ``urn:zitadel:iam:org:project:roles`` — a dict whose keys
       are role names and whose values are dicts of org IDs, e.g.::

           {"admin": {"<org-id>": "..."}, "member": {"<org-id>": "..."}}

    Both formats are merged into a single set of role/group names before
    checking against ``OIDC_STAFF_GROUPS`` and ``OIDC_SUPERUSER_GROUPS``.
    """
    # --- Collect roles from all supported claim formats ---
    groups: list[str] = list(claims.get("groups") or [])

    # Zitadel project-level roles claim (no project ID in the key)
    zitadel_roles = claims.get("urn:zitadel:iam:org:project:roles")
    if isinstance(zitadel_roles, dict):
        groups.extend(zitadel_roles.keys())

    # Zitadel project-specific roles claims: urn:zitadel:iam:org:project:<id>:roles
    # Scan all claims for the pattern to avoid hardcoding a project ID.
    _ZITADEL_ROLE_PREFIX = "urn:zitadel:iam:org:project:"
    _ZITADEL_ROLE_SUFFIX = ":roles"
    for claim_key, claim_val in claims.items():
        if (
            claim_key.startswith(_ZITADEL_ROLE_PREFIX)
            and claim_key.endswith(_ZITADEL_ROLE_SUFFIX)
            and claim_key != "urn:zitadel:iam:org:project:roles"
            and isinstance(claim_val, dict)
        ):
            groups.extend(claim_val.keys())

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

    role_set = set(groups)
    new_is_staff = bool(staff_groups & role_set)
    new_is_superuser = bool(superuser_groups & role_set)

    if hasattr(user, "is_staff"):
        user.is_staff = new_is_staff  # type: ignore[attr-defined]
    if hasattr(user, "is_superuser"):
        user.is_superuser = new_is_superuser  # type: ignore[attr-defined]

    if groups:
        logger.debug(
            "OIDC _sync_permissions: user=%r roles=%r staff=%s super=%s",
            getattr(user, "email", user.pk),
            groups,
            new_is_staff,
            new_is_superuser,
        )


@transaction.atomic
def _handle_invite_token(user, request):
    """Consume an invitation once, for its verified email, on any login."""
    from circles.models import Circle, CircleMember, PRESET_ROLES
    from .models import CircleInviteToken

    session = getattr(request, "session", {})
    token = session.get("iam_invite_token")
    if not token:
        return
    invite = CircleInviteToken.objects.select_for_update().filter(token=token).first()
    if invite is None or not invite.is_valid():
        session.pop("iam_invite_token", None)
        return
    if invite.email.casefold() != user.email.casefold():
        raise SuspiciousOperation("Invitation email does not match the verified account.")
    circle = Circle.objects.filter(pk=invite.circle_id).first()
    if circle is None or invite.role not in PRESET_ROLES[circle.preset]:
        raise SuspiciousOperation("Invitation circle or role is invalid.")
    CircleMember.objects.get_or_create(
        user=user, circle=circle,
        defaults={"role": invite.role, "display_name": user.get_full_name() or user.username,
                  "invite_accepted_at": timezone.now()},
    )
    invite.used_at = timezone.now()
    invite.save(update_fields=["used_at"])
    session.pop("iam_invite_token", None)


AseOIDCAuthenticationBackend = OIDCBackend
