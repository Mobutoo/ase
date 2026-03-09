from __future__ import annotations

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import AppSpecificPassword, CircleInviteToken, OIDCConfig, TrustedExternalIdP


@admin.register(OIDCConfig)
class OIDCConfigAdmin(admin.ModelAdmin):
    """Admin for the tenant OIDC configuration."""

    list_display = ["backend_type", "issuer_url", "client_id", "created_at"]
    readonly_fields = ["created_at"]
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "backend_type",
                    "issuer_url",
                    "client_id",
                    "client_secret",
                    "api_url",
                    "created_at",
                ]
            },
        ),
    ]

    def get_readonly_fields(
        self, request: object, obj: OIDCConfig | None = None
    ) -> list[str]:
        readonly = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:  # type: ignore[union-attr]
            # Hide the raw secret from non-superusers.
            readonly.append("client_secret")
        return readonly


@admin.register(TrustedExternalIdP)
class TrustedExternalIdPAdmin(admin.ModelAdmin):
    """Admin for trusted external Identity Providers."""

    list_display = ["display_name", "issuer_url", "enabled", "created_at"]
    list_filter = ["enabled"]
    search_fields = ["display_name", "issuer_url", "client_id"]
    readonly_fields = ["created_at"]
    list_editable = ["enabled"]
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "display_name",
                    "issuer_url",
                    "client_id",
                    "client_secret",
                    "enabled",
                    "created_at",
                ]
            },
        ),
    ]

    def get_readonly_fields(
        self, request: object, obj: TrustedExternalIdP | None = None
    ) -> list[str]:
        readonly = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:  # type: ignore[union-attr]
            readonly.append("client_secret")
        return readonly


@admin.register(AppSpecificPassword)
class AppSpecificPasswordAdmin(admin.ModelAdmin):
    """Admin for application-specific passwords.

    The hash is deliberately hidden from the change form — admins can only
    revoke (delete) passwords, never read them.
    """

    list_display = [
        "user",
        "name",
        "last_used_at",
        "expires_at",
        "is_expired_display",
        "created_at",
    ]
    list_filter = ["user"]
    search_fields = ["user__username", "user__email", "name"]
    readonly_fields = ["password_hash", "last_used_at", "created_at"]
    raw_id_fields = ["user"]

    def is_expired_display(self, obj: AppSpecificPassword) -> str:
        expired = obj.is_expired()
        icon = "✗" if expired else "✓"
        colour = "red" if expired else "green"
        return format_html('<span style="color:{}">{}</span>', colour, icon)

    is_expired_display.short_description = _("Active")  # type: ignore[attr-defined]

    def has_add_permission(self, request: object) -> bool:
        # Passwords must be created through the API (so the plaintext is returned once).
        return False


@admin.register(CircleInviteToken)
class CircleInviteTokenAdmin(admin.ModelAdmin):
    """Admin for Circle invite tokens."""

    list_display = [
        "email",
        "circle_id",
        "role",
        "invited_by",
        "is_valid_display",
        "expires_at",
        "used_at",
        "created_at",
    ]
    list_filter = ["role"]
    search_fields = ["email", "token"]
    readonly_fields = ["token", "used_at", "created_at"]
    raw_id_fields = ["invited_by"]

    def is_valid_display(self, obj: CircleInviteToken) -> str:
        valid = obj.is_valid()
        icon = "✓" if valid else "✗"
        colour = "green" if valid else "red"
        return format_html('<span style="color:{}">{}</span>', colour, icon)

    is_valid_display.short_description = _("Valid")  # type: ignore[attr-defined]
