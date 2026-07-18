# from django.shortcuts import render

# Create your views here.

from rest_framework_simplejwt.views import (
    TokenObtainPairView
)

from .authentication import (
    CustomTokenObtainPairSerializer
)

from .serializers import (
    ChangePasswordSerializer
)

from .serializers import LogoutSerializer

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


class LoginView(TokenObtainPairView):

    serializer_class = (
        CustomTokenObtainPairSerializer
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

    permission_classes = [AllowAny]

    def get(self, request, uid, token):
        # Quoted-printable email wrapping can insert soft-break "=" into long URLs.
        # Django auth tokens never contain "=", so strip those artifacts.
        token = token.replace("=", "")

        user = get_object_or_404(User, id=uid)

        if email_verification_token.check_token(user, token):
            user.email_verified = True
            user.save(update_fields=["email_verified"])

            return Response(
                {"message": "Email verified successfully"}
            )

        return Response(
            {"error": "Invalid or expired token"},
            status=status.HTTP_400_BAD_REQUEST,
        )
        

class ProfileView(RetrieveUpdateAPIView):

    serializer_class = UserProfileSerializer

    permission_classes = [
        IsAuthenticated
    ]


    def get_object(self):

        return self.request.user

class ChangePasswordView(APIView):

    permission_classes = [
        IsAuthenticated
    ]


    def post(self, request):

        serializer = ChangePasswordSerializer(
            data=request.data,
            context={
                "request": request
            }
        )


        serializer.is_valid(
            raise_exception=True
        )


        serializer.save()


        return Response(
            {
                "message":
                "Password changed successfully"
            }
        )

from .serializers import (
    ForgotPasswordSerializer,
)



class ForgotPasswordView(APIView):

    permission_classes = []


    def post(
        self,
        request
    ):

        serializer = (
            ForgotPasswordSerializer(
                data=request.data
            )
        )


        serializer.is_valid(
            raise_exception=True
        )


        serializer.save()


        return Response(
            {
                "message":
                "Password reset email sent"
            }
        )
        
from django.shortcuts import get_object_or_404

from .models import User

from .tokens import (
    password_reset_token
)



class ResetPasswordView(APIView):

    permission_classes = []


    def post(
        self,
        request,
        uid,
        token
    ):

        user = get_object_or_404(
            User,
            id=uid
        )


        if not password_reset_token.check_token(
            user,
            token
        ):

            return Response(
                {
                    "error":
                    "Invalid or expired token"
                },
                status=400
            )


        serializer = ResetPasswordSerializer(
            data=request.data,
            context={
                "user": user
            }
        )


        serializer.is_valid(
            raise_exception=True
        )


        serializer.save()


        return Response(
            {
                "message":
                "Password reset successfully"
            }
        )

class LogoutView(APIView):

    permission_classes = [
        IsAuthenticated
    ]


    def post(self, request):

        serializer = LogoutSerializer(
            data=request.data
        )


        serializer.is_valid(
            raise_exception=True
        )


        serializer.save()


        return Response(
            {
                "message":
                "Successfully logged out"
            },
            status=status.HTTP_205_RESET_CONTENT
        )