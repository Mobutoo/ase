"""
Phase 3+4 serializers — Achievement and DailyPlan.

These are additive: they do not modify api/serializers.py.
"""

from rest_framework import serializers

from app.models_phase34 import ACHIEVEMENT_TYPES, Achievement, DailyPlan


# ---------------------------------------------------------------------------
# Achievement
# ---------------------------------------------------------------------------

class AchievementSerializer(serializers.ModelSerializer):
    """Read-only serializer for Achievement records."""

    username = serializers.CharField(source="user.username", read_only=True)
    label = serializers.SerializerMethodField()

    class Meta:
        model = Achievement
        fields = ["id", "username", "achievement_type", "label", "unlocked_at"]
        read_only_fields = ["id", "username", "unlocked_at"]

    def get_label(self, obj) -> str:
        label_map = dict(ACHIEVEMENT_TYPES)
        return label_map.get(obj.achievement_type, obj.achievement_type)


class AchievementUnlockSerializer(serializers.Serializer):
    """
    Input serializer for the unlock endpoint.

    Used when an achievement is explicitly granted via the API
    (e.g. after client-side verification of first_reflection).
    """

    achievement_type = serializers.ChoiceField(
        choices=[t[0] for t in ACHIEVEMENT_TYPES]
    )


# ---------------------------------------------------------------------------
# DailyPlan
# ---------------------------------------------------------------------------

class PlannedTaskSerializer(serializers.Serializer):
    """Validate a single task entry inside DailyPlan.planned_tasks."""

    id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    title = serializers.CharField(max_length=500)
    source = serializers.ChoiceField(
        choices=["local", "plane"],
        default="local",
    )
    estimated_minutes = serializers.IntegerField(
        required=False, allow_null=True, min_value=1
    )


class DailyPlanSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = DailyPlan
        fields = [
            "id",
            "username",
            "date",
            "planned_tasks",
            "focus_score",
            "reflection",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "username", "focus_score", "created_at", "updated_at"]

    def validate_planned_tasks(self, value):
        """Ensure each task object has the required shape."""
        if not isinstance(value, list):
            raise serializers.ValidationError("planned_tasks must be a list.")
        validated = []
        for idx, item in enumerate(value):
            task_serializer = PlannedTaskSerializer(data=item)
            if not task_serializer.is_valid():
                raise serializers.ValidationError(
                    {f"planned_tasks[{idx}]": task_serializer.errors}
                )
            validated.append(task_serializer.validated_data)
        return validated

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Immutable pattern: discard user override if accidentally passed
        validated_data.pop("user", None)
        return super().update(instance, validated_data)


class DailyPlanReflectSerializer(serializers.Serializer):
    """Input serializer for the reflect action on DailyPlanViewSet."""

    reflection = serializers.CharField(
        allow_blank=False,
        max_length=5000,
    )


# ---------------------------------------------------------------------------
# Analytics response shapes (not model-backed — plain Serializers for docs)
# ---------------------------------------------------------------------------

class DailyStatsSerializer(serializers.Serializer):
    date = serializers.DateField()
    total_sessions = serializers.IntegerField()
    total_minutes = serializers.IntegerField()
    avg_energy_before = serializers.FloatField()
    avg_energy_after = serializers.FloatField()
    mode_breakdown = serializers.ListField(child=serializers.DictField())


class StreakSerializer(serializers.Serializer):
    current_streak = serializers.IntegerField()
    longest_streak = serializers.IntegerField()
    freeze_days_used = serializers.IntegerField()
    last_active_date = serializers.DateField(allow_null=True)


class HeatmapEntrySerializer(serializers.Serializer):
    hour = serializers.IntegerField(min_value=0, max_value=23)
    weekday = serializers.IntegerField(min_value=1, max_value=7)
    avg_level = serializers.FloatField()


class DensityEntrySerializer(serializers.Serializer):
    date = serializers.DateField()
    intensity = serializers.IntegerField(min_value=0, max_value=4)
    total_minutes = serializers.IntegerField()
    session_count = serializers.IntegerField()


class LeaderboardEntrySerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    username = serializers.CharField()
    avatar = serializers.CharField()
    total_minutes = serializers.IntegerField()
    total_sessions = serializers.IntegerField()
