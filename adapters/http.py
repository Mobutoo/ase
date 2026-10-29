"""Outbound access is limited to exact destinations approved by the operator.

Allow only origins under operator control, backed by trusted DNS/egress policy.
Self-hosted HTTP services are supported when explicitly approved. Redirects are
never followed: API keys must never be forwarded to another destination.
"""
from pathlib import Path
from urllib.parse import urlsplit

import requests
from django.conf import settings


def _origin(url: str) -> str:
    if not isinstance(url, str) or any(ord(char) <= 32 for char in url) or "\\" in url:
        raise ValueError("Adapter URL must be an absolute HTTP(S) URL without whitespace.")
    parsed = urlsplit(url)
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or parsed.fragment or "%" in parsed.netloc):
        raise ValueError("Adapter URL must use HTTP(S), without userinfo or fragments.")
    # Accessing port validates numeric syntax and the permitted range.
    parsed.port
    return f"{parsed.scheme}://{parsed.netloc.lower()}"


def validate_url(url: str, *, fixed_origin: str | None = None) -> str:
    origin = _origin(url)
    allowed = [fixed_origin] if fixed_origin else getattr(settings, "ADAPTER_ALLOWED_ORIGINS", [])
    if origin not in allowed:
        raise ValueError("Adapter origin is not approved in ADAPTER_ALLOWED_ORIGINS.")
    return url


def validate_file(path: str) -> Path:
    """Resolve symlinks before comparing exact operator-approved export paths."""
    requested = Path(path)
    if not requested.is_absolute():
        raise ValueError("Adapter export path must be absolute.")
    resolved = requested.resolve()
    allowed = {Path(item).resolve() for item in getattr(settings, "ADAPTER_ALLOWED_FILES", [])}
    if resolved not in allowed:
        raise ValueError("Adapter export is not approved in ADAPTER_ALLOWED_FILES.")
    return resolved


class RestrictedHTTP:
    def __init__(self, fixed_origin=None):
        self.fixed_origin = fixed_origin

    def request(self, method, url, **kwargs):
        validate_url(url, fixed_origin=self.fixed_origin)
        kwargs["allow_redirects"] = False
        kwargs.setdefault("timeout", 10)
        response = requests.request(method, url, **kwargs)
        if 300 <= response.status_code < 400:
            response.close()
            raise requests.HTTPError("Adapter redirects are disabled.", response=response)
        return response

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)

    def put(self, url, **kwargs):
        return self.request("PUT", url, **kwargs)

    def patch(self, url, **kwargs):
        return self.request("PATCH", url, **kwargs)

    def delete(self, url, **kwargs):
        return self.request("DELETE", url, **kwargs)


adapter_http = RestrictedHTTP()
github_http = RestrictedHTTP("https://api.github.com")
