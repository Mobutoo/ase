from __future__ import annotations

from django.db import transaction
from rest_framework import serializers

from .models import (
    Calendar,
    CalendarSubscription,
    Event,
    EventException,
    EventReminder,
    GoogleCalendarSync,
)


class EventReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventReminder
        fields = [
            "id",
            "member",
            "offset_minutes",
            "channel",
            "sent_at",
            "created_at",
        ]
        read_only_fields = ["id", "sent_at", "created_at"]


class EventExceptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventException
        fields = [
            "id",
            "recurring_event",
            "original_start",
            "replacement_event",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class MemberSummarySerializer(serializers.Serializer):
    """Lightweight read-only serializer for members nested inside events."""

    id = serializers.IntegerField(source="pk")
    display_name = serializers.CharField()
    avatar_color = serializers.CharField()
    avatar_emoji = serializers.CharField()
    role = serializers.CharField()


class EventSerializer(serializers.ModelSerializer):
    reminders = EventReminderSerializer(many=True, required=False)

    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id",
            "uid",
            "calendar",
            "parent_event",
            "title",
            "description",
            "location",
            "start_at",
            "end_at",
            "all_day",
            "event_type",
            "display_mode",
            "visibility",
            "recurrence_rule",
            "members",
            "linked_task",
            "dependent_type",
            "booking_ref",
            "validated_by",
            "validated_at",
            "etag",
            "subscription",
            "ical_uid",
            "google_event_id",
            "is_subscribed",
            "reminders",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "uid",
            "etag",
            "subscription",
            "ical_uid",
            "google_event_id",
            "is_subscribed",
            "validated_by",
            "validated_at",
            "created_at",
            "updated_at",
        ]

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        if request is not None:
            user = request.user
            fields["calendar"].queryset = Calendar.objects.filter(owner__user=user)
            fields["parent_event"].queryset = Event.objects.filter(calendar__owner__user=user)
            fields["linked_task"].queryset = fields["linked_task"].queryset.filter(user=user)
            fields["members"].child_relation.queryset = fields["members"].child_relation.queryset.filter(
                circle__members__user=user
            ).distinct()
        return fields

    def get_is_subscribed(self, obj: Event) -> bool:
        return obj.subscription_id is not None

    def to_representation(self, instance: Event) -> dict:
        """Override to return full member objects instead of just PKs."""
        data = super().to_representation(instance)
        data["members"] = MemberSummarySerializer(
            instance.members.all(), many=True
        ).data
        return data

    def validate(self, attrs: dict) -> dict:
        calendar = attrs.get("calendar", self.instance.calendar if self.instance else None)
        if calendar is not None:
            members = attrs.get("members", self.instance.members.all() if self.instance else [])
            if any(member.circle_id != calendar.owner.circle_id for member in members):
                raise serializers.ValidationError({"members": "Members must belong to the calendar's circle."})
            reminders = attrs.get("reminders", (
                [{"member": reminder.member} for reminder in self.instance.reminders.select_related("member")]
                if self.instance else []
            ))
            if any(reminder["member"].circle_id != calendar.owner.circle_id for reminder in reminders):
                raise serializers.ValidationError({"reminders": "Reminder recipients must belong to the calendar's circle."})
            parent = attrs.get("parent_event", self.instance.parent_event if self.instance else None)
            if parent and parent.calendar_id != calendar.pk:
                raise serializers.ValidationError({"parent_event": "Parent event must belong to the same calendar."})
        start_at = attrs.get("start_at") or (
            self.instance.start_at if self.instance else None
        )
        end_at = attrs.get("end_at") or (
            self.instance.end_at if self.instance else None
        )
        if start_at and end_at and end_at <= start_at:
            raise serializers.ValidationError(
                {"end_at": "end_at must be after start_at."}
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data: dict) -> Event:
        reminders_data = validated_data.pop("reminders", [])
        members_data = validated_data.pop("members", [])
        event = Event.objects.create(**validated_data)
        event.members.set(members_data)
        for reminder_data in reminders_data:
            EventReminder.objects.create(event=event, **reminder_data)
        return event

    @transaction.atomic
    def update(self, instance: Event, validated_data: dict) -> Event:
        reminders_data = validated_data.pop("reminders", None)
        members_data = validated_data.pop("members", None)

        # Regenerate ICS after REST edits instead of returning stale imported text.
        instance.caldav_raw = ""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if members_data is not None:
            instance.members.set(members_data)

        if reminders_data is not None:
            instance.reminders.all().delete()
            for reminder_data in reminders_data:
                EventReminder.objects.create(event=instance, **reminder_data)

        return instance


class EventWriteSerializer(EventSerializer):
    """Serializer used for write operations — omits etag and uid (read-only)."""

    class Meta(EventSerializer.Meta):
        read_only_fields = EventSerializer.Meta.read_only_fields


class CalendarSerializer(serializers.ModelSerializer):
    event_count = serializers.SerializerMethodField()

    class Meta:
        model = Calendar
        fields = [
            "id",
            "owner",
            "name",
            "color",
            "icon",
            "visibility",
            "caldav_enabled",
            "event_count",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_fields(self):
        fields = super().get_fields()
        fields["owner"].required = False
        request = self.context.get("request")
        if request is not None:
            fields["owner"].queryset = fields["owner"].queryset.filter(user=request.user)
        return fields

    def validate_owner(self, owner):
        if self.instance is not None and owner.pk != self.instance.owner_id:
            raise serializers.ValidationError("Calendar ownership cannot be changed.")
        return owner

    def get_event_count(self, obj: Calendar) -> int:
        return obj.events.count()


class CalendarSubscriptionSerializer(serializers.ModelSerializer):
    imported_event_count = serializers.SerializerMethodField()

    class Meta:
        model = CalendarSubscription
        fields = [
            "id",
            "member",
            "display_name",
            "ical_url",
            "color",
            "refresh_minutes",
            "last_fetched_at",
            "last_etag",
            "enabled",
            "imported_event_count",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "member",
            "last_fetched_at",
            "last_etag",
            "imported_event_count",
            "created_at",
        ]

    def get_imported_event_count(self, obj: CalendarSubscription) -> int:
        return obj.imported_events.count()


class IcsImportPreviewSerializer(serializers.Serializer):
    """Used to represent a single event extracted from an .ics file during preview."""

    uid = serializers.CharField(read_only=True)
    title = serializers.CharField(read_only=True)
    start_at = serializers.DateTimeField(read_only=True)
    end_at = serializers.DateTimeField(read_only=True)
    all_day = serializers.BooleanField(read_only=True)
    recurrence_rule = serializers.CharField(read_only=True, allow_null=True)
    conflict = serializers.BooleanField(read_only=True)


class IcsImportConfirmSerializer(serializers.Serializer):
    """Payload to confirm import after preview."""

    calendar_id = serializers.IntegerField()
    uids = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False,
        help_text="List of event UIDs to import from the uploaded .ics payload.",
    )
    ics_payload = serializers.CharField(
        help_text="Raw iCalendar data (previously parsed in the preview step).",
    )


class GoogleCalendarSyncSerializer(serializers.ModelSerializer):
    """Serializer for Google Calendar sync configurations.

    ``member`` is read-only and automatically set from the authenticated user.
    ``sync_token`` and ``last_synced_at`` are read-only sync-state fields.
    """

    class Meta:
        model = GoogleCalendarSync
        fields = [
            "id",
            "member",
            "ase_calendar",
            "google_calendar_id",
            "google_account_email",
            "sync_token",
            "last_synced_at",
            "enabled",
            "sync_direction",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "member",
            "sync_token",
            "last_synced_at",
            "created_at",
        ]

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        if request is not None:
            fields["ase_calendar"].queryset = Calendar.objects.filter(owner__user=request.user)
        return fields

    def validate_ase_calendar(self, calendar):
        if self.instance is not None and calendar.owner_id != self.instance.member_id:
            raise serializers.ValidationError("The calendar must belong to this sync's member.")
        return calendar
