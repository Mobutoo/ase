from __future__ import annotations

from django.contrib.auth.models import User
from django.db import models


CIRCLE_PRESET_CHOICES = (
    ("family", "Famille"),
    ("colocation", "Colocation"),
    ("team", "Equipe"),
    ("club", "Club / Association"),
    ("custom", "Personnalise"),
)


class Circle(models.Model):
    """N circles par tenant (ex: famille + club sport + projet pro)."""

    name = models.CharField(max_length=255)
    preset = models.CharField(
        max_length=20,
        choices=CIRCLE_PRESET_CHOICES,
        default="family",
    )
    tenant_id = models.CharField(max_length=255, db_index=True)
    is_primary = models.BooleanField(default=False)
    timezone = models.CharField(max_length=50, default="UTC")
    agent_enabled = models.BooleanField(default=True)
    agent_budget_limit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=50.00,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id"],
                condition=models.Q(is_primary=True),
                name="unique_primary_circle_per_tenant",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.preset})"


MEMBERSHIP_TYPE_CHOICES = (
    ("local", "Local"),
    ("federated", "Federated"),
)

# All valid roles across all presets
ROLE_CHOICES = (
    ("admin", "Admin"),
    ("adult", "Adult"),
    ("child", "Child"),
    ("guest", "Guest"),
    ("roommate", "Roommate"),
    ("member", "Member"),
    ("coach", "Coach"),
    ("player", "Player"),
    ("parent", "Parent"),
    ("intern", "Intern"),
)

# Roles allowed per preset
PRESET_ROLES: dict[str, tuple[str, ...]] = {
    "family": ("admin", "adult", "child", "guest", "parent"),
    "colocation": ("admin", "adult", "roommate", "guest"),
    "team": ("admin", "adult", "member", "intern", "guest"),
    "club": ("admin", "coach", "player", "member", "guest"),
    "custom": tuple(r[0] for r in ROLE_CHOICES),
}


class CircleMember(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="circle_memberships",
    )
    circle = models.ForeignKey(
        Circle,
        on_delete=models.CASCADE,
        related_name="members",
    )
    role = models.CharField(max_length=20)
    display_name = models.CharField(max_length=100)
    avatar_color = models.CharField(max_length=7, default="#E76F51")
    avatar_emoji = models.CharField(max_length=10, blank=True, default="")
    invite_token = models.CharField(max_length=255, blank=True, default="")
    invite_accepted_at = models.DateTimeField(null=True, blank=True)
    membership_type = models.CharField(
        max_length=20,
        choices=MEMBERSHIP_TYPE_CHOICES,
        default="local",
    )
    external_issuer = models.URLField(blank=True, null=True)
    external_sub = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "circle")]
        constraints = [
            models.UniqueConstraint(
                fields=["circle", "external_issuer", "external_sub"],
                condition=models.Q(membership_type="federated"),
                name="unique_federated_member_per_circle",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.display_name} ({self.role}) in {self.circle.name}"
