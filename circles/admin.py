from __future__ import annotations

from django.contrib import admin
from django.utils.html import format_html

from circles.models import Circle, CircleMember


# ---------------------------------------------------------------------------
# Inline admin
# ---------------------------------------------------------------------------

class CircleMemberInline(admin.TabularInline):
    """Inline editor for CircleMember entries within a Circle admin page."""

    model = CircleMember
    extra = 0
    readonly_fields = ("user", "invite_accepted_at", "created_at")
    fields = (
        "user",
        "role",
        "display_name",
        "avatar_color",
        "avatar_emoji",
        "membership_type",
        "invite_token",
        "invite_accepted_at",
        "created_at",
    )
    show_change_link = True


# ---------------------------------------------------------------------------
# Circle admin
# ---------------------------------------------------------------------------

@admin.register(Circle)
class CircleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "preset",
        "tenant_id",
        "is_primary",
        "timezone",
        "agent_enabled",
        "agent_budget_limit",
        "member_count",
        "created_at",
    )
    list_filter = ("preset", "is_primary", "agent_enabled")
    search_fields = ("name", "tenant_id")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    inlines = [CircleMemberInline]

    fieldsets = (
        (
            "Identity",
            {
                "fields": ("name", "preset", "tenant_id", "is_primary", "timezone"),
            },
        ),
        (
            "AI Agent",
            {
                "fields": ("agent_enabled", "agent_budget_limit"),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_at",),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Members")
    def member_count(self, obj: Circle) -> int:
        return obj.members.count()


# ---------------------------------------------------------------------------
# CircleMember admin
# ---------------------------------------------------------------------------

@admin.register(CircleMember)
class CircleMemberAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "display_name",
        "user",
        "circle",
        "role",
        "membership_type",
        "avatar_preview",
        "invite_accepted_at",
        "created_at",
    )
    list_filter = ("role", "membership_type", "circle__preset")
    search_fields = (
        "display_name",
        "user__username",
        "user__email",
        "circle__name",
        "invite_token",
    )
    readonly_fields = ("created_at", "invite_accepted_at")
    ordering = ("-created_at",)
    raw_id_fields = ("user", "circle")

    fieldsets = (
        (
            "Identity",
            {
                "fields": (
                    "user",
                    "circle",
                    "role",
                    "display_name",
                    "avatar_color",
                    "avatar_emoji",
                ),
            },
        ),
        (
            "Membership",
            {
                "fields": (
                    "membership_type",
                    "external_issuer",
                    "external_sub",
                ),
            },
        ),
        (
            "Invite",
            {
                "fields": ("invite_token", "invite_accepted_at"),
                "classes": ("collapse",),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_at",),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Avatar")
    def avatar_preview(self, obj: CircleMember) -> str:
        color = obj.avatar_color or "#E76F51"
        emoji = obj.avatar_emoji or ""
        return format_html(
            '<span style="'
            "display:inline-block;"
            "width:24px;height:24px;"
            "border-radius:50%;"
            "background:{color};"
            "text-align:center;"
            "line-height:24px;"
            'font-size:14px;">{emoji}</span>',
            color=color,
            emoji=emoji,
        )
