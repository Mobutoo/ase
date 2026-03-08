"""LocalAdapter — manages ad-hoc tasks stored in Ase's own database."""
from __future__ import annotations

from app.models import LocalTask
from .base import TaskSource, TaskDTO


class LocalAdapter(TaskSource):
    """Task source for tasks created directly in Ase."""

    def __init__(self, user):
        self._user = user

    @property
    def source_name(self) -> str:
        return "local"

    def _to_dto(self, task: LocalTask) -> TaskDTO:
        return TaskDTO(
            id=str(task.id),
            title=task.title,
            description=task.description,
            status=task.status,
            priority=task.priority,
            labels=task.labels or [],
            due_date=task.due_date,
            estimated_minutes=task.estimated_minutes,
            source="local",
            source_url="",
            raw_data={"display_order": task.display_order},
        )

    def get_tasks(self, filters: dict | None = None) -> list[TaskDTO]:
        qs = LocalTask.objects.filter(user=self._user)
        if filters:
            if "status" in filters:
                qs = qs.filter(status=filters["status"])
            if "priority" in filters:
                qs = qs.filter(priority=filters["priority"])
        return [self._to_dto(t) for t in qs]

    def get_task(self, task_id: str) -> TaskDTO | None:
        try:
            task = LocalTask.objects.get(id=int(task_id), user=self._user)
            return self._to_dto(task)
        except (LocalTask.DoesNotExist, ValueError):
            return None

    def log_time(self, task_id: str, minutes: int, notes: str = "") -> bool:
        # For local tasks, time is tracked via Session, not on the task itself.
        # This is a no-op that returns True for compatibility.
        return True

    def update_status(self, task_id: str, new_status: str) -> bool:
        try:
            task = LocalTask.objects.get(id=int(task_id), user=self._user)
            task.status = new_status
            task.save(update_fields=["status", "updated_at"])
            return True
        except (LocalTask.DoesNotExist, ValueError):
            return False
