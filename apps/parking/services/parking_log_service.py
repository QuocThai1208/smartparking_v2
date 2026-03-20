from datetime import date
import  math
from django.utils import timezone
from typing import Optional
from ...users.models import UserRole, User
from ..models import ParkingLog, ParkingStatus, Vehicle, FeeRule, FeeType, VehicleFace
from django.db.models import Sum

class ParkingLogStatsService:
    @staticmethod
    def get_total_count_parking(user: User,
                                date_from: Optional[date] = None,
                                date_to: Optional[date] = None) -> int:
        if user.user_role == UserRole.CUSTOMER:
            parking_logs = ParkingLog.objects.filter(user=user, status=ParkingStatus.OUT)
        else:
            parking_logs = ParkingLog.objects.filter(status=ParkingStatus.OUT)

        if date_from:
            # lấy các bảng ghi có ngày lớn hơn date_froms
            parking_logs = parking_logs.filter(created_date__date__gte=date_from)
        if date_to:
            # lấy các bảng ghi có ngày nhỏ lơn date_to
            parking_logs = parking_logs.filter(created_date__date__lte=date_to)

        count = parking_logs.count()
        return count

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
    def create_parking_log(v: Vehicle, fee_type: FeeType, face = VehicleFace) -> tuple[bool, str]:
        exist_p = ParkingLog.objects.filter(user=v.user, vehicle=v, status=ParkingStatus.IN).first()
        if exist_p:
            return False, 'Phương tiện này đang có trong bãi'
        p = ParkingLog.objects.create(
            user=v.user,
            vehicle_face=face,
            vehicle=v,
            fee_rule=FeeRule.objects.get(fee_type=fee_type),
            status=ParkingStatus.IN
        )
        if p:
            return True, "Xin mời vào."
        return False, "Không hợp lệ."