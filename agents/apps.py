from __future__ import annotations

from django.apps import AppConfig


class AgentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "agents"
    verbose_name = "Agents"

    def ready(self) -> None:
        import agents.signals  # noqa: F401 — register signal handlers
