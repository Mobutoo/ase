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
