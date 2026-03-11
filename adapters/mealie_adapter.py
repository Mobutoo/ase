"""MealieAdapter — bridges Ase with a self-hosted Mealie recipe/meal-plan instance.

Config keys (stored in TaskSourceConfig.config JSONField):
    api_url : base URL of the Mealie API, e.g. "https://mealie.example.com"
    api_key : Mealie API token (Settings → API Tokens)

Environment variable fallbacks (used when config keys are absent):
    MEALIE_URL     : same as api_url
    MEALIE_API_KEY : same as api_key

Tasks exposed by this adapter
------------------------------
* Meal-plan entries (today + next 7 days)  → one TaskDTO per planned recipe.
  - id        : "mealplan-<entry_id>"
  - title     : "<meal_type>: <recipe_name>"   (e.g. "dinner: Poulet rôti")
  - status    : "todo" until marked cooked, "done" afterwards
  - due_date  : the planned date at midday (local noon, no tz)
  - labels    : ["mealplan", meal_type]
  - source    : "mealie"

* Cooking tasks stored inside individual recipe notes are NOT surfaced
  (Mealie has no first-class task API for those; use meal-plan entries instead).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

import requests
from requests.exceptions import ConnectionError, HTTPError, Timeout

from .base import TaskDTO, TaskSource

logger = logging.getLogger(__name__)

# Mealie meal-type strings → human-readable label kept in DTO labels
_MEAL_TYPE_LABELS = {
    "breakfast": "breakfast",
    "lunch": "lunch",
    "dinner": "dinner",
    "side": "side",
    "snack": "snack",
}

# DTO status that means "mark as cooked" on update_status
_DONE_STATUS = "done"


class MealieAdapter(TaskSource):
    """TaskSource implementation backed by a self-hosted Mealie API.

    Surfaces meal-plan entries (GET /api/groups/mealplans?startDate=…) as
    TaskDTO objects so Ase's agent system can reason about upcoming meals.
    """

    def __init__(self, config: dict) -> None:
        api_url = config.get("api_url") or os.environ.get("MEALIE_URL", "")
        api_key = config.get("api_key") or os.environ.get("MEALIE_API_KEY", "")
        if not api_url:
            raise KeyError("MealieAdapter requires 'api_url' in config or MEALIE_URL env var.")
        if not api_key:
            raise KeyError("MealieAdapter requires 'api_key' in config or MEALIE_API_KEY env var.")
        self._api_url = api_url.rstrip("/")
        self._api_key = api_key

    @property
    def source_name(self) -> str:
        return "mealie"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
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
            logger.error("MealieAdapter: cannot connect to %s", self._api_url)
            return None
        except Timeout:
            logger.error("MealieAdapter: request timed out for %s", url)
            return None
        except HTTPError as exc:
            logger.error(
                "MealieAdapter: HTTP %s for GET %s — %s",
                exc.response.status_code,
                url,
                exc.response.text[:200],
            )
            return None

    def _put(self, path: str, payload: dict) -> dict | None:
        url = f"{self._api_url}{path}"
        try:
            resp = requests.put(
                url, json=payload, headers=self._headers(), timeout=10
            )
            resp.raise_for_status()
            return resp.json()
        except ConnectionError:
            logger.error("MealieAdapter: cannot connect to %s", self._api_url)
            return None
        except Timeout:
            logger.error("MealieAdapter: PUT timed out for %s", url)
            return None
        except HTTPError as exc:
            logger.error(
                "MealieAdapter: HTTP %s for PUT %s — %s",
                exc.response.status_code,
                url,
                exc.response.text[:200],
            )
            return None

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    def _parse_date(self, raw: str | None) -> datetime | None:
        """Parse a Mealie date string (YYYY-MM-DD) to a noon-UTC datetime."""
        if not raw:
            return None
        try:
            d = datetime.strptime(raw, "%Y-%m-%d")
            # Return at midday UTC so the due date is unambiguous
            return d.replace(hour=12, tzinfo=timezone.utc)
        except ValueError:
            return None

    def _entry_to_dto(self, entry: dict[str, Any]) -> TaskDTO:
        """Convert a Mealie meal-plan entry dict to a TaskDTO."""
        entry_id = str(entry.get("id", ""))
        meal_type = str(entry.get("entryType") or entry.get("entry_type") or "dinner").lower()
        recipe = entry.get("recipe") or {}
        recipe_name = recipe.get("name") or entry.get("title") or "Repas sans titre"
        due_date = self._parse_date(entry.get("date"))

        labels = ["mealplan", _MEAL_TYPE_LABELS.get(meal_type, meal_type)]

        recipe_id = recipe.get("id") or recipe.get("slug") or ""
        source_url = (
            f"{self._api_url}/r/{recipe.get('slug', recipe_id)}" if recipe_id else self._api_url
        )

        return TaskDTO(
            id=f"mealplan-{entry_id}",
            title=f"{meal_type}: {recipe_name}",
            description=recipe.get("description") or "",
            status="todo",
            priority="none",
            labels=labels,
            due_date=due_date,
            estimated_minutes=recipe.get("totalTime") or recipe.get("total_time"),
            source="mealie",
            source_url=source_url,
            raw_data=entry,
        )

    # ------------------------------------------------------------------
    # TaskSource interface
    # ------------------------------------------------------------------

    def get_tasks(self, filters: dict | None = None) -> list[TaskDTO]:
        """Return upcoming meal-plan entries for the current week (+7 days).

        Mealie's /api/groups/mealplans endpoint accepts startDate / endDate
        query params (YYYY-MM-DD). We fetch today through today+7.

        Filters supported:
            status   : "todo" | "in_progress" | "done"  (all are "todo" from Mealie)
            priority : ignored (Mealie has no priority concept)
        """
        today = datetime.now(timezone.utc).date()
        end = today.replace(day=today.day + 7) if today.day <= 24 else today  # safe window

        params: dict[str, Any] = {
            "startDate": today.isoformat(),
            "endDate": end.isoformat(),
            "perPage": 50,
            "page": 1,
        }
        data = self._get("/api/groups/mealplans", params=params)
        if data is None:
            return []

        items = data if isinstance(data, list) else data.get("items", data.get("results", []))
        dtos = [self._entry_to_dto(entry) for entry in items]

        if filters:
            if "status" in filters:
                dtos = [t for t in dtos if t.status == filters["status"]]
            if "priority" in filters:
                dtos = [t for t in dtos if t.priority == filters["priority"]]

        return dtos

    def get_task(self, task_id: str) -> TaskDTO | None:
        """Retrieve a single meal-plan entry by its composite ID (mealplan-<id>)."""
        # Strip the "mealplan-" prefix to obtain the numeric Mealie entry ID
        raw_id = task_id.removeprefix("mealplan-")
        data = self._get(f"/api/groups/mealplans/{raw_id}")
        if data is None:
            return None
        return self._entry_to_dto(data)

    def log_time(self, task_id: str, minutes: int, notes: str = "") -> bool:
        """Log cooking time.

        Mealie has no time-tracking API for meal-plan entries. This is a no-op
        that returns True for interface compatibility.
        """
        logger.debug(
            "MealieAdapter.log_time: no-op for task_id=%s (%d min)", task_id, minutes
        )
        return True

    def update_status(self, task_id: str, new_status: str) -> bool:
        """Mark a meal as cooked (done) by updating the meal-plan entry.

        Mealie does not have a native "cooked" flag on meal-plan entries.
        When new_status is 'done', we DELETE the entry (it has been cooked).
        Any other status transition is a no-op (returns True for compatibility).
        """
        if new_status != _DONE_STATUS:
            logger.debug(
                "MealieAdapter.update_status: status '%s' is a no-op for task_id=%s",
                new_status,
                task_id,
            )
            return True

        raw_id = task_id.removeprefix("mealplan-")
        url = f"{self._api_url}/api/groups/mealplans/{raw_id}"
        try:
            resp = requests.delete(url, headers=self._headers(), timeout=10)
            resp.raise_for_status()
            return True
        except ConnectionError:
            logger.error("MealieAdapter: cannot connect to %s", self._api_url)
            return False
        except Timeout:
            logger.error("MealieAdapter: DELETE timed out for %s", url)
            return False
        except HTTPError as exc:
            logger.error(
                "MealieAdapter: HTTP %s for DELETE %s — %s",
                exc.response.status_code,
                url,
                exc.response.text[:200],
            )
            return False
