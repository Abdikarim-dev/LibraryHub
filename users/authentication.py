from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):

    def validate(self, attrs):
        data = super().validate(attrs)

        if not self.user.email_verified:
            raise serializers.ValidationError(
                {"detail": "Please verify your email first"}
            )

        if not self.user.is_active:
            raise serializers.ValidationError(
                {"detail": "This account is inactive."}
            )

        return data
