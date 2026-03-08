from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from .viewsets import (
    SessionViewSet,
    LocalTaskViewSet,
    EnergyReadingViewSet,
    UserSettingsViewSet,
)

# DRF router for v1 API
router = DefaultRouter()
router.register(r"sessions", SessionViewSet, basename="session")
router.register(r"tasks", LocalTaskViewSet, basename="localtask")
router.register(r"energy", EnergyReadingViewSet, basename="energyreading")

urlpatterns = [
    # Health check
    path("v1/health/", views.health, name="health"),

    # Ase v1 API (DRF)
    path("v1/", include(router.urls)),

    # Settings (custom routing — singleton, no pk)
    path(
        "v1/settings/",
        UserSettingsViewSet.as_view({"get": "list", "patch": "partial_update"}),
        name="user-settings",
    ),

    # Legacy PomoTracker API (kept for compatibility)
    path("<str:username>/alltags", views.getAllUserTags),
    path("<str:username>/alldates", views.getAllUserPomosDates),
    path("<str:username>/allpomodoros", views.getAllUserPomodoros),
    path("leaderboard", views.getAllPomodoros),
    path("<str:token>/getSettings", views.getSettings),
    path("<str:token>/create", views.create, name="create"),
    path("<str:token>/<int:pomodoro_id>", views.updateDelete),
    path("<str:token>/updateTag/<str:tag_to_replace>", views.updateTags),
    path("<str:token>/settings", views.updateSettings),
]
