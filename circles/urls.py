from __future__ import annotations

"""
URL routing for the circles app.

Mount in the main urls.py with:

    path("api/v1/", include("circles.urls")),

Resulting endpoints
-------------------
GET    /api/v1/circles/                                  list circles
POST   /api/v1/circles/                                  create circle
GET    /api/v1/circles/{id}/                             retrieve circle
PATCH  /api/v1/circles/{id}/                             partial update circle
DELETE /api/v1/circles/{id}/                             delete circle
POST   /api/v1/circles/{id}/invite/                      generate invite token
POST   /api/v1/circles/{id}/accept_invite/               accept invite token

GET    /api/v1/circles/{circle_pk}/members/              list members
GET    /api/v1/circles/{circle_pk}/members/{pk}/         retrieve member
PATCH  /api/v1/circles/{circle_pk}/members/{pk}/         update display_name / avatar
DELETE /api/v1/circles/{circle_pk}/members/{pk}/         remove member
PATCH  /api/v1/circles/{circle_pk}/members/{pk}/role/    change member role (admin-only)
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from circles.views import CircleMemberViewSet, CircleViewSet


# Top-level router for Circle CRUD + custom actions
router = DefaultRouter()
router.register(r"circles", CircleViewSet, basename="circle")

# Manual nested routes for CircleMember (avoids drf-nested-routers dependency)
member_list = CircleMemberViewSet.as_view(
    {
        "get": "list",
    }
)

member_detail = CircleMemberViewSet.as_view(
    {
        "get": "retrieve",
        "patch": "partial_update",
        "delete": "destroy",
    }
)

member_role = CircleMemberViewSet.as_view(
    {
        "patch": "update_role",
    }
)

urlpatterns = [
    # DRF router — circles + invite / accept_invite actions
    path("", include(router.urls)),
    # Nested members endpoints
    path(
        "circles/<int:circle_pk>/members/",
        member_list,
        name="circle-member-list",
    ),
    path(
        "circles/<int:circle_pk>/members/<int:pk>/",
        member_detail,
        name="circle-member-detail",
    ),
    path(
        "circles/<int:circle_pk>/members/<int:pk>/role/",
        member_role,
        name="circle-member-role",
    ),
]
