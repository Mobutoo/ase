import logging

from django.conf import settings
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from app.models import AISuggestion, EnergyReading, LocalTask, Session, UserSettings
from app.webhooks import send_daily_plan_request, send_reflection_prompt
from api.serializers import (
    AISuggestionSerializer,
    EnergyReadingSerializer,
    LocalTaskSerializer,
    SessionCompleteSerializer,
    SessionSerializer,
    UserSettingsSerializer,
)

logger = logging.getLogger(__name__)


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


class WebhookViewSet(viewsets.ViewSet):
    """Receive webhook callbacks from n8n / OpenClaw.

    Authentication uses a shared secret header (X-Webhook-Secret) rather than
    session auth so that n8n can POST without a Django session cookie.
    """

    permission_classes = [AllowAny]

    # Maps event type → internal suggestion_type value
    _EVENT_TO_TYPE = {
        "daily_plan": "daily_plan",
        "task_decomposition": "task_decomposition",
        "reflection_prompt": "reflection_prompt",
        "energy_suggestion": "energy_suggestion",
    }

    def _validate_secret(self, request):
        """Return True if the incoming request carries the correct webhook secret."""
        expected = getattr(settings, "N8N_WEBHOOK_SECRET", "")
        if not expected:
            # Secret not configured — accept all (dev/test mode)
            logger.warning("N8N_WEBHOOK_SECRET not set; accepting unauthenticated webhook")
            return True
        provided = request.headers.get("X-Webhook-Secret", "")
        return provided == expected

    def create(self, request):
        """POST /api/v1/webhooks/ — receive AI suggestion callback from n8n."""
        if not self._validate_secret(request):
            logger.warning("Incoming webhook rejected: invalid secret")
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        event_type = request.data.get("event")
        username = request.data.get("user")
        content = request.data.get("content")

        if not event_type or not username or content is None:
            return Response(
                {"error": "Missing required fields: event, user, content"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        suggestion_type = self._EVENT_TO_TYPE.get(event_type)
        if not suggestion_type:
            return Response(
                {"error": f"Unknown event type: {event_type}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Resolve user
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            logger.warning("Webhook received for unknown user: %s", username)
            return Response(
                {"error": f"User not found: {username}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        suggestion = AISuggestion.objects.create(
            user=user,
            suggestion_type=suggestion_type,
            content=content,
        )

        logger.info(
            "AI suggestion stored: id=%s type=%s user=%s",
            suggestion.pk,
            suggestion_type,
            username,
        )
        return Response(
            AISuggestionSerializer(suggestion).data,
            status=status.HTTP_201_CREATED,
        )


class AISuggestionViewSet(viewsets.ReadOnlyModelViewSet):
    """User-facing endpoint to browse and act on AI suggestions."""

    serializer_class = AISuggestionSerializer

    def get_queryset(self):
        qs = AISuggestion.objects.filter(user=self.request.user)
        suggestion_type = self.request.query_params.get("type")
        if suggestion_type:
            qs = qs.filter(suggestion_type=suggestion_type)
        pending = self.request.query_params.get("pending")
        if pending == "true":
            qs = qs.filter(accepted__isnull=True)
        return qs

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        """Mark a suggestion as accepted (accepted=True)."""
        suggestion = self.get_object()
        updated = AISuggestion(
            **{f.name: getattr(suggestion, f.name) for f in suggestion._meta.fields}
        )
        updated.accepted = True
        updated.save(update_fields=["accepted"])
        return Response(AISuggestionSerializer(updated).data)

    @action(detail=True, methods=["post"])
    def dismiss(self, request, pk=None):
        """Mark a suggestion as dismissed (accepted=False)."""
        suggestion = self.get_object()
        updated = AISuggestion(
            **{f.name: getattr(suggestion, f.name) for f in suggestion._meta.fields}
        )
        updated.accepted = False
        updated.save(update_fields=["accepted"])
        return Response(AISuggestionSerializer(updated).data)

    @action(detail=False, methods=["post"])
    def request_plan(self, request):
        """Trigger a daily plan request to n8n for the current user.

        Body (optional): { "tasks": [...], "energy_patterns": [...] }
        """
        tasks = request.data.get("tasks", [])
        energy_history = request.data.get("energy_patterns", [])

        result = send_daily_plan_request(request.user, tasks, energy_history)
        if result is None:
            return Response(
                {"status": "queued", "detail": "Webhook not configured or failed"},
                status=status.HTTP_202_ACCEPTED,
            )
        return Response({"status": "ok", "response": result})

    @action(detail=False, methods=["post"])
    def request_reflection(self, request):
        """Trigger an end-of-day reflection prompt for the current user.

        Body (optional): { "sessions": [...] }
        """
        from django.utils.timezone import now as tz_now
        today = tz_now().date()
        sessions_today = list(
            Session.objects.filter(
                user=request.user,
                started_at__date=today,
                completed=True,
            )
        )

        result = send_reflection_prompt(request.user, sessions_today)
        if result is None:
            return Response(
                {"status": "queued", "detail": "Webhook not configured or failed"},
                status=status.HTTP_202_ACCEPTED,
            )
        return Response({"status": "ok", "response": result})


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
