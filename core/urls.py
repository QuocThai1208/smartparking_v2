from django.urls import path, include, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.parking.admin_site import custom_admin_site

schema_view = get_schema_view(
    openapi.Info(
        title="Smart Parking API",
        default_version='v2',
        description="APIs for SmartParkingApp",
        contact=openapi.Contact(email="thai124@gmail.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # Quản trị hệ thống
    path('admin/', custom_admin_site.urls),

    # Các API nghiệp vụ
    path("api/", include('apps.users.urls')),
    path("api/", include('apps.parking.urls')),
    path("api/", include('apps.finance.urls')),

    # Tài liệu API Swagger
    re_path(r'^swagger(?P<format>\.json|\.yaml)$',
            schema_view.without_ui(cache_timeout=0),
            name='schema-json'),
    re_path(r'^swagger/$',
            schema_view.with_ui('swagger', cache_timeout=0),
            name='schema-swagger-ui'),
    re_path(r'^redoc/$',
            schema_view.with_ui('redoc', cache_timeout=0),
            name='schema-redoc')
]
