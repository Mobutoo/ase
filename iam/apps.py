from __future__ import annotations

from django.apps import AppConfig


class IamConfig(AppConfig):
    """AppConfig for the IAM (Identity & Access Management) Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "iam"
    verbose_name = "Identity & Access Management"

    def ready(self) -> None:
        # Import signal handlers when the app is ready.
        import iam.signals  # noqa: F401
