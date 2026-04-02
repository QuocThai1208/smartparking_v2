from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter(trailing_slash=False)

router.register('payments', views.PaymentViewSet, basename='payment')
router.register('stats', views.StatsViewSet, basename='stats')
router.register('transactions', views.WalletTransactionViewSet, basename='walletTransaction')
router.register('wallet', views.WalletViewSet, basename='wallet')

urlpatterns = [
    path('', include(router.urls)),
]
