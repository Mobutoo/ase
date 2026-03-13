from __future__ import annotations

"""URL routing for the calendars app.

REST API endpoints (under /api/calendars/):
    GET/POST   /api/calendars/calendars/
    GET/PUT/PATCH/DELETE /api/calendars/calendars/<pk>/
    GET        /api/calendars/events/
    POST       /api/calendars/events/
    GET/PUT/PATCH/DELETE /api/calendars/events/<pk>/
    GET        /api/calendars/events/<pk>/conflicts/
    POST       /api/calendars/events/<pk>/edit-this/
    POST       /api/calendars/events/<pk>/edit-following/
    PATCH      /api/calendars/events/<pk>/edit-all/
    GET/POST   /api/calendars/subscriptions/
    GET/PUT/PATCH/DELETE /api/calendars/subscriptions/<pk>/
    POST       /api/calendars/subscriptions/<pk>/refresh/
    POST       /api/calendars/ics/import/
    GET        /api/calendars/ics/export/<calendar_id>/

CalDAV endpoints (under /caldav/):
    PROPFIND   /caldav/<username>/
    PROPFIND   /caldav/<username>/<calendar_id>/
    REPORT     /caldav/<username>/<calendar_id>/
    GET/PUT/DELETE /caldav/<username>/<calendar_id>/<uid>.ics

Include this module from the project root urls.py:

    from django.urls import path, include
    ...
    path("api/calendars/", include("calendars.urls")),
    path("caldav/", include("calendars.urls", namespace="caldav")),

Or more granularly (recommended)::

    urlpatterns = [
        ...
        path("api/", include([
            path("calendars/", include("calendars.urls")),
        ])),
        path("caldav/", include("calendars.caldav_urls")),
    ]

This file exposes ``urlpatterns`` for the REST API and ``caldav_urlpatterns``
for the CalDAV protocol layer so that the project can mount them independently.
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CalendarSubscriptionViewSet,
    CalendarViewSet,
    EventViewSet,
    IcsExportView,
    IcsImportView,
)
from .caldav.views import (
    CalDavCalendarView,
    CalDavEventView,
    CalDavRootView,
)

# ---------------------------------------------------------------------------
# REST API router
# ---------------------------------------------------------------------------

router = DefaultRouter()
router.register(r"calendars", CalendarViewSet, basename="calendar")
router.register(r"events", EventViewSet, basename="event")
router.register(r"subscriptions", CalendarSubscriptionViewSet, basename="subscription")

urlpatterns = router.urls + [
    path("ics/import/", IcsImportView.as_view(), name="ics-import"),
    path("ics/export/<int:calendar_id>/", IcsExportView.as_view(), name="ics-export"),
]

# ---------------------------------------------------------------------------
# CalDAV protocol URLs — mount separately at /caldav/
# ---------------------------------------------------------------------------

caldav_urlpatterns = [
    path("<str:username>/", CalDavRootView.as_view(), name="caldav-principal"),
    path(
        "<str:username>/<int:calendar_id>/",
        CalDavCalendarView.as_view(),
        name="caldav-calendar",
    ),
    path(
        "<str:username>/<int:calendar_id>/<str:uid>.ics",
        CalDavEventView.as_view(),
        name="caldav-event",
    ),
]
