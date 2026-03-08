from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from .viewsets import (
    AISuggestionViewSet,
    EnergyReadingViewSet,
    LocalTaskViewSet,
    SessionViewSet,
    UserSettingsViewSet,
    WebhookViewSet,
)
from .viewsets_phase2 import (
    PlaylistViewSet,
    TaskSourceConfigViewSet,
    UnifiedTaskViewSet,
)
from .viewsets_phase34 import (
    AnalyticsViewSet,
    DailyPlanViewSet,
    EnergyAnalyticsViewSet,
    LeaderboardViewSet,
)

# DRF router for v1 API
router = DefaultRouter()

# Phase 1 — Core
router.register(r"sessions", SessionViewSet, basename="session")
router.register(r"tasks", LocalTaskViewSet, basename="localtask")
router.register(r"energy", EnergyReadingViewSet, basename="energyreading")

# Phase 2 — Task Bridge + Music
router.register(r"unified-tasks", UnifiedTaskViewSet, basename="unifiedtask")
router.register(r"playlists", PlaylistViewSet, basename="playlist")
router.register(r"task-sources", TaskSourceConfigViewSet, basename="tasksource")

# Phase 3+4 — Analytics + Gamification
router.register(r"analytics", AnalyticsViewSet, basename="analytics")
router.register(r"leaderboard", LeaderboardViewSet, basename="leaderboard")
router.register(r"plans", DailyPlanViewSet, basename="dailyplan")
router.register(r"energy-analytics", EnergyAnalyticsViewSet, basename="energyanalytics")

# Phase 5 — AI Copilot
router.register(r"ai/suggestions", AISuggestionViewSet, basename="aisuggestion")
router.register(r"webhooks", WebhookViewSet, basename="webhook")

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
