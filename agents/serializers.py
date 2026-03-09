from __future__ import annotations

from rest_framework import serializers

from .models import AgentAction, MemberPreference, NotificationPreference


class AgentActionSerializer(serializers.ModelSerializer):
    """Read-only serializer for AgentAction audit log entries.

    Direct creation from the API is not allowed — only the agent service
    may create AgentAction records. Approve/reject are separate actions.
    """

    status = serializers.SerializerMethodField()
    circle_name = serializers.CharField(source="circle.name", read_only=True)
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = AgentAction
        fields = [
            "id",
            "circle",
            "circle_name",
            "action_type",
            "payload",
            "proposed_at",
            "approved_by",
            "approved_by_name",
            "approved_at",
            "rejected_at",
            "executed_at",
            "error",
            "integrity_hash",
            "status",
        ]
        read_only_fields = fields

    def get_status(self, obj: AgentAction) -> str:
        if obj.is_executed:
            return "executed"
        if obj.is_approved:
            return "approved"
        if obj.is_rejected:
            return "rejected"
        return "pending"

    def get_approved_by_name(self, obj: AgentAction) -> str | None:
        if obj.approved_by_id is None:
            return None
        return obj.approved_by.display_name


class AgentActionApproveSerializer(serializers.Serializer):
    """Payload for approve action — empty body, member identity from request."""

    pass


class AgentActionRejectSerializer(serializers.Serializer):
    """Payload for reject action with optional reason."""

    reason = serializers.CharField(required=False, allow_blank=True, default="")


class MemberPreferenceSerializer(serializers.ModelSerializer):
    """CRUD serializer for MemberPreference.

    The 'member' field is set automatically from the request context
    on create — the API consumer cannot set it for another member.
    """

    class Meta:
        model = MemberPreference
        fields = [
            "id",
            "member",
            "category",
            "key",
            "value",
            "confirmed",
            "source",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "member", "created_at", "updated_at"]

    def validate_category(self, value: str) -> str:
        value = value.strip().lower()
        if not value:
            raise serializers.ValidationError("Category cannot be empty.")
        return value

    def validate_key(self, value: str) -> str:
        value = value.strip().lower()
        if not value:
            raise serializers.ValidationError("Key cannot be empty.")
        return value

    def validate_source(self, value: str) -> str:
        allowed = {"manual", "learned", "imported"}
        if value not in allowed:
            raise serializers.ValidationError(
                f"Source must be one of: {', '.join(sorted(allowed))}."
            )
        return value


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Retrieve + update serializer for NotificationPreference.

    Scoped to the authenticated member — retrieve and update only.
    """

    class Meta:
        model = NotificationPreference
        fields = [
            "id",
            "member",
            "push_enabled",
            "telegram_enabled",
            "email_enabled",
            "quiet_start",
            "quiet_end",
            "notify_event_created",
            "notify_event_modified",
            "notify_event_reminder",
            "notify_agent_proposal",
            "notify_agent_digest",
            "notify_conflict",
            "notify_invitation",
            "updated_at",
        ]
        read_only_fields = ["id", "member", "updated_at"]

    def validate(self, attrs: dict) -> dict:
        quiet_start = attrs.get("quiet_start", getattr(self.instance, "quiet_start", None))
        quiet_end = attrs.get("quiet_end", getattr(self.instance, "quiet_end", None))
        # Validate that both or neither quiet times are set
        if (quiet_start is None) != (quiet_end is None):
            raise serializers.ValidationError(
                "Both quiet_start and quiet_end must be set together, or both left empty."
            )
        return attrs
