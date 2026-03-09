from __future__ import annotations

import logging
from datetime import timezone as dt_timezone

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from circles.models import Circle, CircleMember

from .models import AgentAction, MemberPreference, NotificationPreference
from .serializers import (
    AgentActionApproveSerializer,
    AgentActionRejectSerializer,
    AgentActionSerializer,
    MemberPreferenceSerializer,
    NotificationPreferenceSerializer,
)

logger = logging.getLogger(__name__)


def _get_circle_member(request: Request, circle_pk: int | str) -> CircleMember:
    """Return the CircleMember for the authenticated user in the given circle.

    Raises Http404 if the user is not a member of that circle.
    """
    return get_object_or_404(
        CircleMember,
        user=request.user,
        circle_id=circle_pk,
    )


class AgentActionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """ViewSet for AgentAction — list, retrieve, approve, reject.

    Direct creation from the API is NOT allowed.
    The agent service creates AgentAction records internally.
    Human approval is required before any action is executed.
    """

    serializer_class = AgentActionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        circle_pk = self.kwargs.get("circle_pk")
        _get_circle_member(self.request, circle_pk)
        qs = AgentAction.objects.filter(circle_id=circle_pk).select_related(
            "circle", "approved_by"
        )
        # Optional filter by status
        status_filter = self.request.query_params.get("status")
        if status_filter == "pending":
            qs = qs.filter(approved_at__isnull=True, rejected_at__isnull=True)
        elif status_filter == "approved":
            qs = qs.filter(approved_at__isnull=False, rejected_at__isnull=True)
        elif status_filter == "rejected":
            qs = qs.filter(rejected_at__isnull=False)
        elif status_filter == "executed":
            qs = qs.filter(executed_at__isnull=False)
        return qs

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request: Request, circle_pk: int = None, pk: int = None) -> Response:
        """Approve a pending agent action.

        Only circle members may approve. The action must be in pending state.
        Approval does not execute the action — execution is deferred to a Celery task.
        """
        member = _get_circle_member(request, circle_pk)
        agent_action = get_object_or_404(
            AgentAction, pk=pk, circle_id=circle_pk
        )

        serializer = AgentActionApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not agent_action.is_pending:
            return Response(
                {"detail": "Action is not in pending state."},
                status=status.HTTP_409_CONFLICT,
            )

        agent_action.approved_by = member
        agent_action.approved_at = timezone.now()
        agent_action.save(update_fields=["approved_by", "approved_at"])

        logger.info(
            "AgentAction %s approved by member %s in circle %s",
            agent_action.pk,
            member.pk,
            circle_pk,
        )

        # Schedule async execution
        try:
            from .tasks import execute_agent_action
            execute_agent_action.delay(agent_action.pk)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not schedule execute_agent_action: %s", exc)

        return Response(
            AgentActionSerializer(agent_action).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request: Request, circle_pk: int = None, pk: int = None) -> Response:
        """Reject a pending agent action.

        Rejected actions are retained in the audit log but never executed.
        """
        _get_circle_member(request, circle_pk)
        agent_action = get_object_or_404(
            AgentAction, pk=pk, circle_id=circle_pk
        )

        serializer = AgentActionRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not agent_action.is_pending:
            return Response(
                {"detail": "Action is not in pending state."},
                status=status.HTTP_409_CONFLICT,
            )

        reason = serializer.validated_data.get("reason", "")
        agent_action.rejected_at = timezone.now()
        if reason:
            agent_action.error = reason
        agent_action.save(update_fields=["rejected_at", "error"])

        logger.info(
            "AgentAction %s rejected in circle %s. Reason: %s",
            agent_action.pk,
            circle_pk,
            reason or "(none)",
        )

        return Response(
            AgentActionSerializer(agent_action).data,
            status=status.HTTP_200_OK,
        )


class MemberPreferenceViewSet(viewsets.ModelViewSet):
    """CRUD ViewSet for MemberPreference.

    Members can only manage their own preferences.
    """

    serializer_class = MemberPreferenceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        circle_pk = self.kwargs.get("circle_pk")
        member = _get_circle_member(self.request, circle_pk)
        qs = MemberPreference.objects.filter(member=member)
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        return qs

    def perform_create(self, serializer: MemberPreferenceSerializer) -> None:
        circle_pk = self.kwargs.get("circle_pk")
        member = _get_circle_member(self.request, circle_pk)
        serializer.save(member=member)

    def perform_update(self, serializer: MemberPreferenceSerializer) -> None:
        serializer.save()

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        instance = self.get_object()
        circle_pk = self.kwargs.get("circle_pk")
        member = _get_circle_member(request, circle_pk)
        if instance.member_id != member.pk:
            return Response(
                {"detail": "You can only delete your own preferences."},
                status=status.HTTP_403_FORBIDDEN,
            )
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificationPreferenceViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Retrieve + update NotificationPreference for the current member.

    Uses get_or_create so first access auto-provisions defaults.
    """

    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]

    def _get_or_create_prefs(self, request: Request, circle_pk: int | str) -> NotificationPreference:
        member = _get_circle_member(request, circle_pk)
        prefs, _ = NotificationPreference.objects.get_or_create(member=member)
        return prefs

    def get_object(self) -> NotificationPreference:
        circle_pk = self.kwargs.get("circle_pk")
        return self._get_or_create_prefs(self.request, circle_pk)

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        prefs = self.get_object()
        serializer = self.get_serializer(prefs)
        return Response(serializer.data)

    def update(self, request: Request, *args, **kwargs) -> Response:
        partial = kwargs.pop("partial", False)
        prefs = self.get_object()
        serializer = self.get_serializer(prefs, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)
