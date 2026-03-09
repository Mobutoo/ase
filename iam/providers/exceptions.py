from __future__ import annotations


class ProviderError(Exception):
    """Base exception for all IAM provider errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class UserAlreadyExistsError(ProviderError):
    """Raised when attempting to create a user that already exists."""


class UserNotFoundError(ProviderError):
    """Raised when a requested user does not exist in the directory."""


class AuthenticationError(ProviderError):
    """Raised when the provider rejects the service account credentials."""


class ConfigurationError(ProviderError):
    """Raised when the provider is misconfigured (missing env vars, etc.)."""
