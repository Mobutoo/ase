"""Adapter registry — maps source_type strings to adapter classes.

Usage:
    from adapters.registry import get_adapter

    adapter = get_adapter("plane", config={
        "api_url": "https://plane.example.com",
        "api_key": "secret",
        "workspace_slug": "my-workspace",
        "project_id": "uuid-here",
    })
    tasks = adapter.get_tasks()
"""
from __future__ import annotations

from typing import Type

from .base import TaskSource
from .local_adapter import LocalAdapter
from .plane_adapter import PlaneAdapter
from .github_adapter import GitHubAdapter
from .superproductivity_adapter import SuperProductivityAdapter


# Registry maps source_type string → adapter class
# New adapters are added here only; callers never import individual adapters.
_REGISTRY: dict[str, Type[TaskSource]] = {
    "local": LocalAdapter,
    "plane": PlaneAdapter,
    "github": GitHubAdapter,
    "superproductivity": SuperProductivityAdapter,
}


class UnknownSourceType(ValueError):
    """Raised when an unregistered source_type is requested."""


def get_adapter(source_type: str, config: dict) -> TaskSource:
    """Instantiate and return a TaskSource for the given source_type.

    Args:
        source_type: One of the registered keys ("local", "plane", "github", …).
        config:      Dict of config values passed directly to the adapter constructor.
                     For "local", pass {"user": <User instance>} instead of a JSON dict.

    Returns:
        A fully initialised TaskSource implementation.

    Raises:
        UnknownSourceType: If source_type is not registered.
        KeyError:          If required config keys are missing (adapter raises on its own).
    """
    adapter_class = _REGISTRY.get(source_type)
    if adapter_class is None:
        registered = sorted(_REGISTRY.keys())
        raise UnknownSourceType(
            f"Unknown source_type '{source_type}'. "
            f"Registered types: {registered}"
        )

    # LocalAdapter takes a user object, not a dict
    if source_type == "local":
        return LocalAdapter(user=config["user"])

    return adapter_class(config)


def registered_source_types() -> list[str]:
    """Return sorted list of all registered source_type identifiers."""
    return sorted(_REGISTRY.keys())
