"""Phase 2 serializers — TaskSourceConfig, Playlist, and TaskDTO (read-only).

Follows the same DRF patterns as api/serializers.py.
Do NOT modify serializers.py; these will be merged at integration time.
"""
from __future__ import annotations

from rest_framework import serializers

from adapters.base import TaskDTO
from app.models_phase2 import Playlist, TaskSourceConfig


# ---------------------------------------------------------------------------
# TaskSourceConfig
# ---------------------------------------------------------------------------

class TaskSourceConfigSerializer(serializers.ModelSerializer):
    """Serializer for CRUD on task source configurations.

    The config field holds adapter secrets (API keys etc.).  We expose it
    fully for create/update but write-only to prevent key leakage on reads.
    """

    # Return source_type display label as read-only convenience field
    source_type_display = serializers.CharField(
        source="get_source_type_display", read_only=True
    )
    # Config is write-only: returned as a masked dict on reads
    config = serializers.JSONField(write_only=True, required=False, default=dict)
    config_keys = serializers.SerializerMethodField(
        help_text="List of config key names present (values hidden)"
    )

    class Meta:
        model = TaskSourceConfig
        fields = [
            "id",
            "source_type",
            "source_type_display",
            "enabled",
            "config",
            "config_keys",
            "display_order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "source_type_display", "config_keys", "created_at", "updated_at"]

    def get_config_keys(self, obj: TaskSourceConfig) -> list[str]:
        """Return config key names so the UI knows which keys are set."""
        return sorted(obj.config.keys()) if obj.config else []

    def validate_source_type(self, value: str) -> str:
        from adapters.registry import registered_source_types
        valid = registered_source_types()
        if value not in valid:
            raise serializers.ValidationError(
                f"Unknown source_type '{value}'. Valid choices: {valid}"
            )
        return value

    def create(self, validated_data: dict) -> TaskSourceConfig:
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


# ---------------------------------------------------------------------------
# Playlist
# ---------------------------------------------------------------------------

class PlaylistSerializer(serializers.ModelSerializer):
    """Serializer for Playlist CRUD.

    When is_default is set to True via this serializer the viewset is
    responsible for clearing other defaults (single-default invariant).
    """

    source_display = serializers.CharField(source="get_source_display", read_only=True)
    mode_display = serializers.CharField(source="get_mode_display", read_only=True)

    class Meta:
        model = Playlist
        fields = [
            "id",
            "name",
            "url",
            "source",
            "source_display",
            "mode",
            "mode_display",
            "is_default",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "source_display", "mode_display", "created_at", "updated_at"]

    def create(self, validated_data: dict) -> Playlist:
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


# ---------------------------------------------------------------------------
# TaskDTO (read-only output serializer — not tied to a DB model)
# ---------------------------------------------------------------------------

class TaskDTOSerializer(serializers.Serializer):
    """Read-only serializer for TaskDTO objects returned by adapters.

    Used by UnifiedTaskViewSet to produce consistent JSON from any source.
    """

    id = serializers.CharField(read_only=True)
    title = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True, allow_blank=True)
    status = serializers.CharField(read_only=True)
    priority = serializers.CharField(read_only=True)
    labels = serializers.ListField(
        child=serializers.CharField(), read_only=True
    )
    due_date = serializers.DateTimeField(read_only=True, allow_null=True)
    estimated_minutes = serializers.IntegerField(read_only=True, allow_null=True)
    source = serializers.CharField(read_only=True)
    source_url = serializers.CharField(read_only=True, allow_blank=True)

    def to_representation(self, instance: TaskDTO) -> dict:  # type: ignore[override]
        return {
            "id": instance.id,
            "title": instance.title,
            "description": instance.description,
            "status": instance.status,
            "priority": instance.priority,
            "labels": instance.labels,
            "due_date": instance.due_date.isoformat() if instance.due_date else None,
            "estimated_minutes": instance.estimated_minutes,
            "source": instance.source,
            "source_url": instance.source_url,
        }
