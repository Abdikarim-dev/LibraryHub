from rest_framework import serializers
from .models import User

from .utils import send_verification_email

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

# class RegisterSerializer(serializers.ModelSerializer):

#     password = serializers.CharField(
#         write_only=True
#     )


#     class Meta:

#         model = User

#         fields = [
#             "first_name",
#             "last_name",
#             "username",
#             "email",
#             "password",
#         ]


#     def create(self, validated_data):

#         user = User.objects.create_user(
#             **validated_data
#         )

#         return user
    
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