from __future__ import annotations

import uuid

from django.db import models


EVENT_TYPE_CHOICES = [
    ("event", "Event"),
    ("recurring", "Recurring"),
    ("background", "Background"),
    ("task", "Task"),
    ("dependent", "Dependent"),
]

VISIBILITY_CHOICES = [
    ("family", "Family"),
    ("adults_only", "Adults Only"),
    ("private", "Private"),
    ("custom", "Custom"),
]

DEPENDENT_TYPE_CHOICES = [
    ("transport", "Transport"),
    ("meal", "Meal"),
    ("accompany", "Accompany"),
    ("break", "Break"),
]

REMINDER_CHANNEL_CHOICES = [
    ("push", "Push"),
    ("telegram", "Telegram"),
    ("email", "Email"),
]


class Calendar(models.Model):
    owner = models.ForeignKey(
        "circles.CircleMember",
        on_delete=models.CASCADE,
        related_name="calendars",
    )
    name = models.CharField(max_length=255)
    color = models.CharField(max_length=7, default="#2D6A4F")
    icon = models.CharField(max_length=50, default="calendar")
    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default="family",
    )
    caldav_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.owner})"


class Event(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    calendar = models.ForeignKey(
        Calendar,
        on_delete=models.CASCADE,
        related_name="events",
    )
    parent_event = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True, default="")
    location = models.CharField(max_length=500, blank=True, default="")
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    all_day = models.BooleanField(default=False)
    event_type = models.CharField(
        max_length=20,
        choices=EVENT_TYPE_CHOICES,
        default="event",
    )
    display_mode = models.CharField(max_length=20, default="normal")
    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default="family",
    )
    # RRULE RFC 5545
    recurrence_rule = models.TextField(blank=True, null=True)
    members = models.ManyToManyField(
        "circles.CircleMember",
        blank=True,
        related_name="events",
    )
    linked_task = models.ForeignKey(
        "app.LocalTask",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="calendar_events",
    )
    # Event Graph
    dependent_type = models.CharField(
        max_length=20,
        choices=DEPENDENT_TYPE_CHOICES,
        null=True,
        blank=True,
    )
    booking_ref = models.JSONField(null=True, blank=True)
    validated_by = models.ForeignKey(
        "circles.CircleMember",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="validated_events",
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    # iCal subscription (read-only imported events)
    subscription = models.ForeignKey(
        "CalendarSubscription",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="imported_events",
    )
    ical_uid = models.CharField(
        max_length=512,
        blank=True,
        default="",
        help_text="Original UID from external iCal feed (arbitrary string, not a UUID).",
    )
    # Google Calendar sync
    google_event_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
        help_text="Google Calendar event ID (set when synced from/to Google).",
    )
    # CalDAV sync fields
    etag = models.CharField(max_length=64, blank=True, default="")
    caldav_raw = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_at"]
        indexes = [
            models.Index(fields=["calendar", "start_at", "end_at"]),
            models.Index(fields=["parent_event"]),
            models.Index(fields=["linked_task"]),
            models.Index(fields=["subscription", "ical_uid"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.start_at:%Y-%m-%d %H:%M})"


class EventException(models.Model):
    """Tracks overridden occurrences of a recurring event (EXDATE / RECURRENCE-ID)."""

    recurring_event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="exceptions",
    )
    original_start = models.DateTimeField()
    replacement_event = models.ForeignKey(
        Event,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("recurring_event", "original_start")]

    def __str__(self) -> str:
        return (
            f"Exception for {self.recurring_event} at "
            f"{self.original_start:%Y-%m-%d %H:%M}"
        )


class CalendarSubscription(models.Model):
    """An iCal URL subscription that syncs external events as read-only background events."""

    member = models.ForeignKey(
        "circles.CircleMember",
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    display_name = models.CharField(max_length=255)
    ical_url = models.URLField(max_length=1000)
    color = models.CharField(max_length=7, default="#9CA3AF")
    refresh_minutes = models.PositiveIntegerField(default=15)
    last_fetched_at = models.DateTimeField(null=True, blank=True)
    last_etag = models.CharField(max_length=128, blank=True, default="")
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_name"]

    def __str__(self) -> str:
        return f"{self.display_name} ({self.member})"


class EventReminder(models.Model):
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="reminders",
    )
    member = models.ForeignKey(
        "circles.CircleMember",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    offset_minutes = models.IntegerField()
    channel = models.CharField(max_length=20, choices=REMINDER_CHANNEL_CHOICES)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("event", "member", "offset_minutes", "channel")]

    def __str__(self) -> str:
        return (
            f"Reminder for {self.event} — {self.offset_minutes}min via {self.channel}"
        )


SYNC_DIRECTION_CHOICES = [
    ("both", "Bidirectional"),
    ("push", "Ase to Google only"),
    ("pull", "Google to Ase only"),
]


class GoogleCalendarSync(models.Model):
    """Configuration for bidirectional Google Calendar sync via the gws CLI.

    Each instance links one Ase calendar to one Google Calendar ID and tracks
    incremental sync state (sync_token) for efficient delta polling.
    """

    member = models.ForeignKey(
        "circles.CircleMember",
        on_delete=models.CASCADE,
        related_name="google_syncs",
    )
    ase_calendar = models.ForeignKey(
        Calendar,
        on_delete=models.CASCADE,
        related_name="google_syncs",
    )
    google_calendar_id = models.CharField(
        max_length=255,
        help_text="Google Calendar ID (e.g. 'primary' or email address).",
    )
    google_account_email = models.EmailField(
        help_text="Google account email for gws CLI auth.",
    )
    sync_token = models.CharField(max_length=500, blank=True, default="")
    last_synced_at = models.DateTimeField(null=True, blank=True)
    enabled = models.BooleanField(default=True)
    sync_direction = models.CharField(
        max_length=10,
        choices=SYNC_DIRECTION_CHOICES,
        default="both",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("member", "google_calendar_id")]

    def __str__(self) -> str:
        direction_arrow = {"both": "\u2194", "push": "\u2192", "pull": "\u2190"}.get(
            self.sync_direction, "\u2194"
        )
        return f"{self.member} {direction_arrow} {self.google_calendar_id}"
