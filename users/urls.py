from django.urls import path

from .views import (
    RegisterView,
    ProfileView,
    VerifyEmailView,
    LoginView,
    LogoutView,
    ChangePasswordView,
    ForgotPasswordView,
    ResetPasswordView,
)

from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

urlpatterns = [

    path(
        "auth/register/",
        RegisterView.as_view(),
        name="register"
    ),
    path(
        "auth/verify-email/<int:uid>/<str:token>/",
        VerifyEmailView.as_view(),
        name="verify-email"
    ),
    # path(
    #     "auth/resend-verification/",
    #     ResendVerificationView.as_view(),
    #     name="resend_verification"
    # ),

    path(
        "auth/login/",
        LoginView.as_view(),
        name="login"
    ),


    path(
        "auth/token/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh"
    ),
    
    path(
        "users/change-password/",
        ChangePasswordView.as_view(),
        name="change-password"
    ),


    path(
        "auth/forgot-password/",
        ForgotPasswordView.as_view(),
        name="forgot-password"
    ),


    path(
        "auth/reset-password/<int:uid>/<str:token>/",
        ResetPasswordView.as_view(),
        name="reset-password"
    ),

    path(
        "users/profile/",
        ProfileView.as_view(),
        name="profile"
    ),
    path(
        "users/profile/update/",
        ProfileView.as_view(),
        name="profile_update"
    ),
     path(
        "auth/logout/",
        LogoutView.as_view(),
        name="logout"
    ),

]