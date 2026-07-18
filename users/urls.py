from django.urls import path

from .views import (
    RegisterView,
    ProfileView
)

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView
)



urlpatterns = [

    path(
        "auth/register/",
        RegisterView.as_view(),
        name="register"
    ),


    path(
        "auth/login/",
        TokenObtainPairView.as_view(),
        name="login"
    ),


    path(
        "auth/token/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh"
    ),


    path(
        "users/profile/",
        ProfileView.as_view(),
        name="profile"
    ),

]