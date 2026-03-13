from __future__ import annotations

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
            "created_at",
            "updated_at",
        ]

    def get_is_subscribed(self, obj: Event) -> bool:
        return obj.subscription_id is not None

    def validate(self, attrs: dict) -> dict:
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

    def create(self, validated_data: dict) -> Event:
        reminders_data = validated_data.pop("reminders", [])
        members_data = validated_data.pop("members", [])
        event = Event.objects.create(**validated_data)
        event.members.set(members_data)
        for reminder_data in reminders_data:
            EventReminder.objects.create(event=event, **reminder_data)
        return event

    def update(self, instance: Event, validated_data: dict) -> Event:
        reminders_data = validated_data.pop("reminders", None)
        members_data = validated_data.pop("members", None)

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
        read_only_fields = ["id", "uid", "etag", "created_at", "updated_at"]


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
