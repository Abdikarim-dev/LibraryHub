# from django.shortcuts import render

# Create your views here.

from rest_framework_simplejwt.views import (
    TokenObtainPairView
)

from .authentication import (
    CustomTokenObtainPairSerializer
)


class LoginView(TokenObtainPairView):

    serializer_class = (
        CustomTokenObtainPairSerializer
    )

from django.shortcuts import get_object_or_404
from rest_framework.views import APIView

from .models import User
from .tokens import email_verification_token

from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated

from .serializers import (
    RegisterSerializer,
    UserProfileSerializer
)



class RegisterView(generics.CreateAPIView):

    serializer_class = RegisterSerializer

    permission_classes = [
        AllowAny
    ]


    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(
            data=request.data
        )


        serializer.is_valid(
            raise_exception=True
        )


        user = serializer.save()


        return Response(
            {
                "message": "User created successfully",
                "username": user.username
            },
            status=status.HTTP_201_CREATED
        )

class VerifyEmailView(APIView):

    permission_classes = []


    def get(
        self,
        request,
        uid,
        token
    ):

        user = get_object_or_404(
            User,
            id=uid
        )


        if email_verification_token.check_token(
            user,
            token
        ):

            user.email_verified = True
            user.save()


            return Response(
                {
                    "message":
                    "Email verified successfully"
                }
            )


        return Response(
            {
                "error":
                "Invalid or expired token"
            },
            status=400
        )
        

class ProfileView(RetrieveUpdateAPIView):

    serializer_class = UserProfileSerializer

    permission_classes = [
        IsAuthenticated
    ]


    def get_object(self):

        return self.request.user