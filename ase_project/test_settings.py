"""Deterministic tests on PostgreSQL; no Redis, brokers, or external providers."""
import os

os.environ.setdefault("DEBUG", "1")
from .settings import *  # noqa: F403, E402

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CELERY_TASK_ALWAYS_EAGER = True
AGENT_ENABLED = False
N8N_WEBHOOK_SESSION = ""
N8N_WEBHOOK_DAILY_PLAN = ""
N8N_WEBHOOK_REFLECTION = ""
SECURE_SSL_REDIRECT = False
