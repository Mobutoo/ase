"""GrocyAdapter — bridges Ase with a self-hosted Grocy stock/chore instance.

Config keys (stored in TaskSourceConfig.config JSONField):
    api_url : base URL of the Grocy API, e.g. "https://grocy.example.com"
    api_key : Grocy API key (Manage API keys in Grocy → Admin)

Environment variable fallbacks (used when config keys are absent):
    GROCY_URL     : same as api_url
    GROCY_API_KEY : same as api_key

Tasks exposed by this adapter
------------------------------
Two categories of tasks are merged and returned by get_tasks():

1. Expiring stock items  (label "stock")
   Fetched from GET /api/stock/products/expiring-soon.
   - id        : "stock-<product_id>"
   - title     : "Vérifier stock: <product_name>"
   - status    : "todo"
   - due_date  : best_before_date (earliest expiry in the batch)
   - priority  : "urgent" if expires within 2 days, "high" within 5, else "medium"
   - labels    : ["stock", "peremption"]

2. Due Grocy chores  (label "chore")
   Fetched from GET /api/chores (filtered to overdue or due today).
   - id        : "chore-<chore_id>"
   - title     : chore name
   - status    : "todo" (or "done" if last_tracked_time is today)
   - due_date  : next_estimated_execution_time
   - priority  : "high" if overdue, "medium" if due today, "low" otherwise
   - labels    : ["chore"]

update_status() dispatches on the task-id prefix:
  * "stock-<id>"  → consume one unit (POST /api/stock/products/<id>/consume)
  * "chore-<id>"  → track chore execution (POST /api/chores/<id>/execute)
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from requests.exceptions import ConnectionError, HTTPError, Timeout

from .base import TaskDTO, TaskSource

logger = logging.getLogger(__name__)

_NOW = datetime.now  # patched in tests


def _utcnow() -> datetime:
    return _NOW(tz=timezone.utc)


def _days_until(dt: datetime | None) -> int | None:
    """Return days between now and dt; negative means overdue."""
    if dt is None:
        return None
    delta = dt - _utcnow()
    return delta.days


def _expiry_priority(days: int | None) -> str:
    if days is None:
        return "medium"
    if days <= 2:
        return "urgent"
    if days <= 5:
        return "high"
    return "medium"


def _chore_priority(days: int | None) -> str:
    if days is None:
        return "low"
    if days < 0:
        return "high"
    if days == 0:
        return "medium"
    return "low"


class GrocyAdapter(TaskSource):
    """TaskSource implementation backed by a self-hosted Grocy API.

    Surfaces expiring stock items and due chores as TaskDTO objects so Ase's
    agent system can propose shopping, consumption, or cleaning tasks.
    """

    def __init__(self, config: dict) -> None:
        api_url = config.get("api_url") or os.environ.get("GROCY_URL", "")
        api_key = config.get("api_key") or os.environ.get("GROCY_API_KEY", "")
        if not api_url:
            raise KeyError("GrocyAdapter requires 'api_url' in config or GROCY_URL env var.")
        if not api_key:
            raise KeyError("GrocyAdapter requires 'api_key' in config or GROCY_API_KEY env var.")
        self._api_url = api_url.rstrip("/")
        self._api_key = api_key

    @property
    def source_name(self) -> str:
        return "grocy"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        return {
            "GROCY-API-KEY": self._api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: dict | None = None) -> Any:
        url = f"{self._api_url}{path}"
        try:
            resp = requests.get(
                url, headers=self._headers(), params=params or {}, timeout=10
            )
            resp.raise_for_status()
            return resp.json()
        except ConnectionError:
            logger.error("GrocyAdapter: cannot connect to %s", self._api_url)
            return None
        except Timeout:
            logger.error("GrocyAdapter: request timed out for %s", url)
            return None
        except HTTPError as exc:
            logger.error(
                "GrocyAdapter: HTTP %s for GET %s — %s",
                exc.response.status_code,
                url,
                exc.response.text[:200],
            )
            return None

    def _post(self, path: str, payload: dict) -> dict | None:
        url = f"{self._api_url}{path}"
        try:
            resp = requests.post(
                url, json=payload, headers=self._headers(), timeout=10
            )
            resp.raise_for_status()
            # Grocy often returns 204 No Content on success
            if resp.status_code == 204 or not resp.content:
                return {}
            return resp.json()
        except ConnectionError:
            logger.error("GrocyAdapter: cannot connect to %s", self._api_url)
            return None
        except Timeout:
            logger.error("GrocyAdapter: POST timed out for %s", url)
            return None
        except HTTPError as exc:
            logger.error(
                "GrocyAdapter: HTTP %s for POST %s — %s",
                exc.response.status_code,
                url,
                exc.response.text[:200],
            )
            return None

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    def _parse_dt(self, raw: str | None) -> datetime | None:
        """Parse a Grocy datetime string to an aware UTC datetime."""
        if not raw:
            return None
        formats = [
            "%Y-%m-%d %H:%M:%S",  # Grocy default: "2025-03-15 00:00:00"
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(raw[:19], fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        return None

    def _stock_to_dto(self, item: dict[str, Any]) -> TaskDTO:
        """Convert a Grocy expiring-stock item to a TaskDTO."""
        product = item.get("product") or {}
        product_id = str(product.get("id") or item.get("product_id") or "")
        product_name = product.get("name") or item.get("product_name") or "Produit inconnu"
        best_before = self._parse_dt(
            item.get("best_before_date") or item.get("due_date")
        )
        days = _days_until(best_before)
        amount = item.get("amount") or item.get("amount_opened") or 1
        unit = (product.get("qu_id_stock") and "") or ""  # unit display is optional

        return TaskDTO(
            id=f"stock-{product_id}",
            title=f"Vérifier stock: {product_name}",
            description=(
                f"{amount}{unit} unité(s) — péremption: "
                f"{best_before.strftime('%Y-%m-%d') if best_before else 'inconnue'}"
            ),
            status="todo",
            priority=_expiry_priority(days),
            labels=["stock", "peremption"],
            due_date=best_before,
            estimated_minutes=None,
            source="grocy",
            source_url=f"{self._api_url}/stockoverview",
            raw_data=item,
        )

    def _chore_to_dto(self, chore: dict[str, Any]) -> TaskDTO:
        """Convert a Grocy chore dict to a TaskDTO."""
        chore_details = chore.get("chore") or chore
        chore_id = str(chore_details.get("id") or chore.get("chore_id") or "")
        chore_name = chore_details.get("name") or chore.get("chore_name") or "Tâche sans nom"
        next_exec_str = chore.get("next_estimated_execution_time") or chore.get("next_execution_now")
        next_exec = self._parse_dt(next_exec_str)
        days = _days_until(next_exec)

        # Determine status: done if last execution was today
        last_tracked_str = chore.get("last_tracked_time")
        status = "todo"
        if last_tracked_str:
            last_tracked = self._parse_dt(last_tracked_str)
            if last_tracked and last_tracked.date() == _utcnow().date():
                status = "done"

        return TaskDTO(
            id=f"chore-{chore_id}",
            title=chore_name,
            description=chore_details.get("description") or "",
            status=status,
            priority=_chore_priority(days),
            labels=["chore"],
            due_date=next_exec,
            estimated_minutes=None,
            source="grocy",
            source_url=f"{self._api_url}/choresoverview",
            raw_data=chore,
        )

    # ------------------------------------------------------------------
    # TaskSource interface
    # ------------------------------------------------------------------

    def get_tasks(self, filters: dict | None = None) -> list[TaskDTO]:
        """Return expiring stock items and due chores as TaskDTOs.

        Filters supported:
            status   : "todo" | "done"
            priority : "urgent" | "high" | "medium" | "low" | "none"
            labels   : list[str] — e.g. ["stock"] to only get stock tasks
        """
        dtos: list[TaskDTO] = []

        # --- Expiring stock items ---
        # days_expiring_soon defaults to 5 if not in filters
        days_soon = 5
        stock_data = self._get(
            "/api/stock/products/expiring-soon",
            params={"expiring_days": days_soon},
        )
        if stock_data is not None:
            items = stock_data if isinstance(stock_data, list) else []
            dtos.extend(self._stock_to_dto(item) for item in items)

        # --- Due chores ---
        chores_data = self._get("/api/chores")
        if chores_data is not None:
            chores = chores_data if isinstance(chores_data, list) else []
            now = _utcnow()
            for chore in chores:
                next_exec_str = chore.get("next_estimated_execution_time")
                next_exec = self._parse_dt(next_exec_str)
                # Include chores that are overdue or due within the next 7 days
                if next_exec is None or next_exec <= now + timedelta(days=7):
                    dtos.append(self._chore_to_dto(chore))

        if filters:
            if "status" in filters:
                dtos = [t for t in dtos if t.status == filters["status"]]
            if "priority" in filters:
                dtos = [t for t in dtos if t.priority == filters["priority"]]
            if "labels" in filters:
                requested_labels = set(filters["labels"])
                dtos = [
                    t for t in dtos if requested_labels.intersection(t.labels)
                ]

        return dtos

    def get_task(self, task_id: str) -> TaskDTO | None:
        """Retrieve a single stock item or chore by its composite ID."""
        if task_id.startswith("stock-"):
            product_id = task_id.removeprefix("stock-")
            data = self._get(f"/api/stock/products/{product_id}")
            if data is None:
                return None
            # Wrap in the same shape _stock_to_dto expects
            return self._stock_to_dto(
                {"product": data.get("product", {}), **data}
            )

        if task_id.startswith("chore-"):
            chore_id = task_id.removeprefix("chore-")
            data = self._get(f"/api/chores/{chore_id}")
            if data is None:
                return None
            return self._chore_to_dto(data)

        logger.warning("GrocyAdapter.get_task: unrecognised task_id format '%s'", task_id)
        return None

    def log_time(self, task_id: str, minutes: int, notes: str = "") -> bool:
        """Log time spent.

        Grocy has no time-tracking API for stock or chores. This is a no-op
        that returns True for interface compatibility.
        """
        logger.debug(
            "GrocyAdapter.log_time: no-op for task_id=%s (%d min)", task_id, minutes
        )
        return True

    def update_status(self, task_id: str, new_status: str) -> bool:
        """Mark a stock item consumed or a chore executed.

        Dispatches on the task_id prefix:
        - "stock-<product_id>" → consume 1 unit via POST /api/stock/products/<id>/consume
        - "chore-<chore_id>"  → track execution via POST /api/chores/<id>/execute

        Only the "done" status triggers a real API call; other values are no-ops.
        """
        if new_status != "done":
            logger.debug(
                "GrocyAdapter.update_status: status '%s' is a no-op for task_id=%s",
                new_status,
                task_id,
            )
            return True

        if task_id.startswith("stock-"):
            product_id = task_id.removeprefix("stock-")
            result = self._post(
                f"/api/stock/products/{product_id}/consume",
                {"amount": 1, "transaction_type": "consume", "spoiled": False},
            )
            return result is not None

        if task_id.startswith("chore-"):
            chore_id = task_id.removeprefix("chore-")
            result = self._post(
                f"/api/chores/{chore_id}/execute",
                {"tracked_time": _utcnow().strftime("%Y-%m-%d %H:%M:%S")},
            )
            return result is not None

        logger.warning(
            "GrocyAdapter.update_status: unrecognised task_id format '%s'", task_id
        )
        return False
