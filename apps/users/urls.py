from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from . import views
from .views import LoginView, UserProfileView, RegisterView

router = DefaultRouter(trailing_slash=False)
router.register('users', views.UserViewSet, basename='user')
router.register('admin', views.AdminViewSet, basename='admin')
router.register('employees', views.EmployeeViewSet, basename='employee')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/login', LoginView.as_view(), name='auth_login'),
    path('auth/token/refresh', TokenRefreshView.as_view(), name='token_refresh'),
    path('users/me', UserProfileView.as_view(), name='user_profile'),
    path('users/register', RegisterView.as_view(), name='user_register'),
]