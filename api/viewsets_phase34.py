"""
Phase 3+4 viewsets — Analytics, Leaderboard, DailyPlan, enhanced Energy.

All viewsets follow the DRF patterns established in api/viewsets.py.
No existing files are modified.
"""

from datetime import date

from django.utils import timezone
from rest_framework import serializers as drf_serializers
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from app.analytics import (
    check_achievements,
    get_daily_stats,
    get_density_chart,
    get_energy_heatmap,
    get_focus_score,
    get_leaderboard,
    get_monthly_stats,
    get_streak,
    get_weekly_stats,
)
from app.models import EnergyReading
from app.models_phase34 import Achievement, DailyPlan
from api.serializers_phase34 import (
    AchievementSerializer,
    AchievementUnlockSerializer,
    DailyPlanReflectSerializer,
    DailyPlanSerializer,
    DensityEntrySerializer,
    HeatmapEntrySerializer,
    LeaderboardEntrySerializer,
    StreakSerializer,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date_param(request, param: str, default: date) -> date:
    """Parse a ?date=YYYY-MM-DD query param, returning default on error."""
    raw = request.query_params.get(param)
    if not raw:
        return default
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return default


def _parse_year_param(request, param: str, default: int) -> int:
    """Parse a ?year=YYYY query param, returning default on error."""
    raw = request.query_params.get(param)
    if not raw:
        return default
    try:
        value = int(raw)
        if 2000 <= value <= 2100:
            return value
        return default
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# AnalyticsViewSet
# ---------------------------------------------------------------------------

class AnalyticsViewSet(viewsets.GenericViewSet):
    """
    Analytics endpoints for the authenticated user.

    All endpoints are GET-only (read-only analytics, immutable).

    Routes (registered under /api/v1/analytics/):
        GET /analytics/daily/         ?date=YYYY-MM-DD
        GET /analytics/weekly/        ?date=YYYY-MM-DD
        GET /analytics/monthly/       ?date=YYYY-MM-DD
        GET /analytics/density/       ?year=YYYY
        GET /analytics/streak/
        GET /analytics/achievements/
    """

    # Required by GenericViewSet even when all actions are custom
    def get_queryset(self):
        return None  # pragma: no cover

    @action(detail=False, methods=["get"])
    def daily(self, request):
        """Daily session stats. ?date=YYYY-MM-DD (default: today)."""
        target = _parse_date_param(request, "date", timezone.localdate())
        stats = get_daily_stats(request.user, target)
        return Response(stats)

    @action(detail=False, methods=["get"])
    def weekly(self, request):
        """Weekly session stats. ?date=YYYY-MM-DD (default: today's week)."""
        target = _parse_date_param(request, "date", timezone.localdate())
        stats = get_weekly_stats(request.user, target)
        return Response(stats)

    @action(detail=False, methods=["get"])
    def monthly(self, request):
        """Monthly session stats. ?date=YYYY-MM-DD (default: current month)."""
        target = _parse_date_param(request, "date", timezone.localdate())
        stats = get_monthly_stats(request.user, target)
        return Response(stats)

    @action(detail=False, methods=["get"])
    def density(self, request):
        """
        GitHub-style contribution density for a year.
        ?year=YYYY (default: current year)
        """
        year = _parse_year_param(request, "year", timezone.localdate().year)
        chart = get_density_chart(request.user, year)
        return Response(chart)

    @action(detail=False, methods=["get"])
    def streak(self, request):
        """Current and longest streak for the authenticated user."""
        streak_data = get_streak(request.user)
        serializer = StreakSerializer(data=streak_data)
        serializer.is_valid()  # always valid — data comes from our own function
        return Response(serializer.data)

    @action(detail=False, methods=["get", "post"])
    def achievements(self, request):
        """
        GET  — list all unlocked achievements for the user.
        POST — unlock one or more newly earned achievements.
                Body: {"achievement_type": "<type>"}
                Returns the created Achievement record.
        """
        if request.method == "GET":
            qs = Achievement.objects.filter(user=request.user)
            serializer = AchievementSerializer(qs, many=True)
            return Response(serializer.data)

        # POST: check + unlock
        input_serializer = AchievementUnlockSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        ach_type = input_serializer.validated_data["achievement_type"]

        # Verify the achievement is actually earned before storing it
        newly_earned = check_achievements(request.user)
        if ach_type not in newly_earned:
            return Response(
                {"error": f"Achievement '{ach_type}' is not yet earned."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        achievement, created = Achievement.objects.get_or_create(
            user=request.user,
            achievement_type=ach_type,
        )
        output_serializer = AchievementSerializer(achievement)
        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# LeaderboardViewSet
# ---------------------------------------------------------------------------

class LeaderboardViewSet(viewsets.GenericViewSet):
    """
    Public leaderboard endpoints.

    Routes (registered under /api/v1/leaderboard/):
        GET /leaderboard/         ?period=weekly|monthly|all_time
        GET /leaderboard/rewards/ (summary of current user's achievements)
    """

    VALID_PERIODS = ("weekly", "monthly", "all_time")

    def get_queryset(self):
        return None  # pragma: no cover

    def list(self, request):
        """
        Return ranked leaderboard.
        Only users with profile_public=True appear on the board.
        ?period=weekly (default) | monthly | all_time
        """
        period = request.query_params.get("period", "weekly")
        if period not in self.VALID_PERIODS:
            return Response(
                {"error": f"Invalid period. Choose from: {self.VALID_PERIODS}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        board = get_leaderboard(period)
        serializer = LeaderboardEntrySerializer(board, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def rewards(self, request):
        """Return the current user's achievement count and recent unlocks."""
        achievements = Achievement.objects.filter(user=request.user)
        total = achievements.count()
        recent = achievements[:5]
        return Response(
            {
                "total_achievements": total,
                "recent": AchievementSerializer(recent, many=True).data,
            }
        )


# ---------------------------------------------------------------------------
# DailyPlanViewSet
# ---------------------------------------------------------------------------

class DailyPlanViewSet(viewsets.ModelViewSet):
    """
    CRUD + reflect action for daily plans.

    Routes (registered under /api/v1/plans/):
        GET    /plans/           list all plans
        POST   /plans/           create a plan
        GET    /plans/{id}/      retrieve a plan
        PATCH  /plans/{id}/      update a plan
        DELETE /plans/{id}/      delete a plan
        POST   /plans/{id}/reflect/   submit end-of-day reflection + compute focus score
    """

    serializer_class = DailyPlanSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        qs = DailyPlan.objects.filter(user=self.request.user)
        # Optional ?date= filter
        date_param = self.request.query_params.get("date")
        if date_param:
            try:
                qs = qs.filter(date=date.fromisoformat(date_param))
            except ValueError:
                pass
        return qs

    @action(detail=True, methods=["post"])
    def reflect(self, request, pk=None):
        """
        Submit end-of-day reflection for a plan and compute the day's focus score.

        Body: {"reflection": "..."}
        Side effects:
          - Saves reflection text to DailyPlan.
          - Computes and saves focus_score via analytics.get_focus_score().
          - Checks and unlocks new achievements (first_reflection, reflections_7).
        """
        plan = self.get_object()

        input_serializer = DailyPlanReflectSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        # Compute focus score for the plan's date
        computed_score = get_focus_score(request.user, plan.date)

        # Persist — immutable update pattern
        plan.reflection = input_serializer.validated_data["reflection"]
        plan.focus_score = computed_score
        plan.save(update_fields=["reflection", "focus_score", "updated_at"])

        # Check reflection-based achievements
        self._unlock_reflection_achievements(request.user)

        return Response(DailyPlanSerializer(plan).data)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _unlock_reflection_achievements(user):
        """Unlock reflection achievements if newly earned (silent, no error on race)."""
        reflection_count = DailyPlan.objects.filter(
            user=user
        ).exclude(reflection="").count()

        candidates = []
        if reflection_count >= 1:
            candidates.append("first_reflection")
        if reflection_count >= 7:
            candidates.append("reflections_7")

        already_unlocked = set(
            Achievement.objects.filter(
                user=user, achievement_type__in=candidates
            ).values_list("achievement_type", flat=True)
        )

        for ach_type in candidates:
            if ach_type not in already_unlocked:
                Achievement.objects.get_or_create(
                    user=user,
                    achievement_type=ach_type,
                )


# ---------------------------------------------------------------------------
# Enhanced Energy ViewSet (heatmap + predict)
# ---------------------------------------------------------------------------

class EnergyAnalyticsViewSet(viewsets.GenericViewSet):
    """
    Additional energy analytics endpoints.

    Routes (registered under /api/v1/energy-analytics/):
        GET /energy-analytics/heatmap/  ?days=30
        GET /energy-analytics/predict/  ?date=YYYY-MM-DD
    """

    def get_queryset(self):
        return EnergyReading.objects.filter(user=self.request.user)

    @action(detail=False, methods=["get"])
    def heatmap(self, request):
        """
        Return average energy by hour-of-day and weekday.
        ?days=30 (default) — how many past days to include.
        """
        try:
            days = int(request.query_params.get("days", 30))
            if days < 1 or days > 365:
                raise ValueError
        except (ValueError, TypeError):
            return Response(
                {"error": "days must be an integer between 1 and 365."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        heatmap = get_energy_heatmap(request.user, days=days)
        serializer = HeatmapEntrySerializer(heatmap, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def predict(self, request):
        """
        Predict the best time slots for a target date based on historical energy.

        Returns the top 3 hour slots (within working hours 06-22) with the
        historically highest average energy for the matching weekday.

        ?date=YYYY-MM-DD (default: tomorrow)
        """
        tomorrow = timezone.localdate() + __import__("datetime").timedelta(days=1)
        target = _parse_date_param(request, "date", tomorrow)

        # Use full 90-day heatmap for prediction
        heatmap = get_energy_heatmap(request.user, days=90)

        # Filter to the target weekday (ISO: Mon=1..Sun=7)
        target_weekday = target.isoweekday()
        relevant = [
            h for h in heatmap
            if h["weekday"] == target_weekday and 6 <= h["hour"] <= 22
        ]

        # Sort by avg_level descending, take top 3
        top_slots = sorted(relevant, key=lambda h: h["avg_level"], reverse=True)[:3]

        return Response(
            {
                "date": target.isoformat(),
                "weekday": target_weekday,
                "predicted_peak_hours": [
                    {
                        "hour": slot["hour"],
                        "avg_energy": slot["avg_level"],
                        "label": f"{slot['hour']:02d}:00",
                    }
                    for slot in top_slots
                ],
            }
        )
