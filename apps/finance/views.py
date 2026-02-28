from typing import Optional

from rest_framework import viewsets, permissions, status, mixins
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import Payment, WalletTransaction, Wallet
from .serializers.payment_serializers import PaymentSerializer
from .serializers.wallet_serializers import WalletSerializer
from .serializers.wallet_transaction_serializers import WalletTransactionSerializer
from .services.finance_service import FinanceService

from ..users.models import UserRole
from ..users import perms

from ..parking.services.parking_service import ParkingService
from ..parking.services.handle_parking_service import HandleParkingService



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



class StatsViewSet(viewsets.ViewSet):
    @action(methods=['get'], detail=False, url_path='revenue', permission_classes=[perms.IsStaffOrAdmin])
    def get_stats_revenue(self, request):
        user = self.request.user
        try:
            day = _to_int_or_none(self.request.query_params.get("day"))
            month = _to_int_or_none(self.request.query_params.get("month"))
            year = _to_int_or_none(self.request.query_params.get("year"))
        except ValueError:
            raise ValidationError("ngày, tháng, năm phải là số dương")

        df, dt = FinanceService.create_df_dt(day, month, year)
        revenue = FinanceService.get_total_revenue_range("my", user, df, dt)
        return Response(revenue, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path='revenue/compare-monthly',
            permission_classes=[perms.IsStaffOrAdmin])
    def get_compare_monthly_revenue(self, request):
        user = self.request.user
        try:
            day = _to_int_or_none(self.request.query_params.get("day"))
            month = _to_int_or_none(self.request.query_params.get("month"))
            year = _to_int_or_none(self.request.query_params.get("year"))
        except ValueError:
            raise ValidationError("ngày, tháng, năm phải là số dương")
        current_start, current_end = FinanceService.create_df_dt(day, month, year)
        prev_start, prev_end = FinanceService.create_df_dt(day, month - 1, year)
        payload = FinanceService.compare_monthly_revenue(user, current_start, current_end, prev_start, prev_end)
        return Response(payload, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path="revenue/by-user", permission_classes=[perms.IsStaffOrAdmin])
    def get_revenue_by_user(self, request):
        try:
            day = _to_int_or_none(self.request.query_params.get("day"))
            month = _to_int_or_none(self.request.query_params.get("month"))
            year = _to_int_or_none(self.request.query_params.get("year"))
        except ValueError:
            raise ValidationError("ngày, tháng, năm phải là số dương")

        df, dt = FinanceService.create_df_dt(day, month, year)
        payload = FinanceService.get_revenue_by_user(df, dt)
        return Response(payload, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path='parking-logs/count',
            permission_classes=[permissions.IsAuthenticated])
    def get_count_parking_log(self, request):
        user = self.request.user
        regimen = self.request.query_params.get("regimen")
        try:
            day = _to_int_or_none(self.request.query_params.get("day"))
            month = _to_int_or_none(self.request.query_params.get("month"))
            year = _to_int_or_none(self.request.query_params.get("year"))
        except ValueError:
            raise ValidationError("ngày, tháng, năm phải là số dương")

        df, dt = FinanceService.create_df_dt(day, month, year)
        count_parking_log = ParkingService.get_total_count_parking(regimen, user, df, dt)
        payload = {"countParkingLog": count_parking_log}

        if df and dt and df == dt:
            payload.update({"ngày": f"{df.day}/{df.month}/{df.year}"})
        elif df and dt and df.month == 1 and df.day == 1 and dt.month == 12:
            payload.update({"năm": df.year})
        elif df and dt and df.day == 1:
            payload.update({"tháng": f"{df.month}/{df.year}"})
        return Response(payload, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path='parking-logs/total-time',
            permission_classes=[permissions.IsAuthenticated])
    def get_total_time_parking_log(self, request):
        user = self.request.user
        regimen = self.request.query_params.get("regimen")
        try:
            day = _to_int_or_none(self.request.query_params.get("day"))
            month = _to_int_or_none(self.request.query_params.get("month"))
            year = _to_int_or_none(self.request.query_params.get("year"))
        except ValueError:
            raise ValidationError("ngày, tháng, năm phải là số dương")

        df, dt = FinanceService.create_df_dt(day, month, year)
        total_time = ParkingService.get_total_time_parking(regimen, user, df, dt)
        payload = {"totalTime": total_time}

        if df and dt and df == dt:
            payload.update({"ngày": f"{df.day}/{df.month}/{df.year}"})
        elif df and dt and df.month == 1 and df.day == 1 and dt.month == 12:
            payload.update({"năm": df.year})
        elif df and dt and df.day == 1:
            payload.update({"tháng": f"{df.month}/{df.year}"})
        return Response(payload, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path='total-customer',
            permission_classes=[perms.IsStaffOrAdmin])
    def get_total_customer(self, request):
        payload = HandleParkingService.get_total_customer()
        return Response(payload, status=status.HTTP_200_OK)


def _to_int_or_none(value: Optional[str]) -> Optional[int]:
    if value is None or value == '':
        return None
    ivalue = int(value)
    if ivalue <= 0:
        raise ValueError
    return ivalue