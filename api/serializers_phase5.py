"""
Phase 5 serializers — AI Copilot via n8n / OpenClaw.

Serializers for:
- AISuggestion (user-facing read/action)
- WebhookCallbackSerializer (n8n → Ase inbound payload)
- PlanRequestSerializer (user triggers daily plan request)
- ReflectionRequestSerializer (user triggers reflection request)
"""
from rest_framework import serializers

from app.models import AISuggestion, AI_SUGGESTION_TYPE_CHOICES


class AISuggestionSerializer(serializers.ModelSerializer):
    """Full representation of an AI suggestion (read-only user view)."""

    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = AISuggestion
        fields = [
            "id",
            "username",
            "suggestion_type",
            "content",
            "accepted",
            "created_at",
        ]
        read_only_fields = ["id", "username", "suggestion_type", "content", "created_at"]


class AISuggestionAcceptSerializer(serializers.Serializer):
    """Payload for accept / dismiss actions (no body required — action is implicit)."""

    pass


class WebhookCallbackSerializer(serializers.Serializer):
    """Validates the inbound callback payload sent by n8n after AI processing.

    n8n POSTs back with at minimum:
      - suggestion_type  (one of AI_SUGGESTION_TYPE_CHOICES keys)
      - username         (target user, resolved server-side from the payload)
      - content          (arbitrary JSON — the AI output)
    """

    VALID_TYPES = [choice[0] for choice in AI_SUGGESTION_TYPE_CHOICES]

    username = serializers.CharField(max_length=150)
    suggestion_type = serializers.ChoiceField(choices=VALID_TYPES)
    content = serializers.JSONField()

    def validate_content(self, value):
        if not isinstance(value, (dict, list)):
            raise serializers.ValidationError(
                "content must be a JSON object or array"
            )
        return value


class PlanRequestSerializer(serializers.Serializer):
    """Optional overrides when the user manually triggers a daily plan."""

    # All fields optional — defaults are computed server-side
    include_done_tasks = serializers.BooleanField(default=False, required=False)
    energy_days = serializers.IntegerField(
        min_value=1,
        max_value=30,
        default=7,
        required=False,
        help_text="How many days of energy history to include",
    )


class ReflectionRequestSerializer(serializers.Serializer):
    """Optional overrides when the user manually triggers an end-of-day reflection."""

    # Nothing required — server derives sessions from today automatically
    pass
