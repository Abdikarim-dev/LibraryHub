from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework_simplejwt.views import TokenObtainPairView

from common.responses import message_response
from .authentication import CustomTokenObtainPairSerializer
from .models import User
from .permissions import IsAdmin, IsAdminOrLibrarian
from .serializers import (
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    LogoutSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    RoleUpdateSerializer,
    UserLibrarianSerializer,
    UserProfileSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from .services import (
    activate_user,
    deactivate_user,
    set_user_role,
    soft_delete_user,
    update_user,
    verify_email,
)
from .throttles import AuthRateThrottle


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return message_response(
            "User created successfully",
            http_status=status.HTTP_201_CREATED,
            username=user.username,
        )


class VerifyEmailView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def get(self, request, uid, token):
        verify_email(uid=uid, token=token)
        return message_response("Email verified successfully")


class ProfileView(RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return message_response("Password changed successfully")


class ForgotPasswordView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = ForgotPasswordSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return message_response("Password reset email sent")


class ResetPasswordView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request, uid, token):
        serializer = ResetPasswordSerializer(
            data=request.data,
            context={"uid": uid, "token": token},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return message_response("Password reset successfully")


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return message_response("Successfully logged out")


class UserViewSet(viewsets.ModelViewSet):
    """
    Admin/Librarian user management.

    list/retrieve: Admin or Librarian
    update/partial_update/destroy/role/activate/deactivate: Admin only
    """

    http_method_names = ["get", "patch", "delete", "head", "options"]
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        if self.action == "set_role":
            return RoleUpdateSerializer
        if self.action in ("list", "retrieve"):
            if (
                self.request.user.is_authenticated
                and self.request.user.role == User.Role.ADMIN
            ):
                return UserSerializer
            return UserLibrarianSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAdminOrLibrarian()]
        return [IsAdmin()]

    def partial_update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = update_user(
            actor=request.user,
            user=user,
            validated_data=serializer.validated_data,
            request=request,
        )
        return Response(UserSerializer(updated, context={"request": request}).data)

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        soft_delete_user(actor=request.user, user=user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["patch"], url_path="role")
    def set_role(self, request, pk=None):
        user = self.get_object()
        serializer = RoleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = set_user_role(
            actor=request.user,
            user=user,
            role=serializer.validated_data["role"],
        )
        return Response(UserSerializer(updated, context={"request": request}).data)

    @action(detail=True, methods=["patch"], url_path="activate")
    def activate(self, request, pk=None):
        user = self.get_object()
        updated = activate_user(actor=request.user, user=user)
        return Response(UserSerializer(updated, context={"request": request}).data)

    @action(detail=True, methods=["patch"], url_path="deactivate")
    def deactivate(self, request, pk=None):
        user = self.get_object()
        updated = deactivate_user(actor=request.user, user=user)
        return Response(UserSerializer(updated, context={"request": request}).data)
