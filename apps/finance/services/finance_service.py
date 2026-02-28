import calendar
from datetime import date
from typing import Optional
from django.db.models.functions import Coalesce
from django.db.models import Sum
from rest_framework.exceptions import ValidationError
from ...users.models import User, UserRole
from ...parking.models import ParkingLog, ParkingStatus

class FinanceService:
    @staticmethod
    def get_total_revenue_range(regimen: str, user: User,
                                date_from: Optional[date] = None,
                                date_to: Optional[date] = None) -> int:
        if regimen == 'my' or user.user_role == UserRole.CUSTOMER:
            parking_logs = ParkingLog.objects.filter(status=ParkingStatus.OUT, user=user)
        else:
            parking_logs = ParkingLog.objects.filter(status=ParkingStatus.OUT)

        if date_from:
            # lấy các bảng ghi có ngày lớn hơn date_from
            parking_logs = parking_logs.filter(created_date__date__gte=date_from)
        if date_to:
            # lấy các bảng ghi có ngày nhỏ lơn date_to
            parking_logs = parking_logs.filter(created_date__date__lte=date_to)

        total_revenue = parking_logs.aggregate(total=Coalesce(Sum("fee"), 0))["total"]
        return total_revenue

    @staticmethod
    def compare_monthly_revenue(user: User, current_start: Optional[date] = None,
                                current_end: Optional[date] = None,
                                prev_start: Optional[date] = None,
                                prev_end: Optional[date] = None):
        current_revenue = FinanceService.get_total_revenue_range('my', user, current_start, current_end)
        prev_revenue = FinanceService.get_total_revenue_range('my',user, prev_start, prev_end)

        if prev_revenue == 0:
            change_percent = 100.0 if current_revenue > 0 else 0.0
        else:
            change_percent = ((current_revenue - prev_revenue) / prev_revenue) * 100
        return {
            "revenue": current_revenue,
            "change_percent": change_percent
        }
    @staticmethod
    def get_revenue_by_user(date_from: Optional[date] = None,
                            date_to: Optional[date] = None):
        parking_logs = ParkingLog.objects.filter(status=ParkingStatus.OUT)
        if date_from:
            parking_logs = parking_logs.filter(created_date__date__gte=date_from)
        if date_to:
            parking_logs = parking_logs.filter(created_date__date__lte=date_to)

        results = parking_logs.values("user__username").annotate(total=Coalesce(Sum('fee'), 0))
        return results

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