from __future__ import annotations

from django.contrib import admin
from django.utils.html import format_html

from .models import AgentAction, MemberPreference, NotificationPreference
from .services.integrity import verify_action


@admin.register(AgentAction)
class AgentActionAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "circle",
        "action_type",
        "proposed_at",
        "status_badge",
        "integrity_ok",
    ]
    list_filter = ["action_type", "circle"]
    search_fields = ["payload", "error"]
    readonly_fields = [
        "circle",
        "action_type",
        "payload",
        "proposed_at",
        "approved_by",
        "approved_at",
        "rejected_at",
        "executed_at",
        "error",
        "integrity_hash",
    ]
    date_hierarchy = "proposed_at"
    ordering = ["-proposed_at"]

    def status_badge(self, obj: AgentAction) -> str:
        if obj.is_executed:
            color, label = "green", "Executed"
        elif obj.is_approved:
            color, label = "blue", "Approved"
        elif obj.is_rejected:
            color, label = "red", "Rejected"
        else:
            color, label = "orange", "Pending"
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>', color, label
        )

    status_badge.short_description = "Status"

    def integrity_ok(self, obj: AgentAction) -> str:
        ok = verify_action(obj)
        return format_html(
            '<span style="color: {};">{}</span>',
            "green" if ok else "red",
            "OK" if ok else "FAIL",
        )

    integrity_ok.short_description = "Integrity"

    def has_add_permission(self, request) -> bool:
        """Prevent creating AgentAction directly in admin — use the agent service."""
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        """Prevent deletion — AgentAction is an immutable audit log."""
        return False


@admin.register(MemberPreference)
class MemberPreferenceAdmin(admin.ModelAdmin):
    list_display = ["id", "member", "category", "key", "confirmed", "source", "updated_at"]
    list_filter = ["category", "source", "confirmed"]
    search_fields = ["key", "member__display_name"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["member", "category", "key"]


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = [
        "member",
        "push_enabled",
        "telegram_enabled",
        "email_enabled",
        "notify_agent_proposal",
        "notify_agent_digest",
        "updated_at",
    ]
    list_filter = ["push_enabled", "telegram_enabled", "email_enabled"]
    search_fields = ["member__display_name"]
    readonly_fields = ["updated_at"]
    ordering = ["member"]
