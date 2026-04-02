from datetime import date
import math
import calendar

from django.db.models.functions import ExtractHour
from django.utils import timezone
from typing import Optional, Any

from rest_framework.exceptions import ValidationError

from ...users.models import UserRole, User
from ..models import ParkingLog, ParkingStatus, Vehicle, FeeRule, FeeType, VehicleFace
from django.db.models import Sum, Count


class ParkingLogStatsService:
    @staticmethod
    def get_peak_hour_stats(date_from=None, date_to=None):
        filters = {}
        if date_from:
            filters["created_date__date__gte"] = date_from
        if date_to:
            filters["created_date__date__lte"] = date_to

        data = ParkingLog.objects.filter(**filters).annotate(
            hour=ExtractHour('created_date')
        ).values('hour').annotate(
            count=Count('id')
        ).order_by('hour')

        #Tạo dictionary để tra cứu nhanh: {8: 150, 17: 200, ...}
        data_dict = {item['hour']: item['count'] for item in data}

        results = []
        for h in range(24):
            results.append({
                "name": f"{h}:00",
                "value": data_dict.get(h, 0)
            })

        return results

    @staticmethod
    def get_parking_current_stats():
        total_slots = 100
        occupied = ParkingLog.objects.filter(status=ParkingStatus.IN).count()
        return {
            "total": total_slots,
            "occupied": occupied,
            "available": total_slots - occupied,
        }

    @staticmethod
    def get_total_count_parking(user: User,
                                period_value: str,
                                current_start: Optional[date] = None,
                                current_end: Optional[date] = None,
                                prev_start: Optional[date] = None,
                                prev_end: Optional[date] = None,
                                ):
        filters_current: dict[str, Any] = {}

        if user.user_role == UserRole.CUSTOMER:
            filters_current["user"] = user
            filters_current["status"] = ParkingStatus.OUT
        elif user.user_role in [UserRole.MANAGE, UserRole.STAFF, UserRole.ADMIN]:
            filters_current["status"] = ParkingStatus.OUT

        if current_start:
            filters_current["created_date__date__gte"] = current_start
        if current_end:
            filters_current["created_date__date__lte"] = current_end

        current_count = ParkingLog.objects.filter(**filters_current).count()

        if prev_start and prev_end:
            filters_prev: dict[str, Any] = {
                "created_date__date__gte": prev_start,
                "created_date__date__lte": prev_end
            }

            if user.user_role == UserRole.CUSTOMER:
                filters_prev["user"] = user
                filters_prev["status"] = ParkingStatus.OUT
            elif user.user_role in [UserRole.MANAGE, UserRole.STAFF, UserRole.ADMIN]:
                filters_prev["status"] = ParkingStatus.OUT


            prev_count = ParkingLog.objects.filter(**filters_prev).count()

            if prev_count == 0:
                change_percent = 100.0 if current_count > 0 else 0.0
            else:
                change_percent = ((current_count - prev_count) / prev_count) * 100
            return {
                "total": current_count,
                "change": change_percent,
                "period": f"so với {period_value}"
            }

        return {
            "total": current_count,
            "change": 0,
            "period": ""
        }

    @staticmethod
    def get_total_time_parking(user: User,
                               date_from: Optional[date] = None,
                               date_to: Optional[date] = None) -> int:
        if user.user_role == UserRole.CUSTOMER:
            parking_logs = ParkingLog.objects.filter(user=user, status=ParkingStatus.OUT)
        else:
            parking_logs = ParkingLog.objects.filter(status=ParkingStatus.OUT)

        if date_from:
            parking_logs = parking_logs.filter(created_date__date__gte=date_from)
        if date_to:
            parking_logs = parking_logs.filter(created_date__date__lte=date_to)
        total = parking_logs.aggregate(total_minutes=Sum('duration_minutes'))['total_minutes'] or 0
        return total

    @staticmethod
    def get_total_customer():
        total_customer = User.objects.filter(user_role=UserRole.CUSTOMER).count()
        return {"totalCustomer": total_customer}


class ParkingLogService:
    # HÀM: tính phí giữ xe
    @staticmethod
    def calculate_fee(minutes: int, fee_rule: FeeRule) -> int:
        if fee_rule.fee_type in [FeeType.MOTORCYCLE, FeeType.CAR]:
            day = max(1, math.ceil(minutes / (24 * 60)))
            return day * fee_rule.amount

        raise ValueError(f"Unsupport fee_type: {fee_rule.fee_type}")

    # HÀM: Cập nhật nhật kí gửi xe
    @staticmethod
    def update_parking(v: Vehicle, ):
        try:
            log = (
                ParkingLog.objects
                .select_for_update()  # khóa bảng ghi cho đến khi hoàn tất
                .get(user=v.user,
                     vehicle=v,
                     status=ParkingStatus.IN)
            )
        except  ParkingLog.DoesNotExist:
            return False, "Không tìm thấy xe lượt vào bãi"

        now = timezone.now()
        log.check_out = now
        duration = int((log.check_out - log.check_in).total_seconds() // 60)
        log.duration_minutes = duration
        log.status = ParkingStatus.OUT
        log.fee = ParkingLogService.calculate_fee(duration, log.fee_rule)
        return True, log

    # HÀM: Tạo mới nhật kí gửi xe
    @staticmethod
    def create_parking_log(parking_lot_id, v: Vehicle, fee_type: FeeType, face=VehicleFace) -> tuple[bool, str]:
        try:
            exist_p = ParkingLog.objects.filter(user=v.user, vehicle=v, status=ParkingStatus.IN).first()
            if exist_p:
                return False, 'Phương tiện này đang có trong bãi'
            p = ParkingLog.objects.create(
                parking_lot_id=parking_lot_id,
                user=v.user,
                vehicle_face=face,
                vehicle=v,
                fee_rule=FeeRule.objects.get(fee_type=fee_type),
                status=ParkingStatus.IN
            )
            if p:
                return True, "Xin mời vào."
            return False, "Không hợp lệ."
        except Exception as e:
            print("Lỗi: ", e)

    @staticmethod
    def get_top5_history():
        logs = ParkingLog.objects.all().order_by('-id')[:10]
        return logs

    @staticmethod
    def get_my_logs(user: User, day: int, month: int, year: int):
        df, dt = ParkingLogService.create_df_dt(day, month, year)

        filters: dict[str, Any] = {
            'user': user,
            'active': True
        }

        if df:
            filters['created_date__date__gte'] = df
        if dt:
            filters['created_date__date__lte'] = dt

        return (ParkingLog.objects.filter(**filters)
                .select_related('vehicle')
                .order_by("-created_date"))

    @staticmethod
    def get_all_logs(user: User, day: int, month: int, year: int, plate: str):
        df, dt = ParkingLogService.create_df_dt(day, month, year)

        filters: dict[str, Any] = {}

        if df:
            filters['created_date__date__gte'] = df
        if dt:
            filters['created_date__date__lte'] = dt
        if plate:
            filters['vehicle__license_plate__istartswith'] = plate

        return (ParkingLog.objects.filter(**filters)
                .select_related('vehicle_face', 'vehicle')
                .order_by("-created_date"))

    @staticmethod
    def create_df_dt(day, month, year) -> tuple[date, date]:
        if day and month and year:
            df = dt = date(year, month, day)
        elif month and year and not day:
            last = calendar.monthrange(year, month)[1]  # lấy ngày cuối cùng của tháng
            df = date(year, month, 1)
            dt = date(year, month, last)
        elif year and not month and not day:
            df = date(year, 1, 1)
            dt = date(year, 12, 31)
        elif not any([day, month, year]):  # trả về false nếu cả 3 là none
            df = dt = None
        else:
            raise ValidationError(
                "• Muốn lấy theo ngày: cần ngày, tháng, năm\n"
                "• Muốn theo tháng: cần tháng, năm\n"
                "• Muốn theo năm: chỉ cần năm"
            )
        return df, dt
