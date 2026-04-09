import calendar
from datetime import date, timedelta
from typing import Optional, Any

from django.db.models.aggregates import Count
from django.db.models.functions import Coalesce, TruncDay, TruncMonth
from django.db.models import Sum, F
from rest_framework.exceptions import ValidationError
from ...users.models import User, UserRole
from ...parking.models import ParkingLog, ParkingStatus
from django.utils import timezone


class FinanceService:
    @staticmethod
    def get_revenue_chart_data():
        today = timezone.now()

        # XỬ LÝ DAILY (7 ngày gần nhất)
        daily_results = []
        start_date_daily = today - timedelta(days=6)

        data = ParkingLog.objects.filter(
            status=ParkingStatus.OUT,
            created_date__date__range=[start_date_daily, today]
        ).annotate(
            date_label=TruncDay('created_date')
        ).values('date_label').annotate(
            total=Coalesce(Sum('fee'), 0)
        ).order_by('date_label')

        dict_daily = {item['date_label'].date(): item['total'] for item in data}
        for i in range(7):
            current_day = start_date_daily + timedelta(days=i)
            daily_results.append({
                "name": current_day.strftime("%a"),
                "value": dict_daily.get(current_day, 0)
            })

        # --- XỬ LÝ MONTHLY (12 tháng gần nhất) ---
        monthly_results = []
        # Lùi về đúng ngày đầu tiên của 11 tháng trước để đủ 12 tháng tính cả tháng này
        start_date_monthly = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        for _ in range(10):  # Lùi tiếp để đủ 12
            start_date_monthly = (start_date_monthly - timedelta(days=1)).replace(day=1)

        data_monthly = ParkingLog.objects.filter(
            status=ParkingStatus.OUT,
            created_date__date__range=[start_date_monthly, today]
        ).annotate(
            month_label=TruncMonth('created_date')
        ).values('month_label').annotate(
            total=Coalesce(Sum('fee'), 0)
        ).order_by('month_label')

        data_dict = {item['month_label'].date().replace(day=1): item['total'] for item in data_monthly}
        for i in range(12):
            m = (start_date_monthly.month + i - 1) % 12 + 1
            y = start_date_monthly.year + (start_date_monthly.month + i - 1) // 12
            current_month = date(y, m, 1)

            monthly_results.append({
                "name": current_month.strftime("%b"),
                "value": data_dict.get(current_month, 0)
            })

        return {
            "daily": daily_results,
            "monthly": monthly_results
        }


    @staticmethod
    def get_total_revenue_range(user: User,
                                date_from: Optional[date] = None,
                                date_to: Optional[date] = None) -> int:
        filters: dict[str, Any] = {}

        if user.user_role == UserRole.CUSTOMER:
            filters["user"] = user
            filters["status"] = ParkingStatus.OUT
        elif user.user_role in [UserRole.MANAGE, UserRole.STAFF, UserRole.ADMIN]:
            filters["status"] = ParkingStatus.OUT

        if date_from:
            filters["created_date__date__gte"] = date_from
        if date_to:
            filters["created_date__date__lte"] = date_to

        total_revenue = ParkingLog.objects.filter(**filters).aggregate(total=Coalesce(Sum("fee"), 0))["total"]
        return total_revenue


    @staticmethod
    def compare_monthly_revenue(user: User,
                                period_value: str,
                                current_start: Optional[date] = None,
                                current_end: Optional[date] = None,
                                prev_start: Optional[date] = None,
                                prev_end: Optional[date] = None):
        current_revenue = FinanceService.get_total_revenue_range(user, current_start, current_end)
        if prev_start and prev_end:
            prev_revenue = FinanceService.get_total_revenue_range(user, prev_start, prev_end)

            if prev_revenue == 0:
                change_percent = 100.0 if current_revenue > 0 else 0.0
            else:
                change_percent = ((current_revenue - prev_revenue) / prev_revenue) * 100
            return {
                "revenue": current_revenue,
                "change": change_percent,
                "period": f"so với {period_value}"
            }
        return {
            "revenue": current_revenue,
            "change": 0,
            "period": ""
        }


    @staticmethod
    def get_revenue_by_user(date_from: Optional[date] = None,
                            date_to: Optional[date] = None):
        filters: dict[str, Any] = {
            "status": ParkingStatus.OUT,
        }
        if date_from:
            filters["created_date__date__gte"] = date_from
        if date_to:
            filters["created_date__date__lte"] = date_to

        results = (ParkingLog.objects.filter(**filters)
                   .values("user__full_name", "user__email")
                   .annotate(revenue=Coalesce(Sum('fee'), 0))
                   .order_by('-revenue'))
        formatted_results = [{
            "full_name": item["user__full_name"],
            "email": item["user__email"],
            "revenue": item["revenue"]
        } for item in results]

        return formatted_results


    @staticmethod
    def get_revenue_by_type_vehicle(date_from: Optional[date] = None,
                                    date_to: Optional[date] = None):

        VEHICLE_NAME_VI = {
            'car': 'Ô tô',
            'motorcycle': 'Xe máy',
            'bike': 'Xe đạp',
            'truck': 'Xe tải',
            'electric_bike': 'Xe máy điện'
        }

        filters: dict[str, Any] = {
            "status": ParkingStatus.OUT,
        }
        if date_from:
            filters["created_date__date__gte"] = date_from
        if date_to:
            filters["created_date__date__lte"] = date_to

        results = ParkingLog.objects.filter(**filters).values(
            vehicle_type=F("vehicle__type")
        ).annotate(
            revenue=Coalesce(Sum('fee'), 0),
        )
        total_revenue = sum(item['revenue'] for item in results)

        formatted_results = []
        for item in results:
            raw_type = str(item['vehicle_type']).lower()
            display_name = VEHICLE_NAME_VI.get(raw_type, raw_type.title())

            percentage = round((item['revenue'] / total_revenue * 100), 1) if total_revenue > 0 else 0

            formatted_results.append({
                "name": display_name,
                "value": percentage,
                "revenue": item['revenue']
            })
        return formatted_results


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
