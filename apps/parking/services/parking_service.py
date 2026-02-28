from datetime import date
from typing import Optional
from ...users.models import UserRole, User
from ..models import ParkingLog, ParkingStatus
from django.db.models import Sum


class ParkingService:
    @staticmethod
    def get_total_count_parking(regimen: str, user: User,
                                date_from: Optional[date] = None,
                                date_to: Optional[date] = None) -> int:
        if regimen == 'my' or user.user_role == UserRole.CUSTOMER:
            parking_logs = ParkingLog.objects.filter(user=user, status=ParkingStatus.OUT)
        else:
            parking_logs = ParkingLog.objects.all()

        if date_from:
            # lấy các bảng ghi có ngày lớn hơn date_froms
            parking_logs = parking_logs.filter(created_date__date__gte=date_from)
        if date_to:
            # lấy các bảng ghi có ngày nhỏ lơn date_to
            parking_logs = parking_logs.filter(created_date__date__lte=date_to)

        count = parking_logs.count()
        return count

    @staticmethod
    def get_total_time_parking(regimen: str, user: User,
                               date_from: Optional[date] = None,
                               date_to: Optional[date] = None) -> int:
        if regimen == 'my' or user.user_role == UserRole.CUSTOMER:
            parking_logs = ParkingLog.objects.filter(user=user, status=ParkingStatus.OUT)
        else:
            parking_logs = ParkingLog.objects.all()

        if date_from:
            parking_logs = parking_logs.filter(created_date__date__gte=date_from)
        if date_to:
            parking_logs = parking_logs.filter(created_date__date__lte=date_to)
        total = parking_logs.aggregate(total_minutes=Sum('duration_minutes'))['total_minutes'] or 0
        return total
