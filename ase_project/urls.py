"""Ase URL Configuration."""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
import os


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


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("accounts/", include("allauth.urls")),
    # Legacy app views (profile, etc.)
    path("legacy/", include("app.urls")),
    # React SPA — catch all remaining routes
    re_path(r"^(?!admin|api|accounts|static|legacy).*$", serve_react),
]

# Serve static files in DEBUG mode (dev/preprod)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
