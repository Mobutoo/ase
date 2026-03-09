from __future__ import annotations

import logging
import os

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
# Zitadel Management API paths
# ---------------------------------------------------------------------------
# Docs: https://zitadel.com/docs/apis/resources/mgmt/management-service
_USERS_PATH = "/management/v1/users"
_HUMAN_PATH = "/management/v1/users/human/_import"
_INVITE_PATH = "/management/v1/users/{user_id}/links"
_USER_PATH = "/management/v1/users/{user_id}"
_LIST_USERS_PATH = "/management/v1/users/_search"
_ORG_MEMBER_PATH = "/management/v1/orgs/me/members"


class ZitadelProvider(UserProvider):
    """UserProvider implementation backed by the Zitadel Management API.

    Authentication uses a service-account personal-access-token (PAT) which
    is sent as a Bearer token on every request.

    Required environment variables
    --------------------------------
    ``ZITADEL_API_URL``
        Zitadel instance base URL, e.g. ``https://auth.example.com``.
    ``ZITADEL_SERVICE_TOKEN``
        Personal Access Token for a service account with ``IAM_OWNER`` or
        ``ORG_USER_MANAGER`` privileges.
    ``ZITADEL_ORG_ID``
        Target organisation ID.  Required for org-scoped management calls.

    Optional
    --------
    ``ZITADEL_DEFAULT_PASSWORD``
        Initial password for newly created users.  Defaults to a secure
        random string; Zitadel will force a reset on first login regardless.
    """

    def __init__(
        self,
        api_url: str | None = None,
        service_token: str | None = None,
        org_id: str | None = None,
    ) -> None:
        self._api_url = (api_url or os.environ.get("ZITADEL_API_URL", "")).rstrip("/")
        self._token = service_token or os.environ.get("ZITADEL_SERVICE_TOKEN", "")
        self._org_id = org_id or os.environ.get("ZITADEL_ORG_ID", "")

        if not self._api_url:
            raise ConfigurationError("ZITADEL_API_URL is not configured.")
        if not self._token:
            raise ConfigurationError("ZITADEL_SERVICE_TOKEN is not configured.")
        if not self._org_id:
            raise ConfigurationError("ZITADEL_ORG_ID is not configured.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "x-zitadel-orgid": self._org_id,
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict:
        url = f"{self._api_url}{path}"
        try:
            resp = requests.request(
                method,
                url,
                headers=self._headers(),
                json=json,
                params=params,
                timeout=15,
            )
        except requests.RequestException as exc:
            raise ProviderError(f"Zitadel API request failed: {exc}") from exc

        if resp.status_code == 401:
            raise AuthenticationError("Zitadel rejected the service-account token.")
        if resp.status_code == 404:
            raise UserNotFoundError(f"Zitadel: resource not found at {path}")
        if resp.status_code == 409:
            raise UserAlreadyExistsError(f"Zitadel: resource already exists — {resp.text}")
        if not resp.ok:
            raise ProviderError(
                f"Zitadel API HTTP {resp.status_code}: {resp.text}",
                status_code=resp.status_code,
            )

        return resp.json() if resp.content else {}

    @staticmethod
    def _user_from_payload(payload: dict) -> dict:
        """Normalise a Zitadel user object into the canonical dict shape."""
        human = payload.get("human", {})
        profile = human.get("profile", {})
        email_obj = human.get("email", {})
        state = payload.get("state", "USER_STATE_ACTIVE")
        return {
            "id": payload.get("userId") or payload.get("id", ""),
            "email": email_obj.get("email", ""),
            "display_name": profile.get("displayName", ""),
            "first_name": profile.get("firstName", ""),
            "last_name": profile.get("lastName", ""),
            "role": payload.get("_ase_role", "member"),
            "state": state,
        }

    # ------------------------------------------------------------------
    # UserProvider interface
    # ------------------------------------------------------------------

    def create_user(self, email: str, display_name: str, role: str) -> dict:
        parts = display_name.strip().split(" ", 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""

        body = {
            "userName": email,
            "profile": {
                "firstName": first_name,
                "lastName": last_name,
                "displayName": display_name,
                "preferredLanguage": "en",
            },
            "email": {
                "email": email,
                "isEmailVerified": False,
            },
            "password": {
                "password": os.environ.get("ZITADEL_DEFAULT_PASSWORD", _random_password()),
                "changeRequired": True,
            },
        }
        data = self._request("POST", _HUMAN_PATH, json=body)
        user_id = data.get("userId", "")

        # Add to org with the requested role.
        self._set_org_role(user_id, role)

        logger.info("Zitadel: created user %r (role=%s, id=%s)", email, role, user_id)
        return {
            "id": user_id,
            "email": email,
            "display_name": display_name,
            "role": role,
        }

    def delete_user(self, user_id: str) -> bool:
        try:
            self._request("DELETE", _USER_PATH.format(user_id=user_id))
            logger.info("Zitadel: deleted user %s", user_id)
            return True
        except UserNotFoundError:
            return False

    def invite_member(self, email: str, display_name: str, role: str) -> dict:
        """Create the user and trigger Zitadel's invitation email flow."""
        user = self.create_user(email, display_name, role)
        user_id = user["id"]

        # Trigger Zitadel invitation link generation.
        link_data = self._request(
            "POST",
            _INVITE_PATH.format(user_id=user_id),
            json={},
        )
        invite_url = link_data.get("authLink", "")
        logger.info("Zitadel: invited member %r", email)
        return {**user, "invite_url": invite_url}

    def update_user(self, user_id: str, **kwargs: object) -> dict:
        profile_patch: dict = {}
        if "display_name" in kwargs:
            profile_patch["displayName"] = kwargs["display_name"]
        if "first_name" in kwargs:
            profile_patch["firstName"] = kwargs["first_name"]
        if "last_name" in kwargs:
            profile_patch["lastName"] = kwargs["last_name"]

        if profile_patch:
            self._request(
                "PUT",
                f"{_USER_PATH.format(user_id=user_id)}/profile",
                json=profile_patch,
            )

        if "email" in kwargs:
            self._request(
                "PUT",
                f"{_USER_PATH.format(user_id=user_id)}/email",
                json={"email": kwargs["email"], "isEmailVerified": False},
            )

        if "role" in kwargs:
            self._set_org_role(user_id, str(kwargs["role"]))

        data = self._request("GET", _USER_PATH.format(user_id=user_id))
        user = self._user_from_payload(data.get("user", data))
        user["role"] = str(kwargs.get("role", user.get("role", "member")))
        return user

    def list_users(self) -> list[dict]:
        body: dict = {"query": {"offset": "0", "limit": 1000, "asc": True}}
        data = self._request("POST", _LIST_USERS_PATH, json=body)
        result = data.get("result") or []
        return [self._user_from_payload(u) for u in result]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _set_org_role(self, user_id: str, role: str) -> None:
        """Add or update the user's organisation role in Zitadel."""
        zitadel_roles = ["ORG_OWNER"] if role == "admin" else ["ORG_USER"]
        try:
            self._request(
                "POST",
                _ORG_MEMBER_PATH,
                json={"userId": user_id, "roles": zitadel_roles},
            )
        except UserAlreadyExistsError:
            # Member already exists — update roles instead.
            self._request(
                "PUT",
                f"{_ORG_MEMBER_PATH}/{user_id}",
                json={"roles": zitadel_roles},
            )


def _random_password(length: int = 24) -> str:
    import secrets
    import string

    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))
