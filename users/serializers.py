from rest_framework import serializers
from .models import User


class RegisterSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True
    )


    class Meta:

        model = User

        fields = [
            "first_name",
            "last_name",
            "username",
            "email",
            "password",
        ]


    def create(self, validated_data):

        user = User.objects.create_user(
            **validated_data
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