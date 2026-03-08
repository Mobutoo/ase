"""Phase 2 models — Task source configs and Playlist.

These models will be merged into models.py in a subsequent migration step.
They are isolated here to avoid touching the stable Phase 1 schema.

Relationships:
    TaskSourceConfig  FK→ User   — one config row per enabled external source
    Playlist          FK→ User   — saved music playlists, one may be default per user
"""
from django.contrib.auth import get_user_model
from django.db import models

from app.models import MODE_CHOICES


# ---------------------------------------------------------------------------
# Task Source Configuration
# ---------------------------------------------------------------------------

SOURCE_TYPE_CHOICES = (
    ("local", "Local (Ase)"),
    ("plane", "Plane"),
    ("github", "GitHub Issues"),
    ("superproductivity", "Super Productivity"),
)


class TaskSourceConfig(models.Model):
    """Stores credentials and config for an external task source.

    The config JSONField holds adapter-specific secrets/settings that are
    passed directly to the adapter constructor via the registry.

    Example config values:
        plane  → {"api_url": "...", "api_key": "...", "workspace_slug": "...", "project_id": "..."}
        github → {"token": "...", "owner": "...", "repo": "..."}
        local  → {} (no extra config needed)
    """

    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="task_source_configs",
    )
    source_type = models.CharField(
        max_length=32,
        choices=SOURCE_TYPE_CHOICES,
        help_text="Adapter identifier — must match a key in adapters.registry._REGISTRY",
    )
    enabled = models.BooleanField(
        default=True,
        help_text="When False this source is excluded from unified task queries",
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Adapter-specific config (api keys, slugs, etc.)",
    )
    display_order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Order in which sources are shown and queried (lower = first)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "created_at"]
        unique_together = [("user", "source_type")]
        verbose_name = "Task Source Config"
        verbose_name_plural = "Task Source Configs"

    def __str__(self) -> str:
        status = "on" if self.enabled else "off"
        return f"{self.user.username} | {self.source_type} [{status}]"


# ---------------------------------------------------------------------------
# Playlist
# ---------------------------------------------------------------------------

PLAYLIST_SOURCE_CHOICES = (
    ("youtube", "YouTube"),
    ("spotify", "Spotify"),
    ("other", "Other"),
)


class Playlist(models.Model):
    """A saved music playlist linked to a user.

    One playlist per user may be the default. Mode can optionally constrain
    the playlist to a specific focus mode (e.g., only play during deep_work).
    When mode is blank the playlist applies to any mode.
    """

    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="playlists",
    )
    name = models.CharField(max_length=200)
    url = models.URLField(max_length=500)
    source = models.CharField(
        max_length=16,
        choices=PLAYLIST_SOURCE_CHOICES,
        default="youtube",
    )
    mode = models.CharField(
        max_length=16,
        choices=MODE_CHOICES,
        blank=True,
        default="",
        help_text="Restrict playlist to a specific focus mode; blank = any mode",
    )
    is_default = models.BooleanField(
        default=False,
        help_text="If True this playlist is auto-selected when starting a session",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_default", "name"]
        verbose_name = "Playlist"
        verbose_name_plural = "Playlists"

    def __str__(self) -> str:
        default_mark = " [default]" if self.is_default else ""
        mode_mark = f" ({self.mode})" if self.mode else ""
        return f"{self.user.username} | {self.name}{mode_mark}{default_mark}"
