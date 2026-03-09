from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AgentActionViewSet, MemberPreferenceViewSet, NotificationPreferenceViewSet

app_name = "agents"

# Nested under /circles/<circle_pk>/agents/
router = DefaultRouter()
router.register(r"actions", AgentActionViewSet, basename="agent-action")
router.register(r"preferences", MemberPreferenceViewSet, basename="member-preference")

# NotificationPreference is a singleton per member — no pk in list/detail
# Exposed as a single resource at:  /circles/<circle_pk>/agents/notifications/
notification_detail = NotificationPreferenceViewSet.as_view(
    {
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
    }
)

urlpatterns = [
    path("", include(router.urls)),
    path("notifications/", notification_detail, name="notification-preference"),
]
