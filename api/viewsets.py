from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from app.models import Session, LocalTask, EnergyReading, UserSettings
from api.serializers import (
    SessionSerializer,
    SessionCompleteSerializer,
    LocalTaskSerializer,
    EnergyReadingSerializer,
    UserSettingsSerializer,
)


class SessionViewSet(viewsets.ModelViewSet):
    serializer_class = SessionSerializer

    def get_queryset(self):
        qs = Session.objects.filter(user=self.request.user)
        # Filter by mode
        mode = self.request.query_params.get("mode")
        if mode:
            qs = qs.filter(mode=mode)
        # Filter by active (not ended)
        active = self.request.query_params.get("active")
        if active == "true":
            qs = qs.filter(ended_at__isnull=True)
        return qs

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Mark a session as completed with actual duration."""
        session = self.get_object()
        if session.ended_at is not None:
            return Response(
                {"error": "Session already ended"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SessionCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        now = timezone.now()
        delta = now - session.started_at
        actual_minutes = int(delta.total_seconds() / 60)

        session.ended_at = now
        session.actual_duration = actual_minutes
        session.completed = True

        if "energy_after" in serializer.validated_data:
            session.energy_after = serializer.validated_data["energy_after"]
        if "notes" in serializer.validated_data:
            session.notes = serializer.validated_data["notes"]

        session.save()

        # Create energy reading if energy_after provided
        if session.energy_after:
            EnergyReading.objects.create(
                user=request.user,
                level=session.energy_after,
                context="session_end",
                session=session,
            )

        return Response(SessionSerializer(session).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel (abandon) a session without completing it."""
        session = self.get_object()
        if session.ended_at is not None:
            return Response(
                {"error": "Session already ended"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        delta = now - session.started_at
        session.ended_at = now
        session.actual_duration = int(delta.total_seconds() / 60)
        session.completed = False
        session.save()

        return Response(SessionSerializer(session).data)


class LocalTaskViewSet(viewsets.ModelViewSet):
    serializer_class = LocalTaskSerializer

    def get_queryset(self):
        qs = LocalTask.objects.filter(user=self.request.user)
        task_status = self.request.query_params.get("status")
        if task_status:
            qs = qs.filter(status=task_status)
        priority = self.request.query_params.get("priority")
        if priority:
            qs = qs.filter(priority=priority)
        return qs


class EnergyReadingViewSet(viewsets.ModelViewSet):
    serializer_class = EnergyReadingSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return EnergyReading.objects.filter(user=self.request.user)


class UserSettingsViewSet(viewsets.GenericViewSet):
    serializer_class = UserSettingsSerializer

    def get_object(self):
        settings, _ = UserSettings.objects.get_or_create(user=self.request.user)
        return settings

    def list(self, request):
        """GET /api/v1/settings/ — retrieve current user settings."""
        serializer = self.get_serializer(self.get_object())
        return Response(serializer.data)

    def partial_update(self, request, pk=None):
        """PATCH /api/v1/settings/ — update user settings."""
        settings = self.get_object()
        serializer = self.get_serializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
