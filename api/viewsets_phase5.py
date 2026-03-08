"""
Phase 5 viewsets — AI Copilot via n8n / OpenClaw.

Two viewsets:

1. WebhookViewSet
   Receives callbacks FROM n8n after AI processing has completed.
   Validates X-Webhook-Secret header before accepting any payload.
   Creates AISuggestion records that the user then sees via AISuggestionViewSet.

2. AISuggestionViewSet
   User-facing CRUD + action endpoints:
     GET  /ai-suggestions/               — list own suggestions
     POST /ai-suggestions/{id}/accept/   — mark accepted=True
     POST /ai-suggestions/{id}/dismiss/  — mark accepted=False
     POST /ai-suggestions/request_plan/  — trigger n8n daily-plan webhook
     POST /ai-suggestions/request_reflection/ — trigger n8n reflection webhook
"""
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from app.models import AISuggestion, EnergyReading, LocalTask
from app.webhooks import send_daily_plan_request, send_reflection_prompt
from api.serializers_phase5 import (
    AISuggestionSerializer,
    PlanRequestSerializer,
    ReflectionRequestSerializer,
    WebhookCallbackSerializer,
)

logger = logging.getLogger(__name__)

User = get_user_model()

_WEBHOOK_SECRET_HEADER = "HTTP_X_WEBHOOK_SECRET"


def _validate_webhook_secret(request):
    """Return True if the X-Webhook-Secret header matches the configured secret.

    Always returns False when N8N_WEBHOOK_SECRET is not set — callers should
    treat this as a misconfiguration and return 503, not 401, so n8n can alert.
    """
    expected = getattr(settings, "N8N_WEBHOOK_SECRET", None)
    if not expected:
        logger.error(
            "N8N_WEBHOOK_SECRET not configured — inbound webhook validation impossible"
        )
        return False
    provided = request.META.get(_WEBHOOK_SECRET_HEADER, "")
    return provided == expected


class WebhookViewSet(viewsets.ViewSet):
    """
    Receives callbacks from n8n after AI processing.

    All endpoints are unauthenticated at the session level (n8n is a machine
    client) but validated via the X-Webhook-Secret shared secret header.

    POST /api/v1/webhooks/callback/
        Body: { username, suggestion_type, content }
        Creates an AISuggestion for the target user.
    """

    authentication_classes = []
    permission_classes = []

    @action(detail=False, methods=["post"], url_path="callback")
    def callback(self, request):
        """Receive AI suggestion payload from n8n and persist it."""
        if not _validate_webhook_secret(request):
            logger.warning(
                "Inbound webhook rejected — invalid or missing X-Webhook-Secret"
                " from %s",
                request.META.get("REMOTE_ADDR"),
            )
            return Response(
                {"error": "Unauthorized"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = WebhookCallbackSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "Inbound webhook payload validation failed: %s",
                serializer.errors,
            )
            return Response(
                {"error": "Invalid payload", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        validated = serializer.validated_data
        username = validated["username"]

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            logger.warning(
                "Inbound webhook references unknown user=%s", username
            )
            return Response(
                {"error": f"Unknown user: {username}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        suggestion = AISuggestion.objects.create(
            user=user,
            suggestion_type=validated["suggestion_type"],
            content=validated["content"],
            accepted=None,
        )

        logger.info(
            "AISuggestion created: id=%s user=%s type=%s",
            suggestion.pk,
            username,
            suggestion.suggestion_type,
        )

        return Response(
            {"id": suggestion.pk, "status": "created"},
            status=status.HTTP_201_CREATED,
        )


class AISuggestionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    User-facing AI suggestions.

    Read operations + accept / dismiss / request_plan / request_reflection actions.
    All endpoints require authentication (IsAuthenticated).
    Users can only see their own suggestions.
    """

    serializer_class = AISuggestionSerializer
    permission_classes = [IsAuthenticated]

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
        """Mark a suggestion as accepted."""
        suggestion = self.get_object()

        if suggestion.accepted is not None:
            return Response(
                {"error": "Suggestion already actioned", "accepted": suggestion.accepted},
                status=status.HTTP_409_CONFLICT,
            )

        updated = AISuggestion.objects.filter(pk=suggestion.pk, accepted__isnull=True).update(
            accepted=True
        )
        if updated == 0:
            return Response(
                {"error": "Suggestion already actioned"},
                status=status.HTTP_409_CONFLICT,
            )

        suggestion.refresh_from_db()
        logger.info(
            "AISuggestion accepted: id=%s user=%s", suggestion.pk, request.user.username
        )
        return Response(AISuggestionSerializer(suggestion).data)

    @action(detail=True, methods=["post"])
    def dismiss(self, request, pk=None):
        """Mark a suggestion as dismissed."""
        suggestion = self.get_object()

        if suggestion.accepted is not None:
            return Response(
                {"error": "Suggestion already actioned", "accepted": suggestion.accepted},
                status=status.HTTP_409_CONFLICT,
            )

        updated = AISuggestion.objects.filter(pk=suggestion.pk, accepted__isnull=True).update(
            accepted=False
        )
        if updated == 0:
            return Response(
                {"error": "Suggestion already actioned"},
                status=status.HTTP_409_CONFLICT,
            )

        suggestion.refresh_from_db()
        logger.info(
            "AISuggestion dismissed: id=%s user=%s", suggestion.pk, request.user.username
        )
        return Response(AISuggestionSerializer(suggestion).data)

    @action(detail=False, methods=["post"])
    def request_plan(self, request):
        """Trigger an AI daily plan request via n8n.

        Gathers the user's pending/in-progress tasks and recent energy history,
        fires the n8n webhook (timeout=30 s), and if n8n responds synchronously
        with a suggestion payload it is persisted and returned immediately.
        If n8n processes asynchronously it will POST back to /webhooks/callback/.
        """
        serializer = PlanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data

        include_done = params.get("include_done_tasks", False)
        energy_days = params.get("energy_days", 7)

        task_qs = LocalTask.objects.filter(user=request.user)
        if not include_done:
            task_qs = task_qs.exclude(status="done")

        tasks = list(
            task_qs.values(
                "id", "title", "status", "priority", "estimated_minutes", "due_date"
            )
        )

        cutoff = timezone.now() - timezone.timedelta(days=energy_days)
        energy_history = list(
            EnergyReading.objects.filter(user=request.user, timestamp__gte=cutoff)
            .values("timestamp", "level", "context")
            .order_by("timestamp")
        )

        result = send_daily_plan_request(request.user, tasks, energy_history)

        if result is None:
            logger.warning(
                "Daily plan webhook not configured or failed for user=%s",
                request.user.username,
            )
            return Response(
                {"status": "queued", "message": "Webhook not configured or request failed"},
                status=status.HTTP_202_ACCEPTED,
            )

        # n8n responded synchronously — persist and return
        if isinstance(result, dict) and result.get("suggestion_type") and result.get("content"):
            suggestion = AISuggestion.objects.create(
                user=request.user,
                suggestion_type=result["suggestion_type"],
                content=result["content"],
                accepted=None,
            )
            logger.info(
                "Daily plan suggestion created synchronously: id=%s user=%s",
                suggestion.pk,
                request.user.username,
            )
            return Response(
                AISuggestionSerializer(suggestion).data,
                status=status.HTTP_201_CREATED,
            )

        # Async path — n8n acknowledged but will callback later
        return Response(
            {"status": "queued", "message": "Daily plan request sent to n8n"},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=False, methods=["post"])
    def request_reflection(self, request):
        """Trigger an end-of-day reflection prompt via n8n.

        Gathers today's sessions and fires the n8n reflection webhook.
        Same sync/async handling as request_plan.
        """
        serializer = ReflectionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from app.models import Session  # local import to avoid circular risk

        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        sessions_today = list(
            Session.objects.filter(
                user=request.user,
                started_at__gte=today_start,
            ).order_by("started_at")
        )

        result = send_reflection_prompt(request.user, sessions_today)

        if result is None:
            logger.warning(
                "Reflection webhook not configured or failed for user=%s",
                request.user.username,
            )
            return Response(
                {"status": "queued", "message": "Webhook not configured or request failed"},
                status=status.HTTP_202_ACCEPTED,
            )

        if isinstance(result, dict) and result.get("suggestion_type") and result.get("content"):
            suggestion = AISuggestion.objects.create(
                user=request.user,
                suggestion_type=result["suggestion_type"],
                content=result["content"],
                accepted=None,
            )
            logger.info(
                "Reflection suggestion created synchronously: id=%s user=%s",
                suggestion.pk,
                request.user.username,
            )
            return Response(
                AISuggestionSerializer(suggestion).data,
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {"status": "queued", "message": "Reflection request sent to n8n"},
            status=status.HTTP_202_ACCEPTED,
        )
