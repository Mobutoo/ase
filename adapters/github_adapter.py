"""GitHubAdapter — bridges Ase with GitHub Issues API.

Config keys (stored in TaskSourceConfig.config JSONField):
    token : GitHub personal access token (or fine-grained PAT)
    owner : repository owner login (user or org)
    repo  : repository name
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import requests
from requests.exceptions import ConnectionError, HTTPError, Timeout

from .base import TaskDTO, TaskSource

logger = logging.getLogger(__name__)

_GITHUB_API = "https://api.github.com"

# GitHub issue state → DTO status
_STATE_MAP = {
    "open": "in_progress",
    "closed": "done",
}

# DTO status → GitHub issue state
_REVERSE_STATE_MAP = {
    "todo": "open",
    "in_progress": "open",
    "done": "closed",
}

# GitHub label names that represent priority (lowercased match)
_PRIORITY_LABELS = {"urgent", "high", "medium", "low"}


def _parse_iso(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _extract_priority(labels: list[str]) -> str:
    for label in labels:
        normalized = label.lower()
        if normalized in _PRIORITY_LABELS:
            return normalized
    return "none"


class GitHubAdapter(TaskSource):
    """TaskSource implementation backed by GitHub Issues on a single repo."""

    def __init__(self, config: dict) -> None:
        self._token = config["token"]
        self._owner = config["owner"]
        self._repo = config["repo"]

    @property
    def source_name(self) -> str:
        return "github"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _issues_url(self) -> str:
        return f"{_GITHUB_API}/repos/{self._owner}/{self._repo}/issues"

    def _issue_url(self, issue_number: str) -> str:
        return f"{self._issues_url()}/{issue_number}"

    def _comments_url(self, issue_number: str) -> str:
        return f"{self._issues_url()}/{issue_number}/comments"

    def _get(self, url: str, params: dict | None = None) -> Any:
        try:
            resp = requests.get(
                url, headers=self._headers(), params=params or {}, timeout=10
            )
            resp.raise_for_status()
            return resp.json()
        except ConnectionError:
            logger.error("GitHubAdapter: cannot connect to %s", _GITHUB_API)
            return None
        except Timeout:
            logger.error("GitHubAdapter: request timed out for %s", url)
            return None
        except HTTPError as exc:
            logger.error(
                "GitHubAdapter: HTTP %s for GET %s — %s",
                exc.response.status_code,
                url,
                exc.response.text[:200],
            )
            return None

    def _post(self, url: str, payload: dict) -> dict | None:
        try:
            resp = requests.post(
                url, json=payload, headers=self._headers(), timeout=10
            )
            resp.raise_for_status()
            return resp.json()
        except ConnectionError:
            logger.error("GitHubAdapter: cannot connect to %s", _GITHUB_API)
            return None
        except Timeout:
            logger.error("GitHubAdapter: POST timed out for %s", url)
            return None
        except HTTPError as exc:
            logger.error(
                "GitHubAdapter: HTTP %s for POST %s — %s",
                exc.response.status_code,
                url,
                exc.response.text[:200],
            )
            return None

    def _patch(self, url: str, payload: dict) -> dict | None:
        try:
            resp = requests.patch(
                url, json=payload, headers=self._headers(), timeout=10
            )
            resp.raise_for_status()
            return resp.json()
        except ConnectionError:
            logger.error("GitHubAdapter: cannot connect to %s", _GITHUB_API)
            return None
        except Timeout:
            logger.error("GitHubAdapter: PATCH timed out for %s", url)
            return None
        except HTTPError as exc:
            logger.error(
                "GitHubAdapter: HTTP %s for PATCH %s — %s",
                exc.response.status_code,
                url,
                exc.response.text[:200],
            )
            return None

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    def _to_dto(self, issue: dict[str, Any]) -> TaskDTO:
        label_names: list[str] = [
            lbl.get("name", "") for lbl in (issue.get("labels") or [])
        ]
        priority = _extract_priority(label_names)
        # Filter priority labels out of the regular label list
        display_labels = [
            l for l in label_names if l.lower() not in _PRIORITY_LABELS
        ]
        state = issue.get("state", "open")
        issue_status = _STATE_MAP.get(state, "todo")
        due_date = _parse_iso(issue.get("due_on") or issue.get("closed_at"))

        # Milestone due date is more reliable when present
        milestone = issue.get("milestone") or {}
        if milestone.get("due_on"):
            due_date = _parse_iso(milestone["due_on"])

        return TaskDTO(
            id=str(issue.get("number", "")),
            title=issue.get("title", ""),
            description=(issue.get("body") or ""),
            status=issue_status,
            priority=priority,
            labels=display_labels,
            due_date=due_date,
            estimated_minutes=None,
            source="github",
            source_url=issue.get("html_url", ""),
            raw_data=issue,
        )

    # ------------------------------------------------------------------
    # TaskSource interface
    # ------------------------------------------------------------------

    def get_tasks(self, filters: dict | None = None) -> list[TaskDTO]:
        """List GitHub Issues (open by default; use filters={'status':'done'} for closed)."""
        state_param = "open"
        if filters and filters.get("status") == "done":
            state_param = "closed"
        elif filters and filters.get("status") in ("todo", "in_progress"):
            state_param = "open"

        params: dict[str, Any] = {"state": state_param, "per_page": 100}
        if filters and "labels" in filters:
            params["labels"] = filters["labels"]

        data = self._get(self._issues_url(), params=params)
        if data is None:
            return []

        # GitHub returns PR objects mixed with issues when using /issues endpoint
        issues_only = [i for i in data if "pull_request" not in i]
        dtos = [self._to_dto(i) for i in issues_only]

        if filters and "priority" in filters:
            dtos = [t for t in dtos if t.priority == filters["priority"]]

        return dtos

    def get_task(self, task_id: str) -> TaskDTO | None:
        """Retrieve a single issue by its number."""
        data = self._get(self._issue_url(task_id))
        if data is None:
            return None
        return self._to_dto(data)

    def log_time(self, task_id: str, minutes: int, notes: str = "") -> bool:
        """Log time by posting a comment on the GitHub issue.

        Format: "Logged Xh Ym — <notes>" so time is human-readable.
        """
        hours, remaining = divmod(minutes, 60)
        time_str = f"{hours}h {remaining}m" if hours else f"{remaining}m"
        body_parts = [f"Logged {time_str}"]
        if notes:
            body_parts.append(notes)
        comment_body = " — ".join(body_parts)

        result = self._post(
            self._comments_url(task_id), {"body": comment_body}
        )
        return result is not None

    def update_status(self, task_id: str, new_status: str) -> bool:
        """Update GitHub issue state: open for active, closed for done."""
        gh_state = _REVERSE_STATE_MAP.get(new_status, "open")
        result = self._patch(self._issue_url(task_id), {"state": gh_state})
        return result is not None
