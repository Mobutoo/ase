from __future__ import annotations

"""App-specific password authentication for CalDAV clients.

CalDAV clients (Thunderbird, Apple Calendar, DAVx5, ...) typically use
HTTP Basic Auth.  This module provides a lightweight authenticator that
validates revocable application passwords (and existing local passwords) so that no
session-cookie machinery is needed over WebDAV.

Usage::

    from calendars.caldav.auth import caldav_auth_required

    @caldav_auth_required
    def my_caldav_view(request, ...):
        ...

The decorator sets ``request.caldav_user`` to the authenticated
``django.contrib.auth`` User instance.
"""

import base64
import logging
from functools import wraps
from typing import Callable

from django.contrib.auth import authenticate, get_user_model
from django.http import HttpRequest, HttpResponse
from django.db.models import Q
from django.utils import timezone

User = get_user_model()
logger = logging.getLogger(__name__)

_REALM = "Ase CalDAV"


def _unauthorized(realm: str = _REALM) -> HttpResponse:
    response = HttpResponse(status=401)
    response["WWW-Authenticate"] = f'Basic realm="{realm}"'
    return response


def parse_basic_auth(request: HttpRequest) -> tuple[str, str] | None:
    """Extract (username, password) from the Authorization header.

    Returns ``None`` if the header is absent or malformed.
    """
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if len(auth_header) > 1024 or not auth_header.lower().startswith("basic "):
        return None
    try:
        decoded = base64.b64decode(auth_header[6:], validate=True).decode("utf-8")
        username, separator, password = decoded.partition(":")
        if not separator or not username or not password or len(username) > 150 or len(password) > 128:
            return None
        return username, password
    except Exception:
        return None


def authenticate_caldav(request: HttpRequest) -> User | None:
    """Attempt to authenticate the request using HTTP Basic Auth.

    Returns the User on success, ``None`` on failure.
    """
    credentials = parse_basic_auth(request)
    if credentials is None:
        return None
    username, password = credentials
    from iam.models import AppSpecificPassword

    user = User.objects.filter(username=username, is_active=True).first()
    if user is None:
        return None
    now = timezone.now()
    app_passwords = AppSpecificPassword.objects.filter(user=user).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    )
    for app_password in app_passwords:
        if app_password.check_password(password):
            app_password.last_used_at = now
            app_password.save(update_fields=["last_used_at"])
            return user
    user = authenticate(request, username=username, password=password)
    if user is not None and user.is_active:
        return user
    logger.warning("CalDAV auth failed for user '%s'", username)
    return None


def caldav_auth_required(view_func: Callable) -> Callable:
    """Decorator that enforces HTTP Basic Auth for CalDAV views.

    Sets ``request.caldav_user`` on success.
    """

    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        user = authenticate_caldav(request)
        if user is None:
            return _unauthorized()
        request.caldav_user = user
        return view_func(request, *args, **kwargs)

    return wrapper
