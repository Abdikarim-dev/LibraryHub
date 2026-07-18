from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer
)


class CustomTokenObtainPairSerializer(
    TokenObtainPairSerializer
):

    def validate(self, attrs):

        data = super().validate(attrs)


        if not self.user.email_verified:

            raise Exception(
                "Please verify your email first"
            )


        return data