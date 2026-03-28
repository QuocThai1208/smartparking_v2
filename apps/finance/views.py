from typing import Optional

from rest_framework import viewsets, permissions, status, mixins
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .models import Payment, WalletTransaction, Wallet
from .serializers.payment_serializers import PaymentSerializer
from .serializers.wallet_serializers import WalletSerializer
from .serializers.wallet_transaction_serializers import WalletTransactionSerializer
from .services.finance_service import FinanceService

from ..users.models import UserRole
from ..users import perms

from ..parking.services.parking_log_service import ParkingLogService, ParkingLogStatsService


class PaymentViewSet(viewsets.GenericViewSet, mixins.ListModelMixin):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Payment.objects.filter(user=user)


class WalletTransactionViewSet(viewsets.GenericViewSet, mixins.ListModelMixin):
    serializer_class = WalletTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_role in [UserRole.STAFF, UserRole.ADMIN]:
            return WalletTransaction.objects.filter(active=True)
        return WalletTransaction.objects.filter(wallet=user.wallet, active=True)


class WalletViewSet(viewsets.GenericViewSet):
    serializer_class = WalletSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request):
        user = request.user
        try:
            wallet = user.wallet
            serializer = WalletSerializer(wallet)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Wallet.DoesNotExist:
            return Response({"detail": "Bạn chưa có ví"}, status=status.HTTP_404_NOT_FOUND)

    @action(methods=['POST'], url_path='deposit', detail=False,
            permission_classes=[permissions.IsAuthenticated])
    def wallet_deposit(self, request):
        user = request.user
        amount = request.data.get('amount')
        description = request.data.get('description')
        wallet = user.wallet
        try:
            wallet.deposit(amount, description)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "Có lỗi " + str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            "message": "Nạp tiền thành công",
            "balance": float(wallet.balance)
        }, status=status.HTTP_200_OK)

    @action(methods=['POST'], url_path='withdraw', detail=False,
            permission_classes=[permissions.IsAuthenticated])
    def wallet_withdraw(self, request):
        user = request.user
        amount = request.data.get('amount')
        description = request.data.get('description')
        wallet = user.wallet
        try:
            wallet.withdraw(amount, description)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "Có lỗi " + str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            "message": "Rút tiền thành công",
            "balance": float(wallet.balance)
        }, status=status.HTTP_200_OK)


class StatsViewSet(viewsets.GenericViewSet):
    pagination_class = PageNumberPagination
    @action(methods=['get'], detail=False, url_path='revenue', permission_classes=[perms.IsEmployee])
    def get_stats_revenue(self, request):
        user = self.request.user
        try:
            day = _to_int_or_none(self.request.query_params.get("day"))
            month = _to_int_or_none(self.request.query_params.get("month"))
            year = _to_int_or_none(self.request.query_params.get("year"))
        except ValueError:
            return Response({"detail": "Thông tin lọc không hợp lệ"}, status=status.HTTP_400_BAD_REQUEST)

        df, dt = ParkingLogService.create_df_dt(day, month, year)
        revenue = FinanceService.get_total_revenue_range(user, df, dt)
        return Response({
            "message": "Lấy tổng doanh thu thành công",
            "result": {
                "revenue": revenue
            }}, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path='revenue/chart', permission_classes=[perms.IsEmployee])
    def get_revenue_chart(self, request):
        results = FinanceService.get_revenue_chart_data()

        return Response({
            "message": "Lấy dữ liệu biểu đồ theo thành công",
            "result": results
        }, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path='revenue/compare', permission_classes=[perms.IsEmployee])
    def get_compare_monthly_revenue(self, request):
        user = self.request.user
        try:
            day = _to_int_or_none(self.request.query_params.get("day"))
            month = _to_int_or_none(self.request.query_params.get("month"))
            year = _to_int_or_none(self.request.query_params.get("year"))
        except ValueError:
            return Response({"detail": "Thông tin lọc không hợp lệ"}, status=status.HTTP_400_BAD_REQUEST)

        current_start, current_end = FinanceService.create_df_dt(day, month, year)

        period_value = ""
        prev_start = None
        prev_end = None
        if day and month and year:
            period_value = f"ngày {day - 1}/{month}/{year}"
            prev_start, prev_end = ParkingLogService.create_df_dt(day - 1, month, year)
        elif month and year and not day:
            period_value = f"tháng {month - 1}/{year}"
            prev_start, prev_end = ParkingLogService.create_df_dt(day, month - 1, year)
        elif year and not month and not day:
            period_value = f"năm {year - 1}"
            prev_start, prev_end = ParkingLogService.create_df_dt(day, month, year - 1)

        response = FinanceService.compare_monthly_revenue(user,
                                                          period_value,
                                                          current_start,
                                                          current_end,
                                                          prev_start,
                                                          prev_end)
        return Response({
            "message": "Lấy thông tin so sánh doanh thu thành công",
            "result": response
        }, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path="revenue/by-user", permission_classes=[perms.IsEmployee])
    def get_revenue_by_user(self, request):
        try:
            day = _to_int_or_none(self.request.query_params.get("day"))
            month = _to_int_or_none(self.request.query_params.get("month"))
            year = _to_int_or_none(self.request.query_params.get("year"))
        except ValueError:
            return Response({"detail": "Thông tin lọc không hợp lệ"}, status=status.HTTP_400_BAD_REQUEST)

        df, dt = FinanceService.create_df_dt(day, month, year)
        response = FinanceService.get_revenue_by_user(df, dt)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(response, request)

        if page is not None:
            return paginator.get_paginated_response(page)

        return Response({
            "message": "Lấy doanh thu theo khách hàng thành công.",
            "result": response
        }, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path="revenue/by-type-vehicle", permission_classes=[perms.IsEmployee])
    def get_revenue_by_type_vehicle(self, request):
        try:
            day = _to_int_or_none(self.request.query_params.get("day"))
            month = _to_int_or_none(self.request.query_params.get("month"))
            year = _to_int_or_none(self.request.query_params.get("year"))
        except ValueError:
            return Response({"detail": "Thông tin lọc không hợp lệ"}, status=status.HTTP_400_BAD_REQUEST)

        df, dt = FinanceService.create_df_dt(day, month, year)
        response = FinanceService.get_revenue_by_type_vehicle(df, dt)
        return Response({
            "message": "Lấy doanh thu theo loại xe thành công.",
            "result": response
        }, status=status.HTTP_200_OK)


def _to_int_or_none(value: Optional[str]) -> Optional[int]:
    if value is None or value == '':
        return None
    ivalue = int(value)
    if ivalue <= 0:
        raise ValueError
    return ivalue
