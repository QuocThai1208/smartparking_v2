from typing import Optional
import json
from datetime import date
from django.utils import timezone
from django.db import transaction

from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, generics, permissions, status, mixins
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .serializers.MapSvgSerializers import MapSvgCreateSerializer
from .serializers.booking_serializers import BookingCreateSerializer, BookingSerializer
from .serializers.parking_lot_policy_serializers import LotPolicyCreateSerializer, BaseLotPolicySerializer
from .serializers.parking_lot_serializers import LotCreateSerializer, LotSerializer, LotDetailSerializer
from .serializers.parking_slot_serializers import SlotCreateSerializer
from .serializers.price_strategy_serializers import PriceStrategySerializer
from .serializers.public_holiday_serializers import BasePublicHolidaySerializer
from .services.sensor_services import SensorService
from ..users import perms

from .models import Vehicle, FeeRule, ParkingLog, ParkingStatus, ParkingLot, ParkingSlot, ParkingLotPolicy, \
    PublicHoliday, PriceStrategy, PriceStrategyTemplate

from .services.vehicle_service import VehicleService
from .serializers.vehicle_serializers import VehicleSerializer, VehicleCreateSerializer
from .serializers.fee_role_serializers import FeeRuleSerializer
from .serializers.parking_log_serializers import ParkingLogSerializer, LogHistoryAdminSerializer, \
    LogDetailAdminSerializer
from .serializers.vehicle_face_serializers import FaceRegistrationInputSerializer, VehicleFaceSerializer
from .serializers.parking_serializers import CheckInSerializer, CheckOutSerializer, ParkingBaseSerializer

from .services.parking_service import ParkingService
from .services.parking_log_service import ParkingLogService, ParkingLogStatsService
from .services.barrier_services import BarrierService


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
        return [perms.IsVehicleOwner()]

    def perform_create(self, serializer):
        serializer.save()

    @action(methods=['get'], detail=False, url_path='stats', permission_classes=[permissions.IsAuthenticated])
    def vehicle_stats(self, request):
        user = request.user
        return Response(VehicleService.get_user_vehicle_stats(user), status=status.HTTP_200_OK)


class LotViewSet(viewsets.GenericViewSet,
                 mixins.CreateModelMixin,
                 mixins.ListModelMixin,
                 mixins.RetrieveModelMixin):
    queryset = ParkingLot.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return LotCreateSerializer
        elif self.action == 'retrieve':
            return LotDetailSerializer
        elif self.action == 'add_policies':
            return LotPolicyCreateSerializer
        return LotSerializer

    def get_permissions(self):
        if self.action in ['create']:
            return [perms.IsManage()]
        elif self.action in ['list']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    @action(detail=True, methods=['POST'], url_path='barrier/open', permission_classes=[permissions.IsAuthenticated])
    def barrier_open(self, request, pk=None):
        user = request.user
        barrier_id = request.data.get('barrier_id')

        success, msg = BarrierService.open_barrier_event(open_flag=True,
                                                         barrier_id=barrier_id,
                                                         user_id=user.id,
                                                         slot_id=pk)
        success = status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST
        return Response({"message": msg}, status=success)

    @action(detail=True, methods=['POST'], url_path='upload-full-map', permission_classes=[perms.IsLotOwner])
    def create_multiple_slot(self, request, pk=None):
        parking_lot = self.get_object()

        map_data = {
            'floor': request.data.get('floor'),
            'floor_display': request.data.get('floor_display'),
            'map_svg': request.data.get('map_svg')
        }

        slots_raw = request.data.get('slots', '[]')  # dữ liệu dạng json
        try:
            slots_data = json.loads(slots_raw)  # chuyển thành câus trúc object
        except json.JSONDecodeError:
            return Response({"error": "Định dạng slots không hợp lệ"}, status=400)

        try:
            with transaction.atomic():
                # Lưu Map
                map_serializer = MapSvgCreateSerializer(data=map_data)
                map_serializer.is_valid(raise_exception=True)
                map_serializer.save(parking_lot=parking_lot)

                # Lưu slots
                slot_serializer = SlotCreateSerializer(data=slots_data, many=True)
                slot_serializer.is_valid(raise_exception=True)
                slot_to_create = [
                    ParkingSlot(parking_lot=parking_lot, **item)
                    for item in slot_serializer.validated_data]

                ParkingSlot.objects.bulk_create(slot_to_create)

            return Response({
                "message": "Lưu sơ đồ và slot thành công",
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['POST', 'GET'], url_path='policies', permission_classes=[perms.IsLotOwner])
    def add_policies(self, request, pk=None):
        if request.method == 'POST':
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.save()
            return Response({
                "message": "Thêm chính sách thành công",
                "result": BaseLotPolicySerializer(data).data
            }, status=status.HTTP_201_CREATED)
        policies = ParkingLotPolicy.objects.filter(parking_lot_id=pk).select_related('strategy', 'holiday')
        serializer = BaseLotPolicySerializer(policies, many=True)
        return Response({
            "message": "Lấy danh sách chính sách thành công",
            "result": serializer.data
        }, status=status.HTTP_200_OK)


class BookingViewSet(viewsets.GenericViewSet,
                     mixins.CreateModelMixin,
                     mixins.ListModelMixin,
                     mixins.RetrieveModelMixin, ):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return BookingCreateSerializer
        return BookingSerializer


class VehicleFaceViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin):
    serializer_class = FaceRegistrationInputSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # Tự động trả về 400 nếu lỗi
        face_record = serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class FeeRoleViewSet(viewsets.GenericViewSet,
                     mixins.CreateModelMixin,
                     mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin,
                     mixins.ListModelMixin):
    queryset = FeeRule.objects.all()
    serializer_class = FeeRuleSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        return [perms.IsEmployee()]


class ParkingLogViewSet(viewsets.ViewSet, generics.ListAPIView):
    serializer_class = ParkingLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_anonymous:
            return Response({
                "message": "Lấy lịch sử gửi xe thành công",
                "result": None
            }, status=status.HTTP_200_OK)
        try:
            day = _to_int_or_none(self.request.query_params.get("day"))
            month = _to_int_or_none(self.request.query_params.get("month"))
            year = _to_int_or_none(self.request.query_params.get("year"))
        except ValueError:
            raise ValidationError("ngày, tháng, năm phải là số dương")

        parking_logs = ParkingLogService.get_my_logs(user, day, month, year)
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

    @action(methods=['get'], detail=True, url_path="fee_detail")
    def get_fee_detail(self, request, pk=None):
        log = self.get_object()
        final_fee, fee_detail = ParkingLogService.calculate_fee(log.fee_rule, log.parking_lot.id, log.check_in, log.check_out)
        return Response({
            "final_fee": final_fee,
            "fee_detail": fee_detail
        }, status=status.HTTP_200_OK)


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

        success, msg, result = ParkingService.check_in(**serializer.validated_data)

        res_status = status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST
        return Response({
            "status": "loading",
            "message": msg,
            "result": result
        }, status=res_status)

    @action(detail=False, methods=['post'], url_path='check-out')
    def check_out(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        success, msg, result = ParkingService.check_out(**serializer.validated_data)

        res_status = status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST
        return Response({
            "status": "loading",
            "message": msg,
            "result": result
        }, status=res_status)


class AdminViewSet(viewsets.GenericViewSet):
    permission_classes = [perms.IsEmployee]
    pagination_class = PageNumberPagination

    @action(detail=False, methods=["post"], url_path=r"vehicles/(?P<vehicle_id>\d+)/is_approved-change",
            permission_classes=[perms.IsEmployee])
    def vehicle_approved(self, request, vehicle_id=None):
        try:
            vehicle = Vehicle.objects.get(id=vehicle_id)
            value = request.query_params.get('value')
            if not value:
                return Response({"message": "Vui lòng điền giá trị thây đổi"}, status=status.HTTP_400_BAD_REQUEST)
            vehicle.is_approved = value
            vehicle.save()
            return Response({"message": "Thây đổi trạng thái phương tiện thành công."}, status=status.HTTP_200_OK)
        except Vehicle.DoesNotExist:
            return Response({"detail": "Không tìm thấy phương tiện"}, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses={200: VehicleSerializer(many=True)})
    @action(detail=False, methods=["get"], url_path="vehicles", permission_classes=[perms.IsEmployee])
    def get_vehicles(self, request):
        license_plate = request.query_params.get("license_plate", "")
        is_approved = request.query_params.get("is_approved", None)

        vehicles = VehicleService.get_all_vehicle(license_plate, is_approved)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(vehicles, request)

        if page is not None:
            serializer = VehicleSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = VehicleSerializer(vehicles, many=True)
        return Response({
            "message": "Lấy toàn bộ danh sách phương tiện thành công.",
            "result": serializer.data
        }, status=status.HTTP_200_OK)

    @swagger_auto_schema(responses={200: LogHistoryAdminSerializer(many=True)})
    @action(detail=False, methods=["get"], url_path="history")
    def history(self, request):
        logs = ParkingLogService.get_top5_history()
        return Response({
            "message": "Lấy lịch sử gửi xe thành công",
            "result": LogHistoryAdminSerializer(logs, many=True).data
        }, status=status.HTTP_200_OK)

    @swagger_auto_schema(responses={200: LogDetailAdminSerializer(many=True)})
    @action(detail=False, methods=["get"], url_path="parking-logs")
    def parking_logs(self, request):
        user = self.request.user
        if user.is_anonymous:
            return Response({
                "message": "Lấy lịch sử gửi xe thành công",
                "result": None
            }, status=status.HTTP_200_OK)
        try:
            day = _to_int_or_none(request.query_params.get("day"))
            month = _to_int_or_none(request.query_params.get("month"))
            year = _to_int_or_none(request.query_params.get("year"))
            plate = request.query_params.get("plate", "")
        except ValueError:
            raise ValidationError("ngày, tháng, năm phải là số dương")

        parking_logs = ParkingLogService.get_all_logs(user, day, month, year, plate)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(parking_logs, request)

        if page is not None:
            serializer = LogDetailAdminSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        return Response({
            "message": "Lấy toàn bộ lịch sử gửi xe thành công",
            "result": LogDetailAdminSerializer(parking_logs, many=True).data
        }, status=status.HTTP_200_OK)


class StatsViewSet(viewsets.GenericViewSet):
    @action(methods=['get'], detail=False, url_path='parking/peak-hours',
            permission_classes=[perms.IsEmployee])
    def get_peak_hour_stats(self, request):
        today = timezone.localdate()
        year = today.year
        month = today.month
        day = today.day

        df, dt = ParkingLogService.create_df_dt(day, month, year)
        response = ParkingLogStatsService.get_peak_hour_stats(df, dt)
        return Response({
            "message": "Lấy thống kê khung giờ cao điểm thành công",
            "result": response
        }, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path='parking-logs/compare',
            permission_classes=[permissions.IsAuthenticated])
    def get_count_parking_log(self, request):
        user = self.request.user
        try:
            day = _to_int_or_none(self.request.query_params.get("day"))
            month = _to_int_or_none(self.request.query_params.get("month"))
            year = _to_int_or_none(self.request.query_params.get("year"))
        except ValueError:
            return Response({"detail": "Thông tin lọc không hợp lệ"}, status=status.HTTP_400_BAD_REQUEST)

        current_start, current_end = ParkingLogService.create_df_dt(day, month, year)

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

        result = ParkingLogStatsService.get_total_count_parking(user,
                                                                period_value,
                                                                current_start,
                                                                current_end,
                                                                prev_start,
                                                                prev_end)
        return Response({
            "message": "Xem số lượng xe giữ thành công.",
            "result": result
        }, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path='parking/current',
            permission_classes=[permissions.IsAuthenticated])
    def get_parking_current_stats(self, request):
        response = ParkingLogStatsService.get_parking_current_stats()
        return Response({
            "message": "Lấy thông tin hiện tại của bãi xe thành công",
            "result": response
        }, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path='total-customer',
            permission_classes=[perms.IsStaffOrAdmin])
    def get_total_customer(self, request):
        response = ParkingLogStatsService.get_total_customer()
        return Response({
            "message": "Lấy tổng số khách hàng thành công",
            "result": response
        }, status=status.HTTP_200_OK)


class PublicHolidayViewSet(viewsets.GenericViewSet,
                           mixins.ListModelMixin,):
    permission_classes = [perms.IsEmployee]
    serializer_class = BasePublicHolidaySerializer
    queryset = PublicHoliday.objects.all()


class PriceStrategyViewSet(viewsets.GenericViewSet,
                           mixins.ListModelMixin,):
    permission_classes = [perms.IsEmployee]
    serializer_class = PriceStrategySerializer
    queryset = PriceStrategyTemplate.objects.all()


class TestViewSet(viewsets.GenericViewSet):
    @action(methods=['post'], detail=False, url_path='sensor-signa', permission_classes=[permissions.AllowAny])
    def sensor_signal(self, request):
        is_occupied = request.data.get('is_occupied', False)
        vehicle_id = request.data.get('vehicle_id', '')
        slot_id = request.data.get('slot_id', '')

        result = SensorService.process_sensor_signal(is_occupied=is_occupied,
                                                     vehicle_id=vehicle_id,
                                                     slot_id=slot_id)

        success = status.HTTP_200_OK if result else status.HTTP_400_BAD_REQUEST
        msg = "Test cảm biến nhận xe thành công." if result else "Test cảm biến nhận xe thất bại"
        return Response({"message": msg}, status=success)


def _to_int_or_none(value: Optional[str]) -> Optional[int]:
    if value is None or value == '':
        return None
    ivalue = int(value)
    if ivalue <= 0:
        raise ValueError
    return ivalue
