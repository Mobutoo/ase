from __future__ import annotations

from django.apps import AppConfig


class CalendarsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "calendars"
    verbose_name = "Calendar"

    def ready(self) -> None:
        import calendars.signals  # noqa: F401 — register signal handlers
