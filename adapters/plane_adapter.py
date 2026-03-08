"""PlaneAdapter — bridges Ase with a self-hosted Plane project management instance.

Config keys (stored in TaskSourceConfig.config JSONField):
    api_url        : base URL of the Plane API, e.g. "https://plane.example.com"
    api_key        : Plane API token
    workspace_slug : Plane workspace identifier slug
    project_id     : UUID of the Plane project to sync
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import requests
from requests.exceptions import ConnectionError, HTTPError, Timeout

from .base import TaskDTO, TaskSource

logger = logging.getLogger(__name__)

# Plane state-name → DTO status mapping (common defaults; override via raw_data)
_STATE_MAP = {
    "Backlog": "todo",
    "Todo": "todo",
    "In Progress": "in_progress",
    "Done": "done",
    "Cancelled": "done",
}

# DTO status → Plane state name used when updating
_REVERSE_STATE_MAP = {
    "todo": "Todo",
    "in_progress": "In Progress",
    "done": "Done",
}

# Plane priority labels → DTO priority
_PRIORITY_MAP = {
    "urgent": "urgent",
    "high": "high",
    "medium": "medium",
    "low": "low",
    "none": "none",
}


class PlaneAdapter(TaskSource):
    """TaskSource implementation backed by a self-hosted Plane API."""

    def __init__(self, config: dict) -> None:
        self._api_url = config["api_url"].rstrip("/")
        self._api_key = config["api_key"]
        self._workspace = config["workspace_slug"]
        self._project = config["project_id"]

    @property
    def source_name(self) -> str:
        return "plane"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self._api_key,
            "Content-Type": "application/json",
        }

    def _base(self) -> str:
        return (
            f"{self._api_url}/api/v1"
            f"/workspaces/{self._workspace}"
            f"/projects/{self._project}"
        )

    def _get(self, path: str) -> dict | list | None:
        url = f"{self._base()}{path}"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=10)
            resp.raise_for_status()
            return resp.json()
        except ConnectionError:
            logger.error("PlaneAdapter: cannot connect to %s", self._api_url)
            return None
        except Timeout:
            logger.error("PlaneAdapter: request timed out for %s", url)
            return None
        except HTTPError as exc:
            logger.error(
                "PlaneAdapter: HTTP %s for GET %s — %s",
                exc.response.status_code,
                url,
                exc.response.text[:200],
            )
            return None

    def _patch(self, path: str, payload: dict) -> dict | None:
        url = f"{self._base()}{path}"
        try:
            resp = requests.patch(url, json=payload, headers=self._headers(), timeout=10)
            resp.raise_for_status()
            return resp.json()
        except ConnectionError:
            logger.error("PlaneAdapter: cannot connect to %s", self._api_url)
            return None
        except Timeout:
            logger.error("PlaneAdapter: PATCH timed out for %s", url)
            return None
        except HTTPError as exc:
            logger.error(
                "PlaneAdapter: HTTP %s for PATCH %s — %s",
                exc.response.status_code,
                url,
                exc.response.text[:200],
            )
            return None

    def _post(self, path: str, payload: dict) -> dict | None:
        url = f"{self._base()}{path}"
        try:
            resp = requests.post(url, json=payload, headers=self._headers(), timeout=10)
            resp.raise_for_status()
            return resp.json()
        except ConnectionError:
            logger.error("PlaneAdapter: cannot connect to %s", self._api_url)
            return None
        except Timeout:
            logger.error("PlaneAdapter: POST timed out for %s", url)
            return None
        except HTTPError as exc:
            logger.error(
                "PlaneAdapter: HTTP %s for POST %s — %s",
                exc.response.status_code,
                url,
                exc.response.text[:200],
            )
            return None

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    def _parse_due_date(self, raw: str | None) -> datetime | None:
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _map_status(self, state_detail: dict | None) -> str:
        if not state_detail:
            return "todo"
        name = state_detail.get("name", "")
        group = state_detail.get("group", "")
        if group in ("started",):
            return "in_progress"
        if group in ("completed", "cancelled"):
            return "done"
        return _STATE_MAP.get(name, "todo")

    def _to_dto(self, issue: dict[str, Any]) -> TaskDTO:
        labels: list[str] = [
            lbl.get("name", "") for lbl in (issue.get("label_details") or [])
        ]
        due_date = self._parse_due_date(issue.get("due_date"))
        state_detail = issue.get("state_detail") or {}
        issue_status = self._map_status(state_detail)
        priority = _PRIORITY_MAP.get(issue.get("priority", "none"), "none")
        source_url = (
            f"{self._api_url}/{self._workspace}/projects"
            f"/{self._project}/issues/{issue.get('id', '')}"
        )
        return TaskDTO(
            id=str(issue.get("id", "")),
            title=issue.get("name", ""),
            description=issue.get("description_stripped", ""),
            status=issue_status,
            priority=priority,
            labels=labels,
            due_date=due_date,
            estimated_minutes=None,
            source="plane",
            source_url=source_url,
            raw_data=issue,
        )

    # ------------------------------------------------------------------
    # TaskSource interface
    # ------------------------------------------------------------------

    def get_tasks(self, filters: dict | None = None) -> list[TaskDTO]:
        data = self._get("/issues/")
        if data is None:
            return []
        issues = data if isinstance(data, list) else data.get("results", [])
        dtos = [self._to_dto(issue) for issue in issues]
        if filters:
            if "status" in filters:
                dtos = [t for t in dtos if t.status == filters["status"]]
            if "priority" in filters:
                dtos = [t for t in dtos if t.priority == filters["priority"]]
        return dtos

    def get_task(self, task_id: str) -> TaskDTO | None:
        data = self._get(f"/issues/{task_id}/")
        if data is None:
            return None
        return self._to_dto(data)

    def log_time(self, task_id: str, minutes: int, notes: str = "") -> bool:
        """Log work time on a Plane issue as an activity entry."""
        payload: dict[str, Any] = {
            "duration": minutes,
            "description": notes,
        }
        result = self._post(f"/issues/{task_id}/activities/", payload)
        return result is not None

    def update_status(self, task_id: str, new_status: str) -> bool:
        """Update the state of a Plane issue.

        Plane requires a state UUID, so we first fetch current states
        to resolve the target state name to an ID.
        """
        states_url = (
            f"{self._api_url}/api/v1"
            f"/workspaces/{self._workspace}"
            f"/projects/{self._project}/states/"
        )
        try:
            resp = requests.get(states_url, headers=self._headers(), timeout=10)
            resp.raise_for_status()
            states = resp.json()
        except (ConnectionError, Timeout, HTTPError) as exc:
            logger.error("PlaneAdapter: failed to fetch states — %s", exc)
            return False

        target_name = _REVERSE_STATE_MAP.get(new_status, "Todo")
        state_id: str | None = None
        state_list = states if isinstance(states, list) else states.get("results", [])
        for state in state_list:
            if state.get("name") == target_name:
                state_id = state.get("id")
                break

        if not state_id:
            logger.warning(
                "PlaneAdapter: no state found matching '%s' in project %s",
                target_name,
                self._project,
            )
            return False

        result = self._patch(f"/issues/{task_id}/", {"state": state_id})
        return result is not None
