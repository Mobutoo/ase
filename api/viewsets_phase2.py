"""Phase 2 viewsets — UnifiedTask, Playlist, TaskSourceConfig.

Do NOT modify viewsets.py; these will be merged at integration time.

Endpoints (to be registered in urls.py at integration):
    GET  /api/v1/unified-tasks/                     list tasks from all enabled sources
    GET  /api/v1/unified-tasks/{source}/{id}/       retrieve single task
    POST /api/v1/unified-tasks/{source}/{id}/log_time/
    POST /api/v1/unified-tasks/{source}/{id}/update_status/

    CRUD /api/v1/playlists/
    POST /api/v1/playlists/{id}/set_default/

    CRUD /api/v1/task-sources/
    POST /api/v1/task-sources/{id}/test/            test connectivity for a source
"""
from __future__ import annotations

import logging

from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from adapters.registry import UnknownSourceType, get_adapter
from app.models_phase2 import Playlist, TaskSourceConfig
from api.serializers_phase2 import (
    PlaylistSerializer,
    TaskDTOSerializer,
    TaskSourceConfigSerializer,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# UnifiedTaskViewSet
# ---------------------------------------------------------------------------

class UnifiedTaskViewSet(viewsets.ViewSet):
    """Aggregate tasks from all enabled TaskSourceConfigs for the current user.

    This is a read-mostly ViewSet backed by adapters, not a DB queryset.
    """

    def list(self, request) -> Response:
        """GET /api/v1/unified-tasks/

        Query params:
            status   — filter by status (todo, in_progress, done)
            priority — filter by priority (urgent, high, medium, low, none)
            source   — limit to a specific source_type
        """
        filters = {}
        for key in ("status", "priority", "labels"):
            val = request.query_params.get(key)
            if val:
                filters[key] = val

        source_filter = request.query_params.get("source")
        configs = TaskSourceConfig.objects.filter(
            user=request.user, enabled=True
        ).order_by("display_order")

        if source_filter:
            configs = configs.filter(source_type=source_filter)

        all_tasks = []
        errors = []

        for cfg in configs:
            try:
                adapter_config = dict(cfg.config)
                if cfg.source_type == "local":
                    adapter_config["user"] = request.user
                adapter = get_adapter(cfg.source_type, adapter_config)
                tasks = adapter.get_tasks(filters or None)
                all_tasks.extend(tasks)
            except UnknownSourceType as exc:
                errors.append({"source": cfg.source_type, "error": str(exc)})
            except Exception as exc:
                logger.error(
                    "UnifiedTaskViewSet.list: error fetching from %s for user %s — %s",
                    cfg.source_type,
                    request.user.username,
                    exc,
                )
                errors.append({"source": cfg.source_type, "error": "fetch_failed"})

        serializer = TaskDTOSerializer(all_tasks, many=True)
        response_data: dict = {"tasks": serializer.data, "count": len(all_tasks)}
        if errors:
            response_data["errors"] = errors
        return Response(response_data)

    def retrieve(self, request, pk=None) -> Response:
        """GET /api/v1/unified-tasks/{source}__{task_id}/

        pk format: "<source_type>__<task_id>", e.g. "plane__abc-uuid" or "github__42"
        """
        if "__" not in (pk or ""):
            return Response(
                {"error": "pk must be in format '<source>__<task_id>'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        source_type, task_id = pk.split("__", 1)

        try:
            cfg = TaskSourceConfig.objects.get(
                user=request.user, source_type=source_type, enabled=True
            )
        except TaskSourceConfig.DoesNotExist:
            return Response(
                {"error": f"No enabled config found for source '{source_type}'"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            adapter_config = dict(cfg.config)
            if source_type == "local":
                adapter_config["user"] = request.user
            adapter = get_adapter(source_type, adapter_config)
            task = adapter.get_task(task_id)
        except Exception as exc:
            logger.error(
                "UnifiedTaskViewSet.retrieve: error for %s/%s — %s",
                source_type,
                task_id,
                exc,
            )
            return Response(
                {"error": "adapter_error", "detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if task is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        return Response(TaskDTOSerializer(task).data)

    @action(detail=True, methods=["post"], url_path="log_time")
    def log_time(self, request, pk=None) -> Response:
        """POST /api/v1/unified-tasks/{source}__{task_id}/log_time/

        Body: { "minutes": 25, "notes": "optional note" }
        """
        if "__" not in (pk or ""):
            return Response(
                {"error": "pk must be in format '<source>__<task_id>'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        source_type, task_id = pk.split("__", 1)

        # Validate input
        minutes = request.data.get("minutes")
        if not minutes or not isinstance(minutes, int) or minutes <= 0:
            return Response(
                {"error": "minutes must be a positive integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        notes = str(request.data.get("notes", ""))

        try:
            cfg = TaskSourceConfig.objects.get(
                user=request.user, source_type=source_type, enabled=True
            )
        except TaskSourceConfig.DoesNotExist:
            return Response(
                {"error": f"No enabled config found for source '{source_type}'"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            adapter_config = dict(cfg.config)
            if source_type == "local":
                adapter_config["user"] = request.user
            adapter = get_adapter(source_type, adapter_config)
            success = adapter.log_time(task_id, minutes, notes)
        except Exception as exc:
            logger.error("UnifiedTaskViewSet.log_time error — %s", exc)
            return Response(
                {"error": "adapter_error", "detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if not success:
            return Response(
                {"error": "log_time failed on the remote source"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response({"logged": True, "minutes": minutes})

    @action(detail=True, methods=["post"], url_path="update_status")
    def update_status(self, request, pk=None) -> Response:
        """POST /api/v1/unified-tasks/{source}__{task_id}/update_status/

        Body: { "status": "in_progress" }
        """
        if "__" not in (pk or ""):
            return Response(
                {"error": "pk must be in format '<source>__<task_id>'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        source_type, task_id = pk.split("__", 1)

        new_status = request.data.get("status")
        valid_statuses = ("todo", "in_progress", "done")
        if new_status not in valid_statuses:
            return Response(
                {"error": f"status must be one of {valid_statuses}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            cfg = TaskSourceConfig.objects.get(
                user=request.user, source_type=source_type, enabled=True
            )
        except TaskSourceConfig.DoesNotExist:
            return Response(
                {"error": f"No enabled config found for source '{source_type}'"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            adapter_config = dict(cfg.config)
            if source_type == "local":
                adapter_config["user"] = request.user
            adapter = get_adapter(source_type, adapter_config)
            success = adapter.update_status(task_id, new_status)
        except Exception as exc:
            logger.error("UnifiedTaskViewSet.update_status error — %s", exc)
            return Response(
                {"error": "adapter_error", "detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if not success:
            return Response(
                {"error": "update_status failed on the remote source"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response({"updated": True, "status": new_status})


# ---------------------------------------------------------------------------
# PlaylistViewSet
# ---------------------------------------------------------------------------

class PlaylistViewSet(viewsets.ModelViewSet):
    """CRUD viewset for Playlist model.

    Enforces single-default invariant: setting is_default=True clears all
    other defaults for the same user.
    """

    serializer_class = PlaylistSerializer

    def get_queryset(self):
        return Playlist.objects.filter(user=self.request.user)

    def _enforce_single_default(self, playlist: Playlist) -> None:
        """Clear is_default on all other playlists for this user."""
        Playlist.objects.filter(
            user=self.request.user, is_default=True
        ).exclude(pk=playlist.pk).update(is_default=False)

    def perform_create(self, serializer) -> None:
        playlist = serializer.save(user=self.request.user)
        if playlist.is_default:
            self._enforce_single_default(playlist)

    def perform_update(self, serializer) -> None:
        playlist = serializer.save()
        if playlist.is_default:
            self._enforce_single_default(playlist)

    @action(detail=True, methods=["post"], url_path="set_default")
    def set_default(self, request, pk=None) -> Response:
        """POST /api/v1/playlists/{id}/set_default/

        Marks this playlist as the default and clears all others.
        """
        playlist = self.get_object()
        # Clear existing defaults
        Playlist.objects.filter(
            user=request.user, is_default=True
        ).update(is_default=False)
        # Mark this one as default — create new instance to stay immutable
        Playlist.objects.filter(pk=playlist.pk).update(is_default=True)
        playlist.refresh_from_db()
        return Response(PlaylistSerializer(playlist, context={"request": request}).data)


# ---------------------------------------------------------------------------
# TaskSourceConfigViewSet
# ---------------------------------------------------------------------------

class TaskSourceConfigViewSet(viewsets.ModelViewSet):
    """CRUD viewset for TaskSourceConfig model.

    Also provides a /test/ action to verify adapter connectivity.
    """

    serializer_class = TaskSourceConfigSerializer

    def get_queryset(self):
        return TaskSourceConfig.objects.filter(user=self.request.user)

    def perform_create(self, serializer) -> None:
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"], url_path="test")
    def test(self, request, pk=None) -> Response:
        """POST /api/v1/task-sources/{id}/test/

        Attempts to fetch tasks from the configured source to verify
        connectivity and credentials. Returns first 3 task titles on success.
        """
        cfg = self.get_object()

        try:
            adapter_config = dict(cfg.config)
            if cfg.source_type == "local":
                adapter_config["user"] = request.user
            adapter = get_adapter(cfg.source_type, adapter_config)
            tasks = adapter.get_tasks()
        except UnknownSourceType as exc:
            return Response(
                {"ok": False, "error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.warning(
                "TaskSourceConfigViewSet.test: failed for %s/%s — %s",
                request.user.username,
                cfg.source_type,
                exc,
            )
            return Response(
                {"ok": False, "error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        sample = [t.title for t in tasks[:3]]
        return Response({
            "ok": True,
            "source_type": cfg.source_type,
            "task_count": len(tasks),
            "sample_titles": sample,
        })
