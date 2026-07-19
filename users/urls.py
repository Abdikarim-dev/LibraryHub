from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    ChangePasswordView,
    ForgotPasswordView,
    LoginView,
    LogoutView,
    ProfileView,
    RegisterView,
    ResetPasswordView,
    UserViewSet,
    VerifyEmailView,
)

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="users")

urlpatterns = [
    # Auth
    path("auth/register/", RegisterView.as_view(), name="register"),
    path(
        "auth/verify-email/<int:uid>/<str:token>/",
        VerifyEmailView.as_view(),
        name="verify-email",
    ),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path(
        "auth/token/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),
    path(
        "auth/forgot-password/",
        ForgotPasswordView.as_view(),
        name="forgot-password",
    ),
    path(
        "auth/reset-password/<int:uid>/<str:token>/",
        ResetPasswordView.as_view(),
        name="reset-password",
    ),
    # Profile (self)
    path("users/profile/", ProfileView.as_view(), name="profile"),
    path(
        "users/change-password/",
        ChangePasswordView.as_view(),
        name="change-password",
    ),
    # User management ViewSet: /users/, /users/{id}/, role, activate, deactivate
    path("", include(router.urls)),
]
