from __future__ import annotations

from abc import ABC, abstractmethod


class UserProvider(ABC):
    """Abstract interface for IAM backend user provisioning.

    Concrete implementations (:class:`LLDAPProvider`, :class:`ZitadelProvider`)
    fulfil these operations against the upstream directory.  All methods are
    synchronous and raise :exc:`iam.providers.exceptions.ProviderError` on
    failure — callers should catch that exception.

    Return value convention
    -----------------------
    Methods that return a user return a plain ``dict`` with at minimum:

    .. code-block:: python

        {
            "id": "<provider-native-user-id>",
            "email": "user@example.com",
            "display_name": "Alice",
            "role": "member",          # or "admin"
        }

    Extra keys may be present depending on the backend.
    """

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @abstractmethod
    def create_user(self, email: str, display_name: str, role: str) -> dict:
        """Provision a new user in the upstream directory.

        Args:
            email: Primary email address — used as the login identifier.
            display_name: Human-readable name shown in the UI.
            role: Role string (e.g. ``"admin"``, ``"member"``).

        Returns:
            Dict describing the created user (see class docstring).

        Raises:
            iam.providers.exceptions.UserAlreadyExistsError: If the email is
                already registered.
            iam.providers.exceptions.ProviderError: On any other failure.
        """

    @abstractmethod
    def delete_user(self, user_id: str) -> bool:
        """Remove a user from the upstream directory.

        Args:
            user_id: Provider-native user identifier.

        Returns:
            ``True`` if the user was deleted, ``False`` if not found.

        Raises:
            iam.providers.exceptions.ProviderError: On API failure.
        """

    @abstractmethod
    def invite_member(self, email: str, display_name: str, role: str) -> dict:
        """Send an invitation to a new member.

        For LLDAP this creates the account immediately and returns a
        password-reset link.  For Zitadel this triggers the built-in
        invitation email flow.

        Args:
            email: Recipient email address.
            display_name: Name to pre-fill in the IdP.
            role: Role to assign on acceptance.

        Returns:
            Dict describing the invited user plus any invitation metadata
            (e.g. ``{"invite_url": "...", ...}``).

        Raises:
            iam.providers.exceptions.ProviderError: On API failure.
        """

    @abstractmethod
    def update_user(self, user_id: str, **kwargs: object) -> dict:
        """Update attributes of an existing user.

        Supported keyword arguments are backend-specific but typically include
        ``display_name``, ``email``, ``role``.

        Args:
            user_id: Provider-native user identifier.
            **kwargs: Fields to update.

        Returns:
            Dict describing the updated user state.

        Raises:
            iam.providers.exceptions.UserNotFoundError: If the user does not
                exist.
            iam.providers.exceptions.ProviderError: On any other API failure.
        """

    @abstractmethod
    def list_users(self) -> list[dict]:
        """Return all users known to the upstream directory.

        Returns:
            List of user dicts (see class docstring for the expected shape).

        Raises:
            iam.providers.exceptions.ProviderError: On API failure.
        """
