from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from . import views
from .views import LoginView, UserProfileView, RegisterView

router = DefaultRouter()

router.register('users', views.UserViewSet, basename='user')


urlpatterns = [
    path('', include(router.urls)),
    path('auth/login', LoginView.as_view(), name='auth_login'),
    path('auth/token/refresh', TokenRefreshView.as_view(), name='token_refresh'),
    path('users/me', UserProfileView.as_view(), name='user_profile'),
    path('users/register', RegisterView.as_view(), name='user_register'),
]