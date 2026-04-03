from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter(trailing_slash=False)

router.register('fee-roles', views.FeeRoleViewSet, basename='fee-role')
router.register('parking-logs', views.ParkingLogViewSet, basename='parking-log')
router.register('vehicles', views.VehicleViewSet, basename='vehicle')
router.register('vehicle-faces', views.VehicleFaceViewSet, basename='vehicle-face')
router.register('parking', views.ParkingViewSet, basename='parking')
router.register('admin', views.AdminViewSet, basename='admin')
router.register('stats', views.StatsViewSet, basename='stats')
router.register('parking-lots', views.LotViewSet, basename='parking-lot')
router.register('bookings', views.BookingViewSet, basename='booking')
router.register('public-holidays', views.PublicHolidayViewSet, basename='public-holiday')
router.register('price-strategy', views.PriceStrategyViewSet, basename='price-strategy')
router.register('tests', views.TestViewSet, basename='test')

urlpatterns = [
    path('', include(router.urls)),
]
