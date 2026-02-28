from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

router.register('fee-role', views.FeeRoleViewSet, basename='fee-role')
router.register('parking-logs', views.ParkingLogViewSet, basename='parking-log')
router.register('vehicles', views.VehicleViewSet, basename='vehicle')

urlpatterns = [
    path('', include(router.urls)),
]
