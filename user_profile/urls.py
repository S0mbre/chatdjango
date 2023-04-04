from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from user_profile.views import *

urlpatterns = [
    path('user/auth/sign-in/', SignInView.as_view(), name='sign-in'),
    path('user/auth/sign-up/', SignupView.as_view(), name='sign-up'),
    path('user/auth/sign-out/', SignOutView.as_view(), name='log-out'),
    path('user/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('user/<int:user_id>', UserView.as_view(), name='user'),
    path('users/', GetAllUsersView.as_view(), name='get-users'),
    path('user/', MyUserView.as_view(), name='get-user'),
    path('search', SearchUsersAndChat.as_view(), name='search'),
]