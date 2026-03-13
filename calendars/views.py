from __future__ import annotations

import hashlib
import logging
from typing import Any

from django.db import transaction
from django.http import HttpResponse
from rest_framework import permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .caldav.ical import events_from_ics, event_to_ics
from .models import Calendar, CalendarSubscription, Event, EventException, GoogleCalendarSync
from .serializers import (
    CalendarSerializer,
    CalendarSubscriptionSerializer,
    EventSerializer,
    GoogleCalendarSyncSerializer,
    IcsImportConfirmSerializer,
    IcsImportPreviewSerializer,
)
from .services import detect_conflicts

logger = logging.getLogger(__name__)


class CalendarViewSet(viewsets.ModelViewSet):
    """CRUD for Calendar objects.

    Filters to calendars owned by the requesting user's CircleMember.
    """

    serializer_class = CalendarSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Calendar.objects.filter(
            owner__user=self.request.user
        ).order_by("name")

    def perform_create(self, serializer: CalendarSerializer) -> None:
        from circles.models import CircleMember

        member = CircleMember.objects.get(user=self.request.user)
        serializer.save(owner=member)


class EventViewSet(viewsets.ModelViewSet):
    """CRUD for Event objects with conflict detection and recurring-event edit modes."""

    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Event.objects.filter(
            calendar__owner__user=self.request.user
        ).prefetch_related("reminders", "members")

        calendar_id = self.request.query_params.get("calendar")
        if calendar_id:
            qs = qs.filter(calendar_id=calendar_id)

        start = self.request.query_params.get("start")
        end = self.request.query_params.get("end")
        if start:
            qs = qs.filter(end_at__gte=start)
        if end:
            qs = qs.filter(start_at__lte=end)

        return qs.order_by("start_at")

    def perform_create(self, serializer: EventSerializer) -> None:
        event = serializer.save()
        self._update_etag(event)

    def perform_update(self, serializer: EventSerializer) -> None:
        if serializer.instance and serializer.instance.subscription_id is not None:
            raise PermissionDenied("Subscribed events are read-only.")
        event = serializer.save()
        self._update_etag(event)

    def perform_destroy(self, instance: Event) -> None:
        if instance.subscription_id is not None:
            raise PermissionDenied("Subscribed events are read-only.")
        instance.delete()

    @staticmethod
    def _update_etag(event: Event) -> None:
        etag_source = f"{event.uid}{event.updated_at.isoformat()}"
        event.etag = hashlib.md5(etag_source.encode()).hexdigest()  # noqa: S324
        event.save(update_fields=["etag"])

    @action(detail=True, methods=["get"], url_path="conflicts")
    def conflicts(self, request: Request, pk: Any = None) -> Response:
        """Return events that overlap with this event's time slot."""
        event = self.get_object()
        overlapping = detect_conflicts(event)
        serializer = EventSerializer(overlapping, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="edit-this")
    def edit_this(self, request: Request, pk: Any = None) -> Response:
        """Edit only this occurrence of a recurring event.

        Creates an EventException that points to a new standalone event,
        then updates that replacement event with the provided data.
        """
        recurring = self.get_object()
        if not recurring.recurrence_rule:
            return Response(
                {"detail": "Event is not recurring."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        original_start_raw = request.data.get("original_start")
        if not original_start_raw:
            return Response(
                {"detail": "original_start is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            replacement_data = {**request.data}
            replacement_data.pop("original_start", None)
            replacement_data["parent_event"] = recurring.pk
            replacement_data["recurrence_rule"] = None

            serializer = EventSerializer(data=replacement_data)
            serializer.is_valid(raise_exception=True)
            replacement = serializer.save()
            self._update_etag(replacement)

            EventException.objects.update_or_create(
                recurring_event=recurring,
                original_start=original_start_raw,
                defaults={"replacement_event": replacement},
            )

        return Response(EventSerializer(replacement).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="edit-following")
    def edit_following(self, request: Request, pk: Any = None) -> Response:
        """Edit this occurrence and all following ones.

        Truncates the original recurring event's RRULE using UNTIL,
        then creates a new recurring event from the given occurrence onward.
        """
        recurring = self.get_object()
        if not recurring.recurrence_rule:
            return Response(
                {"detail": "Event is not recurring."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        original_start_raw = request.data.get("original_start")
        if not original_start_raw:
            return Response(
                {"detail": "original_start is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            # Truncate original rule to end before this occurrence
            until_stamp = original_start_raw.replace(":", "").replace("-", "").split(".")[0] + "Z"
            truncated_rule = self._append_until(recurring.recurrence_rule, until_stamp)
            Event.objects.filter(pk=recurring.pk).update(recurrence_rule=truncated_rule)

            # Create the new tail recurring event
            new_data = {**request.data}
            new_data.pop("original_start", None)
            new_data["parent_event"] = recurring.pk

            serializer = EventSerializer(data=new_data)
            serializer.is_valid(raise_exception=True)
            new_event = serializer.save()
            self._update_etag(new_event)

        return Response(EventSerializer(new_event).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch"], url_path="edit-all")
    def edit_all(self, request: Request, pk: Any = None) -> Response:
        """Edit all occurrences of a recurring event in place."""
        event = self.get_object()
        serializer = EventSerializer(event, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        self._update_etag(updated)
        return Response(EventSerializer(updated).data)

    @staticmethod
    def _append_until(rrule: str, until_stamp: str) -> str:
        """Append or replace the UNTIL clause on an RRULE string."""
        parts = [p for p in rrule.split(";") if not p.startswith("UNTIL=")]
        parts.append(f"UNTIL={until_stamp}")
        return ";".join(parts)


class CalendarSubscriptionViewSet(viewsets.ModelViewSet):
    """CRUD for iCal URL subscriptions.

    Each subscription points to an external .ics feed that is periodically
    fetched by a Celery beat task.  Imported events appear as read-only
    background events on the member's calendar.
    """

    serializer_class = CalendarSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CalendarSubscription.objects.filter(
            member__user=self.request.user,
        ).order_by("display_name")

    def perform_create(self, serializer: CalendarSubscriptionSerializer) -> None:
        from circles.models import CircleMember

        member = CircleMember.objects.get(user=self.request.user)
        serializer.save(member=member)

    @action(detail=True, methods=["post"], url_path="refresh")
    def refresh(self, request: Request, pk: Any = None) -> Response:
        """Trigger an immediate refresh of this subscription."""
        subscription = self.get_object()
        from .tasks import refresh_single_subscription

        refresh_single_subscription.delay(subscription.pk)
        return Response({"detail": "Refresh queued."}, status=status.HTTP_202_ACCEPTED)


class GoogleCalendarSyncViewSet(viewsets.ModelViewSet):
    """CRUD for Google Calendar sync configurations.

    Scoped to the authenticated user's circle memberships.  Provides a
    ``sync-now`` custom action to trigger an immediate sync cycle.
    """

    serializer_class = GoogleCalendarSyncSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return GoogleCalendarSync.objects.filter(
            member__user=self.request.user,
        ).select_related("ase_calendar", "member").order_by("-created_at")

    def perform_create(self, serializer: GoogleCalendarSyncSerializer) -> None:
        from circles.models import CircleMember

        member = CircleMember.objects.get(user=self.request.user)
        serializer.save(member=member)

    @action(detail=True, methods=["post"], url_path="sync-now")
    def sync_now(self, request: Request, pk: Any = None) -> Response:
        """Trigger an immediate sync for this configuration."""
        sync_config = self.get_object()
        if not sync_config.enabled:
            return Response(
                {"detail": "Sync configuration is disabled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from .tasks import sync_google_calendars_single

        sync_google_calendars_single.delay(sync_config.pk)
        return Response(
            {"detail": "Google Calendar sync queued."},
            status=status.HTTP_202_ACCEPTED,
        )


class IcsImportView(APIView):
    """Two-step .ics file import: preview then confirm.

    POST with multipart form-data including an `ics_file` field returns a
    preview list.  POST with JSON body containing `ics_payload` + `uids` +
    `calendar_id` performs the actual import.
    """

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request: Request) -> Response:
        if "ics_file" in request.FILES:
            return self._handle_preview(request)
        return self._handle_confirm(request)

    def _handle_preview(self, request: Request) -> Response:
        ics_file = request.FILES["ics_file"]
        try:
            raw = ics_file.read().decode("utf-8")
        except UnicodeDecodeError:
            return Response(
                {"detail": "File must be UTF-8 encoded."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            parsed_events = events_from_ics(raw)
        except Exception as exc:
            logger.warning("ICS parse error: %s", exc)
            return Response(
                {"detail": f"Could not parse iCalendar data: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        preview_items = []
        for ev_data in parsed_events:
            temp_event = Event(
                start_at=ev_data["start_at"],
                end_at=ev_data["end_at"],
                calendar_id=None,
            )
            conflicts = detect_conflicts(temp_event, calendar_scope=None)
            preview_items.append(
                {
                    "uid": ev_data.get("uid", ""),
                    "title": ev_data.get("title", ""),
                    "start_at": ev_data["start_at"],
                    "end_at": ev_data["end_at"],
                    "all_day": ev_data.get("all_day", False),
                    "recurrence_rule": ev_data.get("recurrence_rule"),
                    "conflict": conflicts.exists(),
                }
            )

        serializer = IcsImportPreviewSerializer(preview_items, many=True)
        return Response(
            {"preview": serializer.data, "ics_payload": raw},
            status=status.HTTP_200_OK,
        )

    def _handle_confirm(self, request: Request) -> Response:
        serializer = IcsImportConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            calendar = Calendar.objects.get(
                pk=data["calendar_id"],
                owner__user=request.user,
            )
        except Calendar.DoesNotExist:
            return Response(
                {"detail": "Calendar not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            parsed_events = events_from_ics(data["ics_payload"])
        except Exception as exc:
            return Response(
                {"detail": f"Could not parse iCalendar data: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        allowed_uids = set(data["uids"])
        created = []
        with transaction.atomic():
            for ev_data in parsed_events:
                if ev_data.get("uid") not in allowed_uids:
                    continue
                event = Event.objects.create(
                    calendar=calendar,
                    title=ev_data.get("title", ""),
                    description=ev_data.get("description", ""),
                    location=ev_data.get("location", ""),
                    start_at=ev_data["start_at"],
                    end_at=ev_data["end_at"],
                    all_day=ev_data.get("all_day", False),
                    recurrence_rule=ev_data.get("recurrence_rule"),
                    caldav_raw=ev_data.get("raw", ""),
                )
                etag_source = f"{event.uid}{event.updated_at.isoformat()}"
                event.etag = hashlib.md5(etag_source.encode()).hexdigest()  # noqa: S324
                event.save(update_fields=["etag"])
                created.append(event)

        return Response(
            EventSerializer(created, many=True).data,
            status=status.HTTP_201_CREATED,
        )


class IcsExportView(APIView):
    """Export all events of a calendar as an .ics file."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request, calendar_id: int) -> HttpResponse:
        try:
            calendar = Calendar.objects.get(
                pk=calendar_id,
                owner__user=request.user,
            )
        except Calendar.DoesNotExist:
            return Response(
                {"detail": "Calendar not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        events = Event.objects.filter(calendar=calendar).prefetch_related("reminders")
        lines: list[str] = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            f"PRODID:-//Ase//{calendar.name}//EN",
            f"X-WR-CALNAME:{calendar.name}",
            f"X-WR-TIMEZONE:UTC",
        ]
        for event in events:
            lines.append(event_to_ics(event))

        lines.append("END:VCALENDAR")
        ics_content = "\r\n".join(lines)

        response = HttpResponse(ics_content, content_type="text/calendar; charset=utf-8")
        safe_name = "".join(c if c.isalnum() else "_" for c in calendar.name)
        response["Content-Disposition"] = f'attachment; filename="{safe_name}.ics"'
        return response
