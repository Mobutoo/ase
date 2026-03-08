"""
Phase 3+4 models — Achievement and DailyPlan.

These are additive: they import from app.models but do not modify it.
"""

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# Achievement
# ---------------------------------------------------------------------------

ACHIEVEMENT_TYPES = (
    # Session milestones
    ("first_session", "First Session"),
    ("sessions_10", "10 Sessions"),
    ("sessions_50", "50 Sessions"),
    ("sessions_100", "100 Sessions"),
    ("sessions_500", "500 Sessions"),
    # Streak milestones
    ("streak_3", "3-Day Streak"),
    ("streak_7", "7-Day Streak"),
    ("streak_30", "30-Day Streak"),
    # Behaviour
    ("energy_tracker", "Energy Tracker"),
    ("deep_work_master", "Deep Work Master"),
    # Reflection
    ("first_reflection", "First Reflection"),
    ("reflections_7", "7 Reflections"),
    # Planning
    ("first_plan", "First Daily Plan"),
    ("plans_30", "30 Daily Plans"),
)

ACHIEVEMENT_TYPE_VALUES = [t[0] for t in ACHIEVEMENT_TYPES]


class Achievement(models.Model):
    """
    Records a moment when a user unlocked an achievement.

    One record per (user, achievement_type) pair — enforced by unique_together.
    """

    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="achievements",
    )
    achievement_type = models.CharField(
        max_length=32,
        choices=ACHIEVEMENT_TYPES,
    )
    unlocked_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("user", "achievement_type")]
        ordering = ["-unlocked_at"]
        verbose_name = "Achievement"
        verbose_name_plural = "Achievements"

    def __str__(self):
        return f"{self.user.username} | {self.achievement_type} | {self.unlocked_at.date()}"


# ---------------------------------------------------------------------------
# DailyPlan
# ---------------------------------------------------------------------------

class DailyPlan(models.Model):
    """
    A user's intention for a single day — tasks to focus on plus end-of-day reflection.

    planned_tasks is a JSON list of task objects:
        [{"id": ..., "title": ..., "source": "local"|"plane", "estimated_minutes": ...}]

    focus_score is computed by analytics.get_focus_score() at day's end and stored here
    for fast retrieval.
    """

    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="daily_plans",
    )
    date = models.DateField(default=timezone.localdate)
    planned_tasks = models.JSONField(
        default=list,
        blank=True,
        help_text="List of task objects planned for this day",
    )
    focus_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Focus score 0-100, computed at end of day",
    )
    reflection = models.TextField(
        blank=True,
        default="",
        help_text="End-of-day reflection text",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("user", "date")]
        ordering = ["-date"]
        verbose_name = "Daily Plan"
        verbose_name_plural = "Daily Plans"

    def __str__(self):
        return f"{self.user.username} | {self.date} | score={self.focus_score}"
