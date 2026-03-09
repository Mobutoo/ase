from __future__ import annotations

from rest_framework import serializers

from circles.models import Circle, CircleMember, CIRCLE_PRESET_CHOICES, PRESET_ROLES


# ---------------------------------------------------------------------------
# Circle serializers
# ---------------------------------------------------------------------------

class CircleSerializer(serializers.ModelSerializer):
    """Full read/write serializer for Circle instances."""

    member_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Circle
        fields = [
            "id",
            "name",
            "preset",
            "tenant_id",
            "is_primary",
            "timezone",
            "agent_enabled",
            "agent_budget_limit",
            "created_at",
            "member_count",
        ]
        read_only_fields = ["id", "created_at", "member_count"]

    def get_member_count(self, obj: Circle) -> int:
        return obj.members.count()

    def validate_preset(self, value: str) -> str:
        valid = [c[0] for c in CIRCLE_PRESET_CHOICES]
        if value not in valid:
            raise serializers.ValidationError(
                f"Invalid preset '{value}'. Valid choices: {valid}"
            )
        return value

    def validate(self, attrs: dict) -> dict:
        # Enforce at most one primary circle per tenant at creation time.
        # On update the database constraint will catch violations too.
        if attrs.get("is_primary"):
            tenant_id = attrs.get(
                "tenant_id",
                getattr(self.instance, "tenant_id", None),
            )
            qs = Circle.objects.filter(tenant_id=tenant_id, is_primary=True)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"is_primary": "A primary circle already exists for this tenant."}
                )
        return attrs


class CircleCreateSerializer(CircleSerializer):
    """Serializer used when creating a circle.

    ``tenant_id`` is injected from the authenticated user so it cannot be
    spoofed via the request body.
    """

    class Meta(CircleSerializer.Meta):
        read_only_fields = CircleSerializer.Meta.read_only_fields + ["tenant_id"]

    def create(self, validated_data: dict) -> Circle:
        request = self.context["request"]
        validated_data["tenant_id"] = str(request.user.pk)
        return Circle.objects.create(**validated_data)


# ---------------------------------------------------------------------------
# CircleMember serializers
# ---------------------------------------------------------------------------

class CircleMemberSerializer(serializers.ModelSerializer):
    """Full serializer for CircleMember — used for list/retrieve."""

    username = serializers.CharField(source="user.username", read_only=True)
    circle_name = serializers.CharField(source="circle.name", read_only=True)

    class Meta:
        model = CircleMember
        fields = [
            "id",
            "user",
            "username",
            "circle",
            "circle_name",
            "role",
            "display_name",
            "avatar_color",
            "avatar_emoji",
            "invite_token",
            "invite_accepted_at",
            "membership_type",
            "external_issuer",
            "external_sub",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "username",
            "circle_name",
            "invite_token",
            "invite_accepted_at",
            "created_at",
        ]

    def validate_role(self, value: str) -> str:
        circle = self.context.get("circle") or (
            self.instance.circle if self.instance else None
        )
        if circle is not None:
            allowed = PRESET_ROLES.get(circle.preset, ())
            if value not in allowed:
                raise serializers.ValidationError(
                    f"Role '{value}' is not allowed for preset '{circle.preset}'. "
                    f"Allowed: {list(allowed)}"
                )
        return value

    def validate_avatar_color(self, value: str) -> str:
        if not value.startswith("#") or len(value) != 7:
            raise serializers.ValidationError(
                "avatar_color must be a 7-character hex string (e.g. '#E76F51')."
            )
        return value


class CircleMemberUpdateRoleSerializer(serializers.ModelSerializer):
    """Minimal serializer for patching a member's role (and display name)."""

    class Meta:
        model = CircleMember
        fields = ["role", "display_name", "avatar_color", "avatar_emoji"]

    def validate_role(self, value: str) -> str:
        circle = self.instance.circle if self.instance else None
        if circle is not None:
            allowed = PRESET_ROLES.get(circle.preset, ())
            if value not in allowed:
                raise serializers.ValidationError(
                    f"Role '{value}' is not allowed for preset '{circle.preset}'. "
                    f"Allowed: {list(allowed)}"
                )
        return value


# ---------------------------------------------------------------------------
# Invite serializers
# ---------------------------------------------------------------------------

class InviteCreateSerializer(serializers.Serializer):
    """Input for generating an invite link for a new member."""

    email = serializers.EmailField(required=False, allow_blank=True)
    role = serializers.CharField(max_length=20)
    display_name = serializers.CharField(max_length=100)
    avatar_color = serializers.CharField(max_length=7, default="#E76F51")
    avatar_emoji = serializers.CharField(max_length=10, default="", allow_blank=True)

    def validate_role(self, value: str) -> str:
        circle = self.context.get("circle")
        if circle is not None:
            allowed = PRESET_ROLES.get(circle.preset, ())
            if value not in allowed:
                raise serializers.ValidationError(
                    f"Role '{value}' is not allowed for preset '{circle.preset}'. "
                    f"Allowed: {list(allowed)}"
                )
        return value

    def validate_avatar_color(self, value: str) -> str:
        if not value.startswith("#") or len(value) != 7:
            raise serializers.ValidationError(
                "avatar_color must be a 7-character hex string (e.g. '#E76F51')."
            )
        return value


class InviteAcceptSerializer(serializers.Serializer):
    """Input for accepting an invite token (resolves to a CircleMember)."""

    token = serializers.CharField(max_length=512)
