from __future__ import annotations

from django.contrib import admin

from .models import Calendar, Event, EventException, EventReminder


class EventReminderInline(admin.TabularInline):
    model = EventReminder
    extra = 0
    fields = ["member", "offset_minutes", "channel", "sent_at"]
    readonly_fields = ["sent_at"]


class EventExceptionInline(admin.TabularInline):
    model = EventException
    fk_name = "recurring_event"
    extra = 0
    fields = ["original_start", "replacement_event", "created_at"]
    readonly_fields = ["created_at"]


@admin.register(Calendar)
class CalendarAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "visibility", "caldav_enabled", "created_at"]
    list_filter = ["visibility", "caldav_enabled"]
    search_fields = ["name", "owner__user__username", "owner__user__email"]
    ordering = ["owner__user__username", "name"]


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "calendar",
        "event_type",
        "start_at",
        "end_at",
        "all_day",
        "visibility",
    ]
    list_filter = ["event_type", "visibility", "all_day", "calendar"]
    search_fields = ["title", "description", "uid"]
    readonly_fields = ["uid", "etag", "created_at", "updated_at"]
    raw_id_fields = ["calendar", "parent_event", "linked_task", "validated_by"]
    filter_horizontal = ["members"]
    date_hierarchy = "start_at"
    inlines = [EventReminderInline, EventExceptionInline]
    fieldsets = [
        (
            "Core",
            {
                "fields": [
                    "uid",
                    "calendar",
                    "title",
                    "description",
                    "location",
                    "start_at",
                    "end_at",
                    "all_day",
                    "event_type",
                    "display_mode",
                    "visibility",
                ]
            },
        ),
        (
            "Recurrence",
            {
                "fields": ["recurrence_rule", "parent_event"],
                "classes": ["collapse"],
            },
        ),
        (
            "Relations",
            {
                "fields": ["members", "linked_task"],
                "classes": ["collapse"],
            },
        ),
        (
            "Event Graph",
            {
                "fields": [
                    "dependent_type",
                    "booking_ref",
                    "validated_by",
                    "validated_at",
                ],
                "classes": ["collapse"],
            },
        ),
        (
            "CalDAV",
            {
                "fields": ["etag", "caldav_raw"],
                "classes": ["collapse"],
            },
        ),
        (
            "Timestamps",
            {
                "fields": ["created_at", "updated_at"],
                "classes": ["collapse"],
            },
        ),
    ]


@admin.register(EventException)
class EventExceptionAdmin(admin.ModelAdmin):
    list_display = ["recurring_event", "original_start", "replacement_event", "created_at"]
    raw_id_fields = ["recurring_event", "replacement_event"]
    readonly_fields = ["created_at"]


@admin.register(EventReminder)
class EventReminderAdmin(admin.ModelAdmin):
    list_display = ["event", "member", "offset_minutes", "channel", "sent_at"]
    list_filter = ["channel"]
    raw_id_fields = ["event", "member"]
    readonly_fields = ["created_at"]
