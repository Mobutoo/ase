"""OIDC Discovery helper.

Fetches the OpenID Connect discovery document from the issuer's
``.well-known/openid-configuration`` endpoint and caches the result
in-process for 1 hour to avoid hitting the IdP on every Django startup.

Usage in ``settings.py``::

    from iam.discovery import get_oidc_endpoints
    endpoints = get_oidc_endpoints(os.environ.get("OIDC_ISSUER_URL", ""))
    OIDC_OP_AUTHORIZATION_ENDPOINT = endpoints["authorization_endpoint"]
    ...

When ``OIDC_ISSUER_URL`` is empty (OIDC disabled), all endpoints are
returned as empty strings so the app can boot without an IdP.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

_cache: dict[str, Any] = {}
_cache_ts: float = 0.0
_CACHE_TTL_SECONDS: int = 3600  # 1 hour


def _fetch_discovery(issuer_url: str) -> dict[str, str]:
    """Fetch the OIDC discovery document from the issuer.

    Args:
        issuer_url: The OIDC issuer base URL (e.g. ``https://auth.example.com``).

    Returns:
        The parsed JSON discovery document.

    Raises:
        RuntimeError: If the discovery document cannot be fetched.
    """
    import requests

    well_known = f"{issuer_url.rstrip('/')}/.well-known/openid-configuration"
    try:
        resp = requests.get(well_known, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        raise RuntimeError(
            f"Failed to fetch OIDC discovery from {well_known}: {exc}"
        ) from exc


def get_oidc_endpoints(issuer_url: str | None = None) -> dict[str, str]:
    """Return OIDC endpoint URLs derived from the discovery document.

    If *issuer_url* is falsy, returns a dict of empty strings (OIDC disabled).
    Results are cached in-process for ``_CACHE_TTL_SECONDS``.

    The returned dict contains:

    - ``authorization_endpoint``
    - ``token_endpoint``
    - ``userinfo_endpoint``
    - ``jwks_uri``
    - ``end_session_endpoint`` (may be empty if the IdP does not support it)
    - ``issuer``

    Args:
        issuer_url: OIDC issuer URL.  Defaults to ``OIDC_ISSUER_URL`` env var.

    Returns:
        Dict mapping standard OIDC field names to their URLs.
    """
    global _cache, _cache_ts

    if issuer_url is None:
        issuer_url = os.environ.get("OIDC_ISSUER_URL", "")

    empty = {
        "authorization_endpoint": "",
        "token_endpoint": "",
        "userinfo_endpoint": "",
        "jwks_uri": "",
        "end_session_endpoint": "",
        "issuer": "",
    }

    if not issuer_url:
        return empty

    now = time.monotonic()
    if _cache and (now - _cache_ts) < _CACHE_TTL_SECONDS:
        return _cache

    try:
        doc = _fetch_discovery(issuer_url)
    except RuntimeError:
        logger.warning(
            "OIDC discovery failed for %r — falling back to Zitadel defaults.",
            issuer_url,
        )
        # Zitadel-style fallback paths when discovery is unreachable.
        base = issuer_url.rstrip("/")
        doc = {
            "authorization_endpoint": f"{base}/oauth/v2/authorize",
            "token_endpoint": f"{base}/oauth/v2/token",
            "userinfo_endpoint": f"{base}/oidc/v1/userinfo",
            "jwks_uri": f"{base}/oauth/v2/keys",
            "end_session_endpoint": f"{base}/oidc/v1/end_session",
            "issuer": base,
        }

    result = {
        "authorization_endpoint": doc.get("authorization_endpoint", ""),
        "token_endpoint": doc.get("token_endpoint", ""),
        "userinfo_endpoint": doc.get("userinfo_endpoint", ""),
        "jwks_uri": doc.get("jwks_uri", ""),
        "end_session_endpoint": doc.get("end_session_endpoint", ""),
        "issuer": doc.get("issuer", issuer_url),
    }

    _cache = result
    _cache_ts = now
    logger.info("OIDC discovery loaded for issuer %r", issuer_url)
    return result
