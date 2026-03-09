from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _


class OIDCConfig(models.Model):
    """OIDC configuration for the tenant (singleton per tenant).

    Stores the IdP coordinates used by mozilla-django-oidc to authenticate
    users.  In practice there is one row per deployment, but the model is
    DB-backed so it can be changed at runtime without a redeploy.

    ``backend_type`` controls which :class:`iam.providers.base.UserProvider`
    implementation is returned by the registry when provisioning users in
    the upstream directory.
    """

    BACKEND_CHOICES = [
        ("lldap", "LLDAP (lightweight)"),
        ("zitadel", "Zitadel (premium)"),
    ]

    issuer_url = models.URLField(
        verbose_name=_("Issuer URL"),
        help_text=_("OIDC discovery endpoint base URL (e.g. https://auth.example.com)"),
    )
    client_id = models.CharField(
        max_length=255,
        verbose_name=_("Client ID"),
    )
    client_secret = models.CharField(
        max_length=500,
        verbose_name=_("Client Secret"),
        help_text=_("Stored encrypted at rest via field-level encryption or Vault."),
    )
    backend_type = models.CharField(
        max_length=20,
        choices=BACKEND_CHOICES,
        verbose_name=_("IAM Backend"),
        help_text=_("Which directory backend to use for user provisioning."),
    )
    api_url = models.URLField(
        verbose_name=_("Management API URL"),
        help_text=_(
            "Base URL for the IAM management API "
            "(LLDAP GraphQL endpoint or Zitadel Management API root)."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("OIDC Configuration")
        verbose_name_plural = _("OIDC Configurations")

    def __str__(self) -> str:
        return f"OIDCConfig({self.backend_type}) → {self.issuer_url}"


class TrustedExternalIdP(models.Model):
    """Trusted external Identity Provider for federated guests.

    Allows users authenticated by a third-party OIDC IdP (e.g. a customer's
    Zitadel Global instance) to log in as guest members without requiring
    a local account in the tenant directory.
    """

    issuer_url = models.URLField(
        unique=True,
        verbose_name=_("Issuer URL"),
        help_text=_("Must exactly match the ``iss`` claim in incoming JWTs."),
    )
    client_id = models.CharField(max_length=255, verbose_name=_("Client ID"))
    client_secret = models.CharField(
        max_length=500,
        verbose_name=_("Client Secret"),
    )
    display_name = models.CharField(
        max_length=100,
        verbose_name=_("Display Name"),
        help_text=_("Shown to the user on the login screen (e.g. 'Acme Corp SSO')."),
    )
    enabled = models.BooleanField(
        default=True,
        verbose_name=_("Enabled"),
        help_text=_("Disabled IdPs are ignored during authentication."),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Trusted External IdP")
        verbose_name_plural = _("Trusted External IdPs")
        ordering = ["display_name"]

    def __str__(self) -> str:
        status = "enabled" if self.enabled else "disabled"
        return f"TrustedExternalIdP({self.display_name!r}, {status})"


class AppSpecificPassword(models.Model):
    """Application-specific password for CalDAV / CardDAV clients.

    Native apps (iOS Calendar, Thunderbird, etc.) cannot participate in an
    OIDC browser redirect flow.  This model stores a bcrypt-hashed password
    that is validated independently of the main OIDC session.

    The plaintext password is shown to the user **once** at creation time and
    is never stored in cleartext.
    """

    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="app_passwords",
        verbose_name=_("User"),
    )
    name = models.CharField(
        max_length=100,
        verbose_name=_("Name"),
        help_text=_("Human-readable label (e.g. 'iPhone de Awa')."),
    )
    password_hash = models.CharField(
        max_length=255,
        verbose_name=_("Password Hash"),
        help_text=_("bcrypt hash of the application-specific password."),
    )
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Last Used At"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Expires At"),
        help_text=_("Leave blank for a non-expiring password."),
    )

    class Meta:
        verbose_name = _("App-Specific Password")
        verbose_name_plural = _("App-Specific Passwords")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"AppSpecificPassword({self.user_id}, {self.name!r})"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def is_expired(self) -> bool:
        """Return True if the password has passed its expiry date."""
        if self.expires_at is None:
            return False
        from django.utils import timezone

        return timezone.now() >= self.expires_at

    def check_password(self, raw_password: str) -> bool:
        """Verify *raw_password* against the stored bcrypt hash.

        Uses Django's ``check_password`` which handles bcrypt identifiers
        transparently when the hash is prefixed with ``bcrypt$``.
        """
        from django.contrib.auth.hashers import check_password as django_check

        return django_check(raw_password, self.password_hash)


class CircleInviteToken(models.Model):
    """One-time token that pre-authorises a new OIDC user as a CircleMember.

    When a user clicks an invite link and then authenticates via OIDC, the
    backend reads this token from the session/URL and creates the
    CircleMember row automatically on first login.

    ``circle_id`` is a generic integer FK so this model does not import from
    ``app`` directly and avoids circular imports.
    """

    token = models.CharField(
        max_length=64,
        unique=True,
        verbose_name=_("Invite Token"),
        help_text=_("Opaque random token included in the invite URL."),
    )
    email = models.EmailField(
        verbose_name=_("Invited Email"),
        help_text=_("Pre-fill for display; the OIDC email must match."),
    )
    circle_id = models.PositiveIntegerField(
        verbose_name=_("Circle ID"),
        help_text=_("ID of the Circle the invitee will be added to."),
    )
    role = models.CharField(
        max_length=32,
        default="member",
        verbose_name=_("Role"),
    )
    invited_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        related_name="sent_invites",
        verbose_name=_("Invited By"),
    )
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Used At"),
    )
    expires_at = models.DateTimeField(verbose_name=_("Expires At"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Circle Invite Token")
        verbose_name_plural = _("Circle Invite Tokens")

    def __str__(self) -> str:
        return f"CircleInviteToken({self.email!r} → circle {self.circle_id})"

    def is_valid(self) -> bool:
        """Return True if the token has not been used and has not expired."""
        from django.utils import timezone

        return self.used_at is None and timezone.now() < self.expires_at
