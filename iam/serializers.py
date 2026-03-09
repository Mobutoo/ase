from __future__ import annotations

from django.contrib.auth.hashers import make_password
from django.utils import timezone
from rest_framework import serializers

from .models import AppSpecificPassword, CircleInviteToken, OIDCConfig, TrustedExternalIdP


class AppSpecificPasswordCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new app-specific password.

    Accepts ``password`` in plaintext during creation, hashes it with bcrypt,
    and never returns the hash thereafter.
    """

    # Write-only plaintext field — not present on the model.
    password = serializers.CharField(
        write_only=True,
        min_length=12,
        max_length=128,
        style={"input_type": "password"},
        help_text="Plaintext password shown once; stored as bcrypt hash.",
    )

    class Meta:
        model = AppSpecificPassword
        fields = [
            "id",
            "name",
            "password",
            "expires_at",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_expires_at(self, value: object) -> object:
        if value is not None and value <= timezone.now():
            raise serializers.ValidationError("expires_at must be in the future.")
        return value

    def create(self, validated_data: dict) -> AppSpecificPassword:
        raw_password = validated_data.pop("password")
        validated_data["password_hash"] = make_password(raw_password, hasher="bcrypt")
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class AppSpecificPasswordListSerializer(serializers.ModelSerializer):
    """Read-only serializer for listing app-specific passwords.

    The hash is never exposed.
    """

    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = AppSpecificPassword
        fields = [
            "id",
            "name",
            "last_used_at",
            "created_at",
            "expires_at",
            "is_expired",
        ]
        read_only_fields = fields

    def get_is_expired(self, obj: AppSpecificPassword) -> bool:
        return obj.is_expired()


class TrustedExternalIdPSerializer(serializers.ModelSerializer):
    """Serializer for TrustedExternalIdP.

    ``client_secret`` is write-only to prevent leakage.
    """

    client_secret = serializers.CharField(
        write_only=True,
        max_length=500,
        required=False,
        allow_blank=True,
        style={"input_type": "password"},
    )

    class Meta:
        model = TrustedExternalIdP
        fields = [
            "id",
            "issuer_url",
            "client_id",
            "client_secret",
            "display_name",
            "enabled",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class OIDCConfigSerializer(serializers.ModelSerializer):
    """Serializer for OIDCConfig — admin/superuser only.

    ``client_secret`` is write-only.
    """

    client_secret = serializers.CharField(
        write_only=True,
        max_length=500,
        style={"input_type": "password"},
    )

    class Meta:
        model = OIDCConfig
        fields = [
            "id",
            "issuer_url",
            "client_id",
            "client_secret",
            "backend_type",
            "api_url",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class CircleInviteTokenSerializer(serializers.ModelSerializer):
    """Serializer for CircleInviteToken — used by the invite flow."""

    is_valid = serializers.SerializerMethodField()

    class Meta:
        model = CircleInviteToken
        fields = [
            "id",
            "token",
            "email",
            "circle_id",
            "role",
            "is_valid",
            "expires_at",
            "created_at",
        ]
        read_only_fields = ["id", "token", "created_at", "is_valid"]

    def get_is_valid(self, obj: CircleInviteToken) -> bool:
        return obj.is_valid()
