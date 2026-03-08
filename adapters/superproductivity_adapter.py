"""SuperProductivityAdapter — bridges Ase with Super Productivity via JSON file sync.

Super Productivity does NOT expose a REST API.  Integration works by reading
the app's JSON data file, which can be a local path or a WebDAV URL.

Config keys (stored in TaskSourceConfig.config JSONField):
    sync_url       : WebDAV URL to SP data file, e.g. "https://webdav.example.com/sp/data.json"
    sync_file_path : absolute path to a local SP export, e.g. "/data/sp-export.json"

At least one of sync_url / sync_file_path must be present.
If both are provided, sync_url takes precedence.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from requests.exceptions import ConnectionError, HTTPError, Timeout

from .base import TaskDTO, TaskSource

logger = logging.getLogger(__name__)


class SuperProductivityAdapter(TaskSource):
    """Read-only TaskSource backed by a Super Productivity JSON data file."""

    def __init__(self, config: dict) -> None:
        self._sync_url: str = config.get("sync_url", "")
        self._sync_file_path: str = config.get("sync_file_path", "")

        if not self._sync_url and not self._sync_file_path:
            raise KeyError(
                "SuperProductivityAdapter requires at least one of "
                "'sync_url' or 'sync_file_path' in config"
            )

    @property
    def source_name(self) -> str:
        return "superproductivity"

    # ------------------------------------------------------------------
    # Internal helpers — data loading
    # ------------------------------------------------------------------

    def _load_json(self) -> dict[str, Any] | None:
        """Load and parse the SP AppBaseData JSON from URL or file."""
        raw_text = self._fetch_raw()
        if raw_text is None:
            return None
        return self._parse_raw(raw_text)

    def _fetch_raw(self) -> str | None:
        """Fetch the raw text content from URL or local file."""
        if self._sync_url:
            return self._fetch_from_url()
        return self._read_from_file()

    def _fetch_from_url(self) -> str | None:
        try:
            resp = requests.get(self._sync_url, timeout=15)
            resp.raise_for_status()
            return resp.text
        except ConnectionError:
            logger.error(
                "SuperProductivityAdapter: cannot connect to %s",
                self._sync_url,
            )
            return None
        except Timeout:
            logger.error(
                "SuperProductivityAdapter: request timed out for %s",
                self._sync_url,
            )
            return None
        except HTTPError as exc:
            logger.error(
                "SuperProductivityAdapter: HTTP %s for GET %s — %s",
                exc.response.status_code,
                self._sync_url,
                exc.response.text[:200],
            )
            return None

    def _read_from_file(self) -> str | None:
        path = Path(self._sync_file_path)
        if not path.is_file():
            logger.error(
                "SuperProductivityAdapter: file not found at %s",
                self._sync_file_path,
            )
            return None
        try:
            return path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.error(
                "SuperProductivityAdapter: failed to read %s — %s",
                self._sync_file_path,
                exc,
            )
            return None

    def _parse_raw(self, raw_text: str) -> dict[str, Any] | None:
        """Parse raw text to JSON dict.

        SP may prefix data with ``SP_CPR_`` (lz-string compressed) or
        ``SP_ENC_`` (encrypted).  We handle plain JSON only for now;
        compressed/encrypted payloads log a warning and return None.
        """
        if raw_text.startswith("SP_CPR_"):
            logger.warning(
                "SuperProductivityAdapter: compressed data (SP_CPR_) is not "
                "supported yet — export an uncompressed backup from SP"
            )
            return None

        if raw_text.startswith("SP_ENC_"):
            logger.warning(
                "SuperProductivityAdapter: encrypted data (SP_ENC_) is not "
                "supported — export an unencrypted backup from SP"
            )
            return None

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as exc:
            logger.error(
                "SuperProductivityAdapter: invalid JSON — %s", exc
            )
            return None

    # ------------------------------------------------------------------
    # Internal helpers — task extraction
    # ------------------------------------------------------------------

    def _extract_tasks(
        self, data: dict[str, Any]
    ) -> dict[str, dict[str, Any]]:
        """Return the task entities dict from AppBaseData.

        SP stores tasks at data["task"]["entities"] — a dict mapping
        task-id strings to task objects.
        """
        task_section = data.get("task") or {}
        entities: dict[str, dict[str, Any]] = task_section.get("entities") or {}
        return entities

    def _is_top_level(self, task: dict[str, Any]) -> bool:
        """Return True when the task has no parent (top-level)."""
        parent_id = task.get("parentId")
        return not parent_id

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    def _derive_status(self, task: dict[str, Any]) -> str:
        """Derive DTO status from SP task fields."""
        if task.get("isDone"):
            return "done"
        time_spent = task.get("timeSpent") or 0
        if time_spent > 0:
            return "in_progress"
        return "todo"

    def _parse_due_date(self, raw: str | None) -> datetime | None:
        """Parse SP dueDay string 'YYYY-MM-DD' to datetime."""
        if not raw:
            return None
        try:
            return datetime.strptime(raw, "%Y-%m-%d")
        except ValueError:
            return None

    def _estimate_minutes(self, task: dict[str, Any]) -> int | None:
        """Convert SP timeEstimate (ms) to minutes.  None if absent/zero."""
        estimate_ms = task.get("timeEstimate")
        if not estimate_ms:
            return None
        return int(estimate_ms / 60_000)

    def _to_dto(self, task: dict[str, Any]) -> TaskDTO:
        tag_ids: list[str] = task.get("tagIds") or []
        due_date = self._parse_due_date(task.get("dueDay"))
        status = self._derive_status(task)
        estimated_minutes = self._estimate_minutes(task)

        return TaskDTO(
            id=str(task.get("id", "")),
            title=task.get("title", ""),
            description=task.get("notes") or "",
            status=status,
            priority="none",
            labels=tag_ids,
            due_date=due_date,
            estimated_minutes=estimated_minutes,
            source="superproductivity",
            source_url="",
            raw_data=task,
        )

    # ------------------------------------------------------------------
    # TaskSource interface
    # ------------------------------------------------------------------

    def get_tasks(self, filters: dict | None = None) -> list[TaskDTO]:
        """Retrieve top-level SP tasks, optionally filtered."""
        data = self._load_json()
        if data is None:
            return []

        entities = self._extract_tasks(data)
        top_level = [t for t in entities.values() if self._is_top_level(t)]
        dtos = [self._to_dto(t) for t in top_level]

        if filters:
            if "status" in filters:
                dtos = [t for t in dtos if t.status == filters["status"]]
            if "priority" in filters:
                dtos = [t for t in dtos if t.priority == filters["priority"]]

        return dtos

    def get_task(self, task_id: str) -> TaskDTO | None:
        """Retrieve a single SP task by its id."""
        data = self._load_json()
        if data is None:
            return None

        entities = self._extract_tasks(data)
        task = entities.get(task_id)
        if task is None:
            return None
        return self._to_dto(task)

    def log_time(self, task_id: str, minutes: int, notes: str = "") -> bool:
        """Not supported — SP has no writable API."""
        logger.info(
            "SuperProductivityAdapter: log_time not supported (read-only)"
        )
        return False

    def update_status(self, task_id: str, new_status: str) -> bool:
        """Not supported — SP has no writable API."""
        logger.info(
            "SuperProductivityAdapter: update_status not supported (read-only)"
        )
        return False
