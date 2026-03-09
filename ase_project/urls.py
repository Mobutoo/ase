"""Ase URL Configuration."""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.http import HttpResponse
from django.views.static import serve as static_serve
import os

from calendars.urls import caldav_urlpatterns


def serve_react(request):
    """Serve the React SPA index.html."""
    index_path = os.path.join(settings.STATIC_ROOT, "frontend", "index.html")
    try:
        with open(index_path, "r") as f:
            return HttpResponse(f.read(), content_type="text/html")
    except FileNotFoundError:
        return HttpResponse(
            "Frontend not built. Run: cd frontend && npm run build", status=503
        )


def serve_asset(request, path):
    """Serve Vite build assets from staticfiles/frontend/assets/."""
    return static_serve(
        request, path, document_root=os.path.join(settings.STATIC_ROOT, "frontend", "assets")
    )


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("accounts/", include("allauth.urls")),
    # Vite assets (JS, CSS, fonts)
    re_path(r"^assets/(?P<path>.*)$", serve_asset),
    # Django static files (admin CSS, legacy)
    re_path(r"^static/(?P<path>.*)$", static_serve, {"document_root": settings.STATIC_ROOT}),
    # Ase v3 new apps
    path("api/", include("circles.urls")),
    path("api/calendar/", include("calendars.urls")),
    path("api/circles/<int:circle_pk>/agents/", include("agents.urls")),
    path("oidc/", include("mozilla_django_oidc.urls")),
    path("iam/", include("iam.urls", namespace="iam")),
    path("caldav/", include((caldav_urlpatterns, "caldav"))),
    # Legacy app views (profile, etc.)
    path("legacy/", include("app.urls")),
    # React SPA — catch all remaining routes (MUST be last)
    re_path(r"^(?!admin|api|accounts|static|assets|legacy|oidc|iam|caldav).*$", serve_react),
]
