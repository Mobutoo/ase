from __future__ import annotations

from django.apps import AppConfig


class AgentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "agents"
    verbose_name = "Agents"

    def ready(self) -> None:
        # Import signal handlers if any are defined in the future
        pass
