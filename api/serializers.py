from rest_framework import serializers

from app.models import (
    Session,
    LocalTask,
    EnergyReading,
    UserSettings,
    MODE_DEFAULTS,
)


class SessionSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Session
        fields = [
            "id",
            "username",
            "mode",
            "started_at",
            "ended_at",
            "planned_duration",
            "actual_duration",
            "task_id",
            "task_title",
            "task_source",
            "energy_before",
            "energy_after",
            "playlist_url",
            "notes",
            "completed",
            "tag",
        ]
        read_only_fields = ["id", "username"]

    def validate_mode(self, value):
        valid_modes = [c[0] for c in Session._meta.get_field("mode").choices]
        if value not in valid_modes:
            raise serializers.ValidationError(
                f"Invalid mode '{value}'. Choose from: {valid_modes}"
            )
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        mode = validated_data.get("mode", "pomodoro")

        # Auto-fill planned_duration from mode defaults if not provided
        if "planned_duration" not in validated_data or not validated_data["planned_duration"]:
            defaults = MODE_DEFAULTS.get(mode, {})
            validated_data["planned_duration"] = defaults.get("work", 25)

        validated_data["user"] = user
        return super().create(validated_data)


class SessionCompleteSerializer(serializers.Serializer):
    """Serializer for the session complete action."""
    energy_after = serializers.IntegerField(min_value=1, max_value=5, required=False)
    notes = serializers.CharField(required=False, allow_blank=True)


class LocalTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocalTask
        fields = [
            "id",
            "title",
            "description",
            "status",
            "priority",
            "labels",
            "due_date",
            "estimated_minutes",
            "display_order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class EnergyReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnergyReading
        fields = ["id", "timestamp", "level", "context", "session"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class UserSettingsSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = UserSettings
        fields = [
            "username",
            "theme",
            "startSound",
            "stopSound",
            "focusTime",
            "shortBreak",
            "longBreak",
            "focusColor",
            "breakColor",
            "image",
            "timezone",
            "deep_work_duration",
            "sprint_duration",
            "free_flow_enabled",
            "auto_mode_selection",
            "mode_label_map",
            "energy_tracking_enabled",
            "youtube_default_playlists",
            "profile_public",
        ]
        read_only_fields = ["username"]
