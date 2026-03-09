from __future__ import annotations

import logging
import os
import secrets

from django.contrib.auth import login
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from rest_framework import permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AppSpecificPassword, CircleInviteToken, TrustedExternalIdP
from .serializers import (
    AppSpecificPasswordCreateSerializer,
    AppSpecificPasswordListSerializer,
    TrustedExternalIdPSerializer,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OIDC helpers
# ---------------------------------------------------------------------------


class OIDCLoginView(View):
    """Kick off an OIDC authorisation-code flow.

    Stores a ``state`` nonce in the session and redirects to the IdP.
    An optional ``invite`` query param is persisted in the session so the
    authentication backend can act on it after the callback.

    URL: ``GET /iam/oidc/login/``
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        from mozilla_django_oidc.views import OIDCAuthenticationRequestView

        invite_token = request.GET.get("invite")
        if invite_token:
            request.session["iam_invite_token"] = invite_token

        # Delegate to mozilla-django-oidc for the actual redirect.
        return OIDCAuthenticationRequestView.as_view()(request)


class OIDCCallbackView(View):
    """Handle the OIDC authorisation-code callback from the IdP.

    Delegates heavy lifting to mozilla-django-oidc.  On success, the
    authentication backend (see :mod:`iam.backends`) creates the Django user
    and optionally the CircleMember row when an invite token is present.

    URL: ``GET /iam/oidc/callback/``
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        from mozilla_django_oidc.views import OIDCAuthenticationCallbackView

        return OIDCAuthenticationCallbackView.as_view()(request)


class OIDCLogoutView(View):
    """Terminate the local Django session.

    Optionally issues an RP-initiated logout to the IdP if
    ``OIDC_OP_LOGOUT_ENDPOINT`` is configured.

    URL: ``POST /iam/oidc/logout/``
    """

    def post(self, request: HttpRequest) -> HttpResponse:
        from django.contrib.auth import logout as django_logout

        django_logout(request)
        post_logout_url = os.environ.get("OIDC_POST_LOGOUT_REDIRECT_URL", "/")
        return redirect(post_logout_url)


# ---------------------------------------------------------------------------
# App-specific passwords
# ---------------------------------------------------------------------------


class AppPasswordListCreateView(APIView):
    """List or create app-specific passwords for the authenticated user.

    - ``GET  /iam/app-passwords/`` — list (no hashes, safe to display)
    - ``POST /iam/app-passwords/`` — create; returns the plaintext password
      **once** in the response body; it is not recoverable after this call.

    URL: ``/iam/app-passwords/``
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        qs = AppSpecificPassword.objects.filter(user=request.user).order_by("-created_at")
        serializer = AppSpecificPasswordListSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request: Request) -> Response:
        serializer = AppSpecificPasswordCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        # Capture the plaintext before it is hashed.
        raw_password = serializer.validated_data.get("password", "")
        instance = serializer.save()
        return Response(
            {
                "id": instance.pk,
                "name": instance.name,
                "password": raw_password,
                "message": (
                    "Store this password now — it will not be shown again."
                ),
                "created_at": instance.created_at,
                "expires_at": instance.expires_at,
            },
            status=status.HTTP_201_CREATED,
        )


class AppPasswordDetailView(APIView):
    """Retrieve or delete a single app-specific password.

    - ``GET    /iam/app-passwords/{id}/`` — metadata only (no hash)
    - ``DELETE /iam/app-passwords/{id}/`` — revoke

    URL: ``/iam/app-passwords/<int:pk>/``
    """

    permission_classes = [permissions.IsAuthenticated]

    def _get_owned(self, request: Request, pk: int) -> AppSpecificPassword:
        return get_object_or_404(AppSpecificPassword, pk=pk, user=request.user)

    def get(self, request: Request, pk: int) -> Response:
        instance = self._get_owned(request, pk)
        serializer = AppSpecificPasswordListSerializer(instance)
        return Response(serializer.data)

    def delete(self, request: Request, pk: int) -> Response:
        instance = self._get_owned(request, pk)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# CalDAV / Basic-auth gateway helper
# ---------------------------------------------------------------------------


class AppPasswordVerifyView(APIView):
    """Internal endpoint: verify a username + app-specific password pair.

    Used by a reverse proxy (Caddy, nginx) auth_request to gate CalDAV
    access without requiring an OIDC session.

    Returns 200 on success, 401 on failure.

    URL: ``POST /iam/app-passwords/verify/``

    Body (JSON):
        ``{"username": "...", "password": "..."}``

    .. note::
        This view does **not** require the user to be logged in, but it
        should be restricted to internal network calls at the proxy layer.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request: Request) -> Response:
        from django.contrib.auth import get_user_model

        username = request.data.get("username", "").strip()
        raw_password = request.data.get("password", "")

        if not username or not raw_password:
            return Response(
                {"detail": "username and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        User = get_user_model()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        now = timezone.now()
        # Check all non-expired passwords for this user.
        app_passwords = AppSpecificPassword.objects.filter(
            user=user,
        ).filter(
            # expires_at is null (no expiry) OR expires_at > now
            expires_at__isnull=True,
        ) | AppSpecificPassword.objects.filter(
            user=user,
            expires_at__gt=now,
        )

        for app_pw in app_passwords:
            if app_pw.check_password(raw_password):
                app_pw.last_used_at = now
                app_pw.save(update_fields=["last_used_at"])
                return Response(
                    {"detail": "ok", "user_id": user.pk},
                    status=status.HTTP_200_OK,
                )

        return Response(status=status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# Trusted External IdP management (admin/staff only)
# ---------------------------------------------------------------------------


class TrustedIdPListCreateView(APIView):
    """List or register trusted external Identity Providers.

    URL: ``/iam/external-idps/``
    """

    permission_classes = [permissions.IsAdminUser]

    def get(self, request: Request) -> Response:
        qs = TrustedExternalIdP.objects.all().order_by("display_name")
        serializer = TrustedExternalIdPSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request: Request) -> Response:
        serializer = TrustedExternalIdPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TrustedIdPDetailView(APIView):
    """Retrieve, update or delete a trusted external IdP.

    URL: ``/iam/external-idps/<int:pk>/``
    """

    permission_classes = [permissions.IsAdminUser]

    def get(self, request: Request, pk: int) -> Response:
        idp = get_object_or_404(TrustedExternalIdP, pk=pk)
        return Response(TrustedExternalIdPSerializer(idp).data)

    def patch(self, request: Request, pk: int) -> Response:
        idp = get_object_or_404(TrustedExternalIdP, pk=pk)
        serializer = TrustedExternalIdPSerializer(idp, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request: Request, pk: int) -> Response:
        idp = get_object_or_404(TrustedExternalIdP, pk=pk)
        idp.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Invite token
# ---------------------------------------------------------------------------


class InviteAcceptView(View):
    """Store an invite token in the session then redirect to the OIDC login.

    The token is validated by the authentication backend after successful
    OIDC authentication.

    URL: ``GET /iam/invite/<str:token>/``
    """

    def get(self, request: HttpRequest, token: str) -> HttpResponse:
        invite = CircleInviteToken.objects.filter(token=token).first()
        if invite is None or not invite.is_valid():
            return HttpResponse("This invite link is invalid or has expired.", status=410)

        request.session["iam_invite_token"] = token
        oidc_login_url = f"/iam/oidc/login/?invite={token}"
        return redirect(oidc_login_url)
