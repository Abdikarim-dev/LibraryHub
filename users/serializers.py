from rest_framework import serializers

from .models import User
from .services import (
    change_password,
    logout,
    register_user,
    request_password_reset,
    reset_password,
)

DEFAULT_PROFILE_IMAGE = (
    "https://i.pinimg.com/736x/18/38/2c/"
    "18382c2de91724da8dd0348722e42e2b.jpg"
)


def _resolve_profile_image(obj, request):
    if obj.profile_image:
        url = obj.profile_image.url
        if request is not None:
            return request.build_absolute_uri(url)
        return url
    return DEFAULT_PROFILE_IMAGE


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=1)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
        ]

    def create(self, validated_data):
        return register_user(
            validated_data=validated_data,
            request=self.context.get("request"),
        )


class UserProfileSerializer(serializers.ModelSerializer):
    profile_image = serializers.ImageField(
        required=False,
        allow_null=True,
        write_only=True,
    )
    profile_image_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "phone_number",
            "profile_image",
            "profile_image_url",
            "email_verified",
            "is_active",
            "date_joined",
        ]
        read_only_fields = [
            "id",
            "username",
            "role",
            "email_verified",
            "is_active",
            "date_joined",
        ]

    def get_profile_image_url(self, obj):
        return _resolve_profile_image(obj, self.context.get("request"))

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Backward-compatible key clients already use
        data["profile_image"] = data.pop("profile_image_url", None)
        return data


class UserSerializer(serializers.ModelSerializer):
    profile_image = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "phone_number",
            "profile_image",
            "email_verified",
            "is_active",
            "deleted_at",
            "date_joined",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "username",
            "email_verified",
            "deleted_at",
            "date_joined",
            "created_at",
            "updated_at",
        ]

    def get_profile_image(self, obj):
        return _resolve_profile_image(obj, self.context.get("request"))


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "profile_image",
        ]


class RoleUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=User.Role.choices)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def save(self, **kwargs):
        return change_password(
            user=self.context["request"].user,
            old_password=self.validated_data["old_password"],
            new_password=self.validated_data["new_password"],
        )


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def save(self, **kwargs):
        return request_password_reset(
            email=self.validated_data["email"],
            request=self.context.get("request"),
        )


class ResetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)

    def save(self, **kwargs):
        return reset_password(
            uid=self.context["uid"],
            token=self.context["token"],
            new_password=self.validated_data["password"],
        )


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def save(self, **kwargs):
        logout(refresh_token=self.validated_data["refresh"])
