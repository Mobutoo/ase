"""
Django settings for Ase project.
Human-centric flow engine and task management.
"""
import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Core ---
DEBUG = os.environ.get("DEBUG", "1") == "1"
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-dev-key-change-in-production",
)
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
CSRF_TRUSTED_ORIGINS = os.environ.get(
    "CSRF_TRUSTED_ORIGINS", "http://localhost:8000"
).split(",")

# --- Security ---
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "0") == "1"
SECURE_HSTS_SECONDS = 2592000 if not DEBUG else 0
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG

# --- Apps ---
INSTALLED_APPS = [
    "daphne",  # Must be before django.contrib.staticfiles
    "app",
    "api",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "rest_framework",
    # Ase v3 new apps
    "circles",
    "calendars",
    "iam",
    "agents",
    # Third-party
    "mozilla_django_oidc",
    "channels",
]

# --- DRF ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%SZ",
}

SITE_ID = 1

# --- Allauth (username-based, no Google OAuth for now) ---
ACCOUNT_EMAIL_REQUIRED = False
ACCOUNT_EMAIL_VERIFICATION = False
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_AUTHENTICATION_METHOD = "username"
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_USER_MODEL_EMAIL_FIELD = None
ACCOUNT_LOGIN_ATTEMPTS_LIMIT = 10
ACCOUNT_LOGIN_ATTEMPTS_TIMEOUT = 1800
ACCOUNT_PASSWORD_MIN_LENGTH = 8
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https" if not DEBUG else "http"
ACCOUNT_LOGIN_ON_PASSWORD_RESET = False
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
ACCOUNT_SIGNUP_REDIRECT_URL = "/"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "ase_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "app/templates", "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "app.context_processors.global_settings",
            ],
        },
    },
]

AUTHENTICATION_BACKENDS = [
    "iam.backends.AseOIDCAuthenticationBackend",
    "django.contrib.auth.backends.ModelBackend",  # fallback
    "allauth.account.auth_backends.AuthenticationBackend",
]

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"

WSGI_APPLICATION = "ase_project.wsgi.application"

# --- Database (via DATABASE_URL or individual vars) ---
CONN_MAX_AGE = 0

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {"default": dj_database_url.parse(DATABASE_URL)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME", "ase"),
            "USER": os.environ.get("DB_USER", "ase"),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5432"),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        }
    }

# --- Cache (Redis) ---
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/4")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

# --- Password validation ---
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- i18n ---
LANGUAGE_CODE = "en-us"
USE_TZ = True
TIME_ZONE = os.environ.get("TZ", "UTC")
USE_I18N = True

# --- Static files ---
STATIC_ROOT = BASE_DIR / "staticfiles"
STATIC_URL = "/static/"
STATICFILES_DIRS = []

# --- Default PK ---
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- n8n / OpenClaw Webhook Integration ---
# Outbound: Ase → n8n
N8N_WEBHOOK_SESSION = os.environ.get("N8N_WEBHOOK_SESSION", "")
N8N_WEBHOOK_DAILY_PLAN = os.environ.get("N8N_WEBHOOK_DAILY_PLAN", "")
N8N_WEBHOOK_REFLECTION = os.environ.get("N8N_WEBHOOK_REFLECTION", "")
# Inbound: n8n → Ase (shared secret validated in X-Webhook-Secret header)
N8N_WEBHOOK_SECRET = os.environ.get("N8N_WEBHOOK_SECRET", "")

# --- OIDC Authentication ---
OIDC_RP_CLIENT_ID = os.environ.get('OIDC_CLIENT_ID', '')
OIDC_RP_CLIENT_SECRET = os.environ.get('OIDC_CLIENT_SECRET', '')
OIDC_OP_AUTHORIZATION_ENDPOINT = os.environ.get('OIDC_ISSUER_URL', '') + '/authorize'
OIDC_OP_TOKEN_ENDPOINT = os.environ.get('OIDC_ISSUER_URL', '') + '/oauth/token'
OIDC_OP_USER_ENDPOINT = os.environ.get('OIDC_ISSUER_URL', '') + '/oidc/v1/userinfo'
OIDC_OP_JWKS_ENDPOINT = os.environ.get('OIDC_ISSUER_URL', '') + '/.well-known/jwks.json'
OIDC_RP_SIGN_ALGO = 'RS256'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# --- IAM Backend ---
IAM_BACKEND = os.environ.get('IAM_BACKEND', 'lldap')
IAM_API_URL = os.environ.get('IAM_API_URL', 'http://lldap:17170')
IAM_API_KEY = os.environ.get('IAM_API_KEY', '')

# --- Federation ---
FEDERATION_ENABLED = os.environ.get('FEDERATION_ENABLED', 'false').lower() == 'true'
FEDERATION_GLOBAL_ISSUER = os.environ.get('FEDERATION_GLOBAL_ISSUER', '')
FEDERATION_GLOBAL_CLIENT_ID = os.environ.get('FEDERATION_GLOBAL_CLIENT_ID', '')
FEDERATION_GLOBAL_CLIENT_SECRET = os.environ.get('FEDERATION_GLOBAL_CLIENT_SECRET', '')

# --- Agent IA ---
AGENT_ENABLED = os.environ.get('AGENT_ENABLED', 'true').lower() == 'true'
AGENT_RATE_LIMIT = int(os.environ.get('AGENT_RATE_LIMIT', '20'))
AGENT_BOOKING_BUDGET_LIMIT = float(os.environ.get('AGENT_BOOKING_BUDGET_LIMIT', '50.00'))
AGENT_TIMEOUT_MINUTES = int(os.environ.get('AGENT_TIMEOUT_MINUTES', '30'))

# --- CalDAV ---
CALDAV_EXTERNAL_URL = os.environ.get('CALDAV_EXTERNAL_URL', '')

# --- Email (Brevo) ---
BREVO_API_KEY = os.environ.get('BREVO_API_KEY', '')
EMAIL_FROM = os.environ.get('EMAIL_FROM', 'noreply@flash.studio')

# --- Push notifications (VAPID) ---
VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', '')
VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '')

# --- Telegram ---
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_FAMILY_CHAT_ID = os.environ.get('TELEGRAM_FAMILY_CHAT_ID', '')

# --- Google Maps ---
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '')

# --- Django Channels ---
ASGI_APPLICATION = 'ase_project.asgi.application'
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [os.environ.get('REDIS_URL', 'redis://localhost:6379/0')],
        },
    },
}

# --- Celery ---
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/1')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')
