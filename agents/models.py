from __future__ import annotations

from django.db import models


ACTION_TYPE_CHOICES = [
    ("event_create", "Create Event"),
    ("booking_propose", "Propose Booking"),
    ("event_suggest", "Suggest Event"),
    ("digest_send", "Send Digest"),
]


class AgentAction(models.Model):
    """Audit log — every agent action is logged here with integrity hash.

    The agent NEVER performs irreversible actions without human approval.
    All proposals go through this model before any state mutation occurs.
    """

    circle = models.ForeignKey(
        "circles.Circle",
        on_delete=models.CASCADE,
        related_name="agent_actions",
    )
    action_type = models.CharField(max_length=30, choices=ACTION_TYPE_CHOICES)
    payload = models.JSONField()
    proposed_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(
        "circles.CircleMember",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_actions",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True, default="")
    integrity_hash = models.CharField(max_length=64)  # SHA-256

    class Meta:
        ordering = ["-proposed_at"]
        indexes = [
            models.Index(fields=["circle", "action_type"]),
            models.Index(fields=["proposed_at"]),
        ]

    def __str__(self) -> str:
        return f"[{self.action_type}] circle={self.circle_id} at {self.proposed_at:%Y-%m-%d %H:%M}"

    @property
    def is_pending(self) -> bool:
        return self.approved_at is None and self.rejected_at is None

    @property
    def is_approved(self) -> bool:
        return self.approved_at is not None and self.rejected_at is None

    @property
    def is_rejected(self) -> bool:
        return self.rejected_at is not None

    @property
    def is_executed(self) -> bool:
        return self.executed_at is not None


class MemberPreference(models.Model):
    """Learned and declared preferences per circle member.

    Categories: restaurant, transport, schedule, communication, etc.
    Values are stored as JSON to support arbitrary preference shapes.
    """

    member = models.ForeignKey(
        "circles.CircleMember",
        on_delete=models.CASCADE,
        related_name="preferences",
    )
    category = models.CharField(max_length=50)  # restaurant, transport, schedule
    key = models.CharField(max_length=100)
    value = models.JSONField()
    confirmed = models.BooleanField(default=False)
    source = models.CharField(
        max_length=20,
        choices=[
            ("manual", "Manual"),
            ("learned", "Learned"),
            ("imported", "Imported"),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "key"]
        indexes = [
            models.Index(fields=["member", "category"]),
        ]
        unique_together = [("member", "category", "key")]

    def __str__(self) -> str:
        return f"{self.member} | {self.category}.{self.key} = {self.value!r}"


class NotificationPreference(models.Model):
    """Per-member notification channel and event-type preferences.

    OneToOne with CircleMember — created on first access via get_or_create.
    quiet_start/quiet_end define a do-not-disturb window in member's local timezone.
    """

    member = models.OneToOneField(
        "circles.CircleMember",
        on_delete=models.CASCADE,
        related_name="notification_prefs",
    )
    push_enabled = models.BooleanField(default=True)
    telegram_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=True)
    quiet_start = models.TimeField(null=True, blank=True)
    quiet_end = models.TimeField(null=True, blank=True)
    notify_event_created = models.BooleanField(default=True)
    notify_event_modified = models.BooleanField(default=True)
    notify_event_reminder = models.BooleanField(default=True)
    notify_agent_proposal = models.BooleanField(default=True)
    notify_agent_digest = models.BooleanField(default=True)
    notify_conflict = models.BooleanField(default=True)
    notify_invitation = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Notification Preference"
        verbose_name_plural = "Notification Preferences"

    def __str__(self) -> str:
        return f"NotifPrefs for {self.member}"

    def is_quiet_now(self, current_time: object) -> bool:
        """Return True if current_time falls within the quiet window."""
        if self.quiet_start is None or self.quiet_end is None:
            return False
        if self.quiet_start <= self.quiet_end:
            return self.quiet_start <= current_time <= self.quiet_end
        # Overnight window (e.g. 22:00 – 07:00)
        return current_time >= self.quiet_start or current_time <= self.quiet_end
