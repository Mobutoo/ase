"""Abstract interface for task source adapters.

Any external task system (Plane, Super Productivity, Jira, etc.)
implements this interface so Ase can work with tasks agnostically.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class TaskDTO:
    """Unified task representation — immutable, source-agnostic."""
    id: str
    title: str
    description: str = ""
    status: str = "todo"  # todo, in_progress, done
    priority: str = "none"  # urgent, high, medium, low, none
    labels: list[str] = field(default_factory=list)
    due_date: datetime | None = None
    estimated_minutes: int | None = None
    source: str = "local"
    source_url: str = ""
    raw_data: dict = field(default_factory=dict)


class TaskSource(ABC):
    """Abstract interface for any task source."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Unique identifier for this source (e.g. 'local', 'plane')."""

    @abstractmethod
    def get_tasks(self, filters: dict | None = None) -> list[TaskDTO]:
        """Retrieve active tasks matching optional filters."""

    @abstractmethod
    def get_task(self, task_id: str) -> TaskDTO | None:
        """Retrieve a single task by ID."""

    @abstractmethod
    def log_time(self, task_id: str, minutes: int, notes: str = "") -> bool:
        """Record time spent on a task. Returns success."""

    @abstractmethod
    def update_status(self, task_id: str, new_status: str) -> bool:
        """Update a task's status. Returns success."""
