from rest_framework import serializers
from .models import User

from rest_framework_simplejwt.tokens import RefreshToken

from .utils import send_verification_email

from django.contrib.auth.password_validation import (
    validate_password
)

from django.contrib.auth import get_user_model

from .utils import (
    send_password_reset_email
)

class RegisterSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True
    )


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

        user = User.objects.create_user(
            **validated_data
        )


        user.email_verified = False
        user.save()


        request = self.context.get(
            "request"
        )

        send_verification_email(
            user,
            request
        )


        return user
  
class UserProfileSerializer(serializers.ModelSerializer):

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
            "date_joined",
        ]

        read_only_fields = [
            "id",
            "username",
            "role",
            "date_joined",
        ]
        


class ChangePasswordSerializer(
    serializers.Serializer
):

    old_password = serializers.CharField(
        write_only=True
    )


    new_password = serializers.CharField(
        write_only=True,
        validators=[
            validate_password
        ]
    )


    def validate_old_password(
        self,
        value
    ):

        user = self.context["request"].user


        if not user.check_password(value):

            raise serializers.ValidationError(
                "Old password is incorrect"
            )


        return value


    def save(self):

        user = self.context["request"].user


        user.set_password(
            self.validated_data["new_password"]
        )


        user.save()


        return user     

from django.contrib.auth import get_user_model

from .utils import (
    send_password_reset_email
)
User = get_user_model()

class ForgotPasswordSerializer(
    serializers.Serializer
):

    email = serializers.EmailField()


    def validate_email(
        self,
        value
    ):

        try:

            user = User.objects.get(
                email=value
            )

            self.user = user


        except User.DoesNotExist:

            raise serializers.ValidationError(
                "No account found with this email"
            )


        return value


    def save(self):

        send_password_reset_email(
            self.user
        )  

class ResetPasswordSerializer(
    serializers.Serializer
):

    password = serializers.CharField(
        write_only=True,
        validators=[
            validate_password
        ]
    )


    def save(self):

        user = self.context["user"]


        user.set_password(
            self.validated_data["password"]
        )


        user.save()


        return user
      
class LogoutSerializer(serializers.Serializer):

    refresh = serializers.CharField()


    def validate(self, attrs):

        self.token = attrs["refresh"]

        return attrs


    def save(self):

        try:

            token = RefreshToken(
                self.token
            )

            token.blacklist()

        except Exception:

            raise serializers.ValidationError(
                "Invalid refresh token"
            )