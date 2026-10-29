"""Bounded downloads from explicitly trusted calendar feed providers."""
from urllib.parse import urlsplit

import httpx
from django.conf import settings

MAX_FEED_BYTES = 5 * 1024 * 1024


def fetch_subscription(url: str, etag: str = "") -> httpx.Response:
    """Never follow redirects or let a user select arbitrary network origins.

    Operators must only allow providers they control/trust, with public DNS.
    Keep network-level egress filtering as defense in depth.
    """
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.fragment):
        raise ValueError("Calendar feeds require an approved HTTPS origin.")
    origin = f"https://{parsed.netloc.lower()}"
    if origin not in settings.ICAL_ALLOWED_ORIGINS:
        raise ValueError("Calendar feed origin is not approved by the administrator.")

    headers = {"Accept": "text/calendar"}
    if etag:
        headers["If-None-Match"] = etag
    with httpx.Client(timeout=30.0, follow_redirects=False) as client:
        with client.stream("GET", url, headers=headers) as response:
            if response.status_code == 304:
                return httpx.Response(304, headers=response.headers)
            # raise_for_status rejects redirects as well as HTTP errors.
            response.raise_for_status()
            data = bytearray()
            for chunk in response.iter_bytes():
                if len(data) + len(chunk) > MAX_FEED_BYTES:
                    raise ValueError("Calendar feed exceeds the 5 MiB size limit.")
                data.extend(chunk)
            return httpx.Response(response.status_code, headers=response.headers,
                                  content=bytes(data), request=response.request)
