from __future__ import annotations

from django.urls import path

from . import views

app_name = "iam"

urlpatterns = [
    # ------------------------------------------------------------------
    # OIDC flow
    # ------------------------------------------------------------------
    path("oidc/login/", views.OIDCLoginView.as_view(), name="oidc-login"),
    path("oidc/callback/", views.OIDCCallbackView.as_view(), name="oidc-callback"),
    path("oidc/logout/", views.OIDCLogoutView.as_view(), name="oidc-logout"),
    # ------------------------------------------------------------------
    # App-specific passwords
    # ------------------------------------------------------------------
    path(
        "app-passwords/",
        views.AppPasswordListCreateView.as_view(),
        name="app-password-list",
    ),
    path(
        "app-passwords/<int:pk>/",
        views.AppPasswordDetailView.as_view(),
        name="app-password-detail",
    ),
    path(
        "app-passwords/verify/",
        views.AppPasswordVerifyView.as_view(),
        name="app-password-verify",
    ),
    # ------------------------------------------------------------------
    # External IdPs (admin only)
    # ------------------------------------------------------------------
    path(
        "external-idps/",
        views.TrustedIdPListCreateView.as_view(),
        name="external-idp-list",
    ),
    path(
        "external-idps/<int:pk>/",
        views.TrustedIdPDetailView.as_view(),
        name="external-idp-detail",
    ),
    # ------------------------------------------------------------------
    # Invite flow
    # ------------------------------------------------------------------
    path("invite/<str:token>/", views.InviteAcceptView.as_view(), name="invite-accept"),
]
