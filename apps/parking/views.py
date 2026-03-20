from typing import Optional

from datetime import date

from rest_framework import viewsets, generics, permissions, status, mixins
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import Vehicle, FeeRule, ParkingLog, ParkingStatus
from .services.vehicle_service import VehicleService
from .serializers.vehicle_serializers import VehicleSerializer, VehicleCreateSerializer
from .serializers.fee_role_serializers import FeeRuleSerializer
from .serializers.parking_log_serializers import ParkingLogSerializer
from .serializers.vehicle_face_serializers import FaceRegistrationInputSerializer, VehicleFaceSerializer
from .serializers.parking_serializers import CheckInSerializer, CheckOutSerializer, ParkingBaseSerializer
from ..users import perms
from ..users.models import UserRole
from ..finance.services.finance_service import FinanceService
from .services.parking_service import ParkingService


class VehicleViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        if self.request.user.is_anonymous:
            return Vehicle.objects.none()
        return Vehicle.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'create':
            return VehicleCreateSerializer
        return VehicleSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated()]
        return [perms.IsVehicleOwner]

    def perform_create(self, serializer):
        serializer.save()

    @action(methods=['get'], detail=False, url_path='stats', permission_classes=[permissions.IsAuthenticated])
    def vehicle_stats(self, request):
        user = request.user
        return Response(VehicleService.get_user_vehicle_stats(user), status=status.HTTP_200_OK)


class VehicleFaceViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin):
    serializer_class = FaceRegistrationInputSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # Tự động trả về 400 nếu lỗi
        face_record = serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class FeeRoleViewSet(viewsets.ViewSet, generics.ListAPIView, generics.UpdateAPIView,
                     generics.DestroyAPIView):
    queryset = FeeRule.objects.all()
    serializer_class = FeeRuleSerializer
    permission_classes = [perms.IsStaffOrReadOnly]


class ParkingLogViewSet(viewsets.ViewSet, generics.ListAPIView):
    serializer_class = ParkingLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        regimen = self.request.query_params.get("regimen")

        if regimen == 'my' or user.user_role == UserRole.CUSTOMER:
            parking_logs = ParkingLog.objects.filter(user=user, active=True)
        else:
            parking_logs = ParkingLog.objects.filter(active=True)

        try:
            day = _to_int_or_none(self.request.query_params.get("day"))
            month = _to_int_or_none(self.request.query_params.get("month"))
            year = _to_int_or_none(self.request.query_params.get("year"))
        except ValueError:
            raise ValidationError("ngày, tháng, năm phải là số dương")
        df, dt = FinanceService.create_df_dt(day, month, year)
        if df:
            parking_logs = parking_logs.filter(created_date__date__gte=df)
        if dt:
            parking_logs = parking_logs.filter(created_date__date__lte=dt)
        return parking_logs

    @action(methods=['get'], detail=False, url_path="occupancy", permission_classes=[perms.IsStaffOrAdmin])
    def get_parking_occupancy(self, request):
        count_occupancy = ParkingLog.objects.filter(status=ParkingStatus.IN).count()
        return Response({"occupancy": count_occupancy}, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path="count-today")
    def get_parking_count_today(self, request):
        now = date.today()
        count_today = ParkingLog.objects.filter(created_date__date=now).count()
        return Response(count_today, status=status.HTTP_200_OK)


class ParkingViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.AllowAny]
    def get_serializer_class(self):
        if self.action == 'check_in':
            return CheckInSerializer
        if self.action == 'check_out':
            return CheckOutSerializer
        return ParkingBaseSerializer

    @action(detail=False, methods=["post"], url_path="check-in")
    def check_in(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        success, msg = ParkingService.check_in(**serializer.validated_data)

        res_status = status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST
        return Response({
            "status": "success" if success else "error",
            "result": msg
        }, status=res_status)

    @action(detail=False, methods=['post'], url_path='check-out')
    def check_out(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        success, msg = ParkingService.check_out(**serializer.validated_data)

        res_status = status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST
        return Response({
            "status": "success" if success else "error",
            "result": msg
        }, status=res_status)


def _to_int_or_none(value: Optional[str]) -> Optional[int]:
    if value is None or value == '':
        return None
    ivalue = int(value)
    if ivalue <= 0:
        raise ValueError
    return ivalue
