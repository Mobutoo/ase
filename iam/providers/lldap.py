from __future__ import annotations

import logging
import os
import secrets
import string

import requests

from .base import UserProvider
from .exceptions import (
    AuthenticationError,
    ConfigurationError,
    ProviderError,
    UserAlreadyExistsError,
    UserNotFoundError,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# GraphQL query / mutation templates
# ---------------------------------------------------------------------------

_GQL_LIST_USERS = """
query ListUsers {
  users {
    id
    email
    displayName
    groups { id displayName }
    creationDate
  }
}
"""

_GQL_GET_USER = """
query GetUser($id: String!) {
  user(id: $id) {
    id
    email
    displayName
    groups { id displayName }
    creationDate
  }
}
"""

_GQL_CREATE_USER = """
mutation CreateUser($user: CreateUserInput!) {
  createUser(user: $user) {
    id
    email
    displayName
    creationDate
  }
}
"""

_GQL_UPDATE_USER = """
mutation UpdateUser($user: UpdateUserInput!) {
  updateUser(user: $user) {
    ok
  }
}
"""

_GQL_DELETE_USER = """
mutation DeleteUser($userId: String!) {
  deleteUser(userId: $userId) {
    ok
  }
}
"""

_GQL_ADD_USER_TO_GROUP = """
mutation AddUserToGroup($userId: String!, $groupId: Int!) {
  addUserToGroup(userId: $userId, groupId: $groupId) {
    ok
  }
}
"""

_GQL_GET_GROUP_BY_NAME = """
query GetGroupByName($name: String!) {
  groups(filters: {displayName: {eq: $name}}) {
    id
    displayName
  }
}
"""

_GQL_RESET_PASSWORD = """
mutation ResetUserPasswordToRandom($userId: String!) {
  resetUserPassword(userId: $userId) {
    ok
    password
  }
}
"""


class LLDAPProvider(UserProvider):
    """UserProvider implementation backed by LLDAP.

    LLDAP exposes a GraphQL API at ``/api/graphql``.  Authentication uses a
    JWT obtained from ``/auth/simple/login`` with the service-account
    credentials configured below.

    Required environment variables
    --------------------------------
    ``LLDAP_API_URL``
        Base URL of the LLDAP instance, e.g. ``http://lldap:17170``.
    ``LLDAP_ADMIN_USER``
        LLDAP service account username (default: ``admin``).
    ``LLDAP_ADMIN_PASSWORD``
        LLDAP service account password.

    Optional
    --------
    ``LLDAP_ADMIN_GROUP``
        Name of the LLDAP group that maps to the ``admin`` role
        (default: ``lldap_admin``).
    ``LLDAP_MEMBER_GROUP``
        Name of the LLDAP group that maps to the ``member`` role
        (default: ``lldap_users``).
    """

    _GRAPHQL_PATH = "/api/graphql"
    _LOGIN_PATH = "/auth/simple/login"
    _DEFAULT_ADMIN_GROUP = "lldap_admin"
    _DEFAULT_MEMBER_GROUP = "lldap_users"

    def __init__(
        self,
        api_url: str | None = None,
        admin_user: str | None = None,
        admin_password: str | None = None,
    ) -> None:
        self._api_url = (api_url or os.environ.get("LLDAP_API_URL", "")).rstrip("/")
        self._admin_user = admin_user or os.environ.get("LLDAP_ADMIN_USER", "admin")
        self._admin_password = admin_password or os.environ.get("LLDAP_ADMIN_PASSWORD", "")
        self._admin_group = os.environ.get("LLDAP_ADMIN_GROUP", self._DEFAULT_ADMIN_GROUP)
        self._member_group = os.environ.get("LLDAP_MEMBER_GROUP", self._DEFAULT_MEMBER_GROUP)
        self._jwt: str | None = None

        if not self._api_url:
            raise ConfigurationError("LLDAP_API_URL is not configured.")
        if not self._admin_password:
            raise ConfigurationError("LLDAP_ADMIN_PASSWORD is not configured.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_token(self) -> str:
        """Obtain (or reuse) a short-lived JWT from LLDAP."""
        if self._jwt:
            return self._jwt

        url = f"{self._api_url}{self._LOGIN_PATH}"
        try:
            resp = requests.post(
                url,
                json={"username": self._admin_user, "password": self._admin_password},
                timeout=10,
            )
        except requests.RequestException as exc:
            raise ProviderError(f"LLDAP login request failed: {exc}") from exc

        if resp.status_code == 401:
            raise AuthenticationError("LLDAP rejected service-account credentials.")
        if not resp.ok:
            raise ProviderError(
                f"LLDAP login failed with HTTP {resp.status_code}: {resp.text}",
                status_code=resp.status_code,
            )

        data = resp.json()
        self._jwt = data.get("token") or data.get("access_token") or data.get("jwt")
        if not self._jwt:
            raise ProviderError("LLDAP login response contained no token.")
        return self._jwt

    def _graphql(self, query: str, variables: dict | None = None) -> dict:
        """Execute a GraphQL operation and return the ``data`` payload."""
        token = self._get_token()
        url = f"{self._api_url}{self._GRAPHQL_PATH}"
        payload: dict = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            resp = requests.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )
        except requests.RequestException as exc:
            raise ProviderError(f"LLDAP GraphQL request failed: {exc}") from exc

        if resp.status_code == 401:
            # Token may have expired — clear and retry once.
            self._jwt = None
            return self._graphql(query, variables)

        if not resp.ok:
            raise ProviderError(
                f"LLDAP GraphQL HTTP {resp.status_code}: {resp.text}",
                status_code=resp.status_code,
            )

        body = resp.json()
        if "errors" in body:
            errors = body["errors"]
            msg = "; ".join(e.get("message", str(e)) for e in errors)
            if any("already exists" in e.get("message", "").lower() for e in errors):
                raise UserAlreadyExistsError(msg)
            if any("not found" in e.get("message", "").lower() for e in errors):
                raise UserNotFoundError(msg)
            raise ProviderError(f"LLDAP GraphQL error: {msg}")

        return body.get("data", {})

    @staticmethod
    def _user_from_payload(payload: dict) -> dict:
        """Normalise an LLDAP user payload into the canonical dict shape."""
        groups = payload.get("groups") or []
        group_names = {g.get("displayName", "") for g in groups}
        role = "admin" if "lldap_admin" in group_names else "member"
        return {
            "id": payload.get("id", ""),
            "email": payload.get("email", ""),
            "display_name": payload.get("displayName", ""),
            "role": role,
            "groups": list(group_names),
            "created_at": payload.get("creationDate"),
        }

    @staticmethod
    def _random_password(length: int = 20) -> str:
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def _group_id_for_role(self, role: str) -> int | None:
        """Return the LLDAP group ID that corresponds to *role*."""
        group_name = self._admin_group if role == "admin" else self._member_group
        data = self._graphql(_GQL_GET_GROUP_BY_NAME, {"name": group_name})
        groups = data.get("groups") or []
        if not groups:
            logger.warning("LLDAP group %r not found — skipping group assignment.", group_name)
            return None
        return groups[0]["id"]

    # ------------------------------------------------------------------
    # UserProvider interface
    # ------------------------------------------------------------------

    def create_user(self, email: str, display_name: str, role: str) -> dict:
        username = email.split("@")[0].lower()
        data = self._graphql(
            _GQL_CREATE_USER,
            {
                "user": {
                    "id": username,
                    "email": email,
                    "displayName": display_name,
                    "firstName": display_name.split()[0] if display_name else "",
                    "lastName": " ".join(display_name.split()[1:]) if display_name else "",
                }
            },
        )
        user = data.get("createUser", {})
        user_id = user.get("id", username)

        # Assign to the appropriate group.
        group_id = self._group_id_for_role(role)
        if group_id is not None:
            self._graphql(_GQL_ADD_USER_TO_GROUP, {"userId": user_id, "groupId": group_id})

        logger.info("LLDAP: created user %r (role=%s)", email, role)
        return self._user_from_payload({**user, "groups": []})

    def delete_user(self, user_id: str) -> bool:
        try:
            data = self._graphql(_GQL_DELETE_USER, {"userId": user_id})
            return bool(data.get("deleteUser", {}).get("ok", False))
        except UserNotFoundError:
            return False

    def invite_member(self, email: str, display_name: str, role: str) -> dict:
        """Create the account and return a one-time password reset link."""
        user = self.create_user(email, display_name, role)
        user_id = user["id"]
        data = self._graphql(_GQL_RESET_PASSWORD, {"userId": user_id})
        temp_password = data.get("resetUserPassword", {}).get("password", "")
        invite_url = (
            f"{self._api_url}/reset-password?user={user_id}&token={temp_password}"
            if temp_password
            else ""
        )
        logger.info("LLDAP: invited member %r with temp URL", email)
        return {**user, "invite_url": invite_url}

    def update_user(self, user_id: str, **kwargs: object) -> dict:
        update_input: dict = {"id": user_id}
        if "display_name" in kwargs:
            update_input["displayName"] = kwargs["display_name"]
        if "email" in kwargs:
            update_input["email"] = kwargs["email"]

        self._graphql(_GQL_UPDATE_USER, {"user": update_input})

        # If role changes, reassign groups.
        if "role" in kwargs:
            group_id = self._group_id_for_role(str(kwargs["role"]))
            if group_id is not None:
                self._graphql(
                    _GQL_ADD_USER_TO_GROUP, {"userId": user_id, "groupId": group_id}
                )

        data = self._graphql(_GQL_GET_USER, {"id": user_id})
        return self._user_from_payload(data.get("user", {}))

    def list_users(self) -> list[dict]:
        data = self._graphql(_GQL_LIST_USERS)
        return [self._user_from_payload(u) for u in (data.get("users") or [])]
