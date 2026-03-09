from __future__ import annotations

from django.apps import AppConfig


class CirclesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "circles"

    def ready(self) -> None:
        pass  # Register signals here if needed in future
