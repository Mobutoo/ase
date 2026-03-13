"""Celery application configuration for Ase project."""
import os

from celery import Celery

# Set the default Django settings module for the Celery worker processes.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ase_project.settings")

app = Celery("ase_project")

# Pull Celery config from Django settings using the CELERY_ namespace prefix.
# e.g. CELERY_BROKER_URL → broker_url
app.config_from_object("django.conf:settings", namespace="CELERY")

# Automatically discover tasks defined in tasks.py inside every INSTALLED_APP.
app.autodiscover_tasks()

# ---------------------------------------------------------------------------
# Celery beat periodic tasks
# ---------------------------------------------------------------------------

app.conf.beat_schedule = {
    "refresh-ical-subscriptions": {
        "task": "calendars.tasks.refresh_ical_subscriptions",
        "schedule": 300.0,  # every 5 minutes
    },
    "sync-google-calendars": {
        "task": "calendars.tasks.sync_google_calendars",
        "schedule": 300.0,  # every 5 minutes
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Introspection task — prints request info; useful for smoke-testing the worker."""
    print(f"Request: {self.request!r}")
