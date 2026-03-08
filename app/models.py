from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone

from datetime import datetime, timedelta
from math import ceil


# --- Flow Modes ---
MODE_CHOICES = (
    ("deep_work", "Deep Work"),
    ("pomodoro", "Pomodoro"),
    ("kids", "Kids"),
    ("sprint", "Sprint"),
    ("free_flow", "Free Flow"),
)

# Default durations per mode (minutes)
MODE_DEFAULTS = {
    "deep_work": {"work": 90, "break": 20},
    "pomodoro": {"work": 25, "short_break": 5, "long_break": 15},
    "kids": {"work": 15, "short_break": 5, "long_break": 10, "long_break_interval": 3},
    "sprint": {"work": 45, "break": 10},
    "free_flow": {"work": 0, "break_ratio": 0.2},
}

ENERGY_CHOICES = ((1, "1"), (2, "2"), (3, "3"), (4, "4"), (5, "5"))

ENERGY_CONTEXT_CHOICES = (
    ("session_start", "Session Start"),
    ("session_end", "Session End"),
    ("check_in", "Check-in"),
)

TASK_STATUS_CHOICES = (
    ("todo", "To Do"),
    ("in_progress", "In Progress"),
    ("done", "Done"),
)

TASK_PRIORITY_CHOICES = (
    ("urgent", "Urgent"),
    ("high", "High"),
    ("medium", "Medium"),
    ("low", "Low"),
    ("none", "None"),
)


class Session(models.Model):
    """A focus session — the core unit of work in Ase."""
    user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="sessions"
    )
    mode = models.CharField(max_length=16, choices=MODE_CHOICES, default="pomodoro")
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    planned_duration = models.PositiveIntegerField(
        help_text="Planned duration in minutes"
    )
    actual_duration = models.PositiveIntegerField(
        null=True, blank=True, help_text="Actual duration in minutes"
    )

    # Task link (agnostic — any source via adapter)
    task_id = models.CharField(max_length=255, null=True, blank=True)
    task_title = models.CharField(max_length=500, null=True, blank=True)
    task_source = models.CharField(
        max_length=64, default="local", help_text="Adapter source: local, plane, etc."
    )

    # Energy tracking
    energy_before = models.PositiveSmallIntegerField(
        null=True, blank=True, choices=ENERGY_CHOICES
    )
    energy_after = models.PositiveSmallIntegerField(
        null=True, blank=True, choices=ENERGY_CHOICES
    )

    # Music
    playlist_url = models.URLField(max_length=500, null=True, blank=True)

    # Meta
    notes = models.TextField(blank=True, default="")
    completed = models.BooleanField(default=False)
    tag = models.ForeignKey(
        "Tag", on_delete=models.SET_NULL, null=True, blank=True, related_name="sessions"
    )

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.user.username} | {self.mode} | {self.started_at}"


class LocalTask(models.Model):
    """Ad-hoc tasks created directly in Ase (not from external sources)."""
    user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="local_tasks"
    )
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=16, choices=TASK_STATUS_CHOICES, default="todo"
    )
    priority = models.CharField(
        max_length=16, choices=TASK_PRIORITY_CHOICES, default="none"
    )
    labels = models.JSONField(default=list, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    estimated_minutes = models.PositiveIntegerField(null=True, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "-created_at"]

    def __str__(self):
        return f"{self.user.username} | {self.title} [{self.status}]"


class EnergyReading(models.Model):
    """Energy self-report (1-5) for pattern tracking."""
    user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="energy_readings"
    )
    timestamp = models.DateTimeField(default=timezone.now)
    level = models.PositiveSmallIntegerField(choices=ENERGY_CHOICES)
    context = models.CharField(
        max_length=16, choices=ENERGY_CONTEXT_CHOICES, default="check_in"
    )
    session = models.ForeignKey(
        Session, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="energy_readings"
    )

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.user.username} | {self.level}/5 | {self.context}"


# --- Legacy PomoTracker model (kept for data migration) ---

class Pomodoro(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE,
                            related_name='pomodoros')
    datetime = models.DateTimeField(default=timezone.now)
    tag = models.ForeignKey('Tag', on_delete=models.PROTECT,
                            related_name='pomodoros')

    def serialize(self):
        timezone.activate(self.user.settings.timezone)
        return {
            'id': self.id,
            'user': self.user.username,
            'created_at': timezone.localtime(self.datetime),
            'tag': self.tag.tag
        }

    def checkLastCreated(self):
        user = self.user
        if user.pomodoros.last() == user.pomodoros.first():
            return True
        date1 = self.datetime
        date2 = user.pomodoros.all().order_by('-id')[1].datetime
        diff = date1 - date2
        if (diff.total_seconds() / 60) < 24.9:
            return False
        return True

    def __str__(self):
        return f'{self.id}, {self.user}, {self.datetime}, {self.tag}'


class SlicePomodoros:
    """Slice pomodoros by year, month, week and day"""
    def __init__(self, pomodoros, user):
        self.user = user
        self.all = pomodoros.all()
        self.year = pomodoros.filter(datetime__year=datetime.now().year)
        self.month = pomodoros.filter(datetime__month=datetime.now().month,
                                    datetime__year=datetime.now().year)
        self.week = pomodoros.filter(datetime__week=datetime.now()
                                        .isocalendar().week,
                                    datetime__month=datetime.now().month,
                                    datetime__year=datetime.now().year)
        self.day = pomodoros.filter(datetime__day=datetime.now().day,
                                    datetime__week=datetime.now()
                                        .isocalendar().week,
                                    datetime__month=datetime.now().month,
                                    datetime__year=datetime
                                        .now().year).order_by('datetime')


class Tag(models.Model):
    tag = models.CharField(max_length=24, null=False, unique=True)

    def __str__(self):
        return f'{self.tag}'


class UserSettings(models.Model):
    sound_choices_start = (
        ('#ding', 'ding'),
        ('#folks', 'nanana')
    )
    sound_choices_stop = (
        ('#minion', 'minion'),
        ('#whoosh', 'whoosh')
    )
    theme_choices = (
        ('default', 'default'),
        ('white', 'white'),
        ('forest', 'forest'),
        ('aquamarine', 'aquamarine'),
        ('garnet', 'garnet'),
        ('coral', 'coral'),
        ('afrofuturist', 'afrofuturist'),
    )

    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE,
                                    related_name='settings')
    token = models.CharField(max_length=27, null=True, unique=True)
    theme = models.CharField(max_length=16, default='default', choices=theme_choices)
    image = models.CharField(max_length=256, default='default.png')
    startSound = models.CharField(max_length=16,
                                    choices=sound_choices_start, default='#ding')
    stopSound = models.CharField(max_length=16, choices=sound_choices_stop,
                                    default='#whoosh')
    focusTime = models.PositiveSmallIntegerField(default=25)
    shortBreak = models.PositiveSmallIntegerField(default=5)
    longBreak = models.PositiveSmallIntegerField(default=15)
    focusColor = models.CharField(default='#f1c232', max_length=7)
    breakColor = models.CharField(default='#ADFF2F', max_length=7)
    timezone = models.CharField(max_length=64, default='UTC')

    # --- Ase Flow Engine additions ---
    deep_work_duration = models.PositiveSmallIntegerField(default=90)
    sprint_duration = models.PositiveSmallIntegerField(default=45)
    free_flow_enabled = models.BooleanField(default=True)
    auto_mode_selection = models.BooleanField(default=True)
    mode_label_map = models.JSONField(
        default=dict, blank=True,
        help_text="Mapping of mode → label list for auto-detection"
    )
    energy_tracking_enabled = models.BooleanField(default=True)
    youtube_default_playlists = models.JSONField(
        default=dict, blank=True,
        help_text="Mode → YouTube playlist URL mapping"
    )
    streak_freeze_days_remaining = models.PositiveSmallIntegerField(default=3)
    streak_freeze_reset_date = models.DateField(null=True, blank=True)
    profile_public = models.BooleanField(default=False)

    def serialize(self):
        return {
            'user': self.user.username,
            'theme': self.theme,
            'startSound': self.startSound,
            'stopSound': self.stopSound,
            'focusTime': self.focusTime,
            'longBreak': self.longBreak,
            'shortBreak': self.shortBreak,
            'focusColor': self.focusColor,
            'breakColor': self.breakColor,
            'token': self.token,
            'image': self.image,
            'deep_work_duration': self.deep_work_duration,
            'sprint_duration': self.sprint_duration,
            'free_flow_enabled': self.free_flow_enabled,
            'auto_mode_selection': self.auto_mode_selection,
            'mode_label_map': self.mode_label_map,
            'energy_tracking_enabled': self.energy_tracking_enabled,
            'youtube_default_playlists': self.youtube_default_playlists,
            'profile_public': self.profile_public,
        }

    def __str__(self):
        return f'''{self.user.username}, {self.theme}, {self.image},
        {self.startSound}, {self.stopSound}, {self.focusTime}, {self.longBreak},
        {self.shortBreak}, {self.focusColor}, {self.breakColor}, {self.token,
        {self.timezone}}'''


class Rewards(models.Model):
    """Model for rewards"""
    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE,
                                related_name='rewards')
    gold = models.PositiveSmallIntegerField(default=0)
    silver = models.PositiveSmallIntegerField(default=0)
    bronze = models.PositiveSmallIntegerField(default=0)
    ranks = ArrayField(models.PositiveIntegerField(), default=list)

    def getAverageRank(self):
        """Returns the average rank"""
        if len(self.ranks) <= 1:
            return 'No rank'
        return round(sum(self.ranks) / len(self.ranks), ndigits=2)

    def getRewards(self):
        """Returns the rewards as a dictionary"""
        return {
            'gold': self.gold,
            'silver': self.silver,
            'bronze': self.bronze,
            'rank': self.getAverageRank()
        }

    def __str__(self):
        return f'''{self.user.username}, {self.gold},
        {self.silver}, {self.bronze}, {self.ranks}'''


AI_SUGGESTION_TYPE_CHOICES = (
    ("daily_plan", "Daily Plan"),
    ("task_decomposition", "Task Decomposition"),
    ("reflection_prompt", "Reflection Prompt"),
    ("energy_suggestion", "Energy Suggestion"),
)


class AISuggestion(models.Model):
    """AI-generated suggestion stored after n8n/OpenClaw processing."""
    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="ai_suggestions",
    )
    suggestion_type = models.CharField(
        max_length=32,
        choices=AI_SUGGESTION_TYPE_CHOICES,
    )
    content = models.JSONField(help_text="Structured suggestion data from AI")
    accepted = models.BooleanField(
        null=True,
        blank=True,
        help_text="True=accepted, False=dismissed, None=pending user action",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} | {self.suggestion_type} | {self.created_at}"


# ---------------------------------------------------------------------------
# Import phase-specific models so Django migration system discovers them.
# These live in separate files for maintainability but are part of the "app".
# ---------------------------------------------------------------------------
from app.models_phase2 import TaskSourceConfig, Playlist  # noqa: E402, F401
from app.models_phase34 import Achievement, DailyPlan  # noqa: E402, F401


class Statistics:

    @staticmethod
    def getAveragePomodoros(user):
        """Returns the total average pomodoros"""
        # Get all pomodoros
        pomodoros = user.pomodoros.all()
        # Make sure there are pomodoros
        if not pomodoros:
            return 0
        # Get the first pomodoro
        first = pomodoros.first()
        # Get the difference between the first pomodoro day and today
        diff = timezone.now() - first.datetime
        # Get the number of pomodoros
        num = pomodoros.count()
        # Get the average pomodoros per day
        try:
            avg = num / diff.days
        except ZeroDivisionError:
            avg = num
        return round(avg, ndigits=2)

    @staticmethod
    def aggregatePomodorosByTag(user):
        """Returns a dictionary of tags and the number of pomodoros with the tag"""
        # Get all pomodoros
        pomodoros = user.pomodoros.all()
        # Make sure there are pomodoros
        if not pomodoros:
            return {}
        # Get all tags
        tags = Tag.objects.all()
        # Initialize the dictionary
        tagDict = {}
        # Loop through all tags
        for tag in tags:
            # Get all pomodoros with the tag
            pomodorosWithTag = pomodoros.filter(tag=tag)
            # Get the number of pomodoros with the tag
            num = pomodorosWithTag.count()
            # Add the number of pomodoros with the tag to the dictionary if it is
            #  not 0
            if num != 0:
                tagDict[tag.tag] = num
        return dict(sorted(tagDict.items(), key=lambda x: x[1], reverse=True))

    @staticmethod
    def totalSumPomodorosUser(user):
        """Returns the total sum of pomodoros"""
        # Get all pomodoros within the period
        pomodoros = user.pomodoros.all()
        # Make sure there are pomodoros
        if not pomodoros:
            return 0
        # Store the total sum of pomodoros
        totalSum = {}
        # Loop through all pomodoros
        for pomodoro in pomodoros:
            # Get the date of the pomodoro
            date = str(pomodoro.datetime.date())
            # Add the pomodoro to the total sum
            try:
                totalSum[date] += 1
            except KeyError:
                totalSum[date] = 1
        return totalSum

    @staticmethod
    def totalSumPomodorosPerUser():
        """Returns the total sum of pomodoros per user"""
        # Get all users
        users = get_user_model().objects.all()
        # Store the total sum of pomodoros
        totalSum = {}
        # Loop through all users
        for user in users:
            # Get the total sum of pomodoros for the user
            totalUser = Statistics.totalSumPomodorosUser(user)
            # Only add the user if there are pomodoros
            if totalUser:
                totalSum[user.username] = {'pomos': totalUser, 'image': user.settings.image, 'rewards': user.rewards.getRewards()}
        return totalSum
