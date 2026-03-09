from __future__ import annotations

import logging
import os

from .base import UserProvider
from .exceptions import ConfigurationError

logger = logging.getLogger(__name__)

# Lazy import to avoid loading heavy dependencies when they are not needed.
_PROVIDERS: dict[str, type[UserProvider]] = {}


def _register_providers() -> None:
    """Populate the provider registry lazily on first use."""
    global _PROVIDERS
    if _PROVIDERS:
        return

    from .lldap import LLDAPProvider
    from .zitadel import ZitadelProvider

    _PROVIDERS = {
        "lldap": LLDAPProvider,
        "zitadel": ZitadelProvider,
    }


def get_provider(backend: str | None = None) -> UserProvider:
    """Return a configured :class:`~iam.providers.base.UserProvider` instance.

    The backend is selected in priority order:

    1. The *backend* argument (if provided).
    2. The ``IAM_BACKEND`` environment variable.
    3. Falls back to ``"lldap"`` if neither is set.

    Args:
        backend: Override the backend type (``"lldap"`` or ``"zitadel"``).

    Returns:
        An initialised UserProvider ready to use.

    Raises:
        :exc:`~iam.providers.exceptions.ConfigurationError`: If the requested
            backend is not recognised or is missing required env vars.
    """
    _register_providers()

    selected = (backend or os.environ.get("IAM_BACKEND", "lldap")).lower().strip()

    if selected not in _PROVIDERS:
        raise ConfigurationError(
            f"Unknown IAM_BACKEND: {selected!r}. "
            f"Valid choices are: {', '.join(sorted(_PROVIDERS))}."
        )

    provider_cls = _PROVIDERS[selected]
    logger.debug("IAM registry: instantiating %s provider.", selected)
    return provider_cls()
