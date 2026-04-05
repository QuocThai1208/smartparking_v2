from datetime import date, datetime
import math
import calendar

from django.db.models.functions import ExtractHour
from django.utils import timezone
from typing import Optional, Any

from rest_framework.exceptions import ValidationError

from .price_services import PriceEngine
from ...users.models import UserRole, User
from ..models import ParkingLog, ParkingStatus, Vehicle, FeeRule, FeeType, VehicleFace, Booking, BookingStatus
from django.db.models import Sum, Count
from datetime import timedelta


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
    def calculate_fee(fee_rule: FeeRule, parking_lot_id, start_time, end_time,):
        try:
            if fee_rule.fee_type not in [FeeType.MOTORCYCLE, FeeType.CAR, FeeType.BUS, FeeType.TRUCK]:
                raise ValueError(f"Unsupport fee_type: {fee_rule.fee_type}")

            if (end_time - start_time).total_seconds() <= 0:
                return 0, []

            final_fee = 0
            fee_detail = []

            current_time = start_time

            while current_time < end_time:
                # Xác định điểm kết thúc là cuối (23:59:59) hay end_time
                next_day_start = (current_time + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                segment_end = min(next_day_start, end_time)

                # Tính số giờ trong phân đoạn của ngày này
                segment_minutes = (segment_end - current_time).total_seconds() / 60
                segment_hours = math.ceil(segment_minutes / 60)

                # Lấy giá của ngày này
                price_info = PriceEngine.calculate_final_price(
                    parking_lot_id,
                    fee_rule.amount,
                    current_time
                )

                unit_price = price_info['total_fee']  # Giá mỗi giờ
                day_fee = segment_hours * unit_price
                final_fee += day_fee

                # 4. Lưu chi tiết cực kỳ ngắn gọn theo ngày
                fee_detail.append({
                    "date": current_time.strftime("%d/%m/%Y"),
                    "period": f"{current_time.strftime('%H:%M')} - {segment_end.strftime('%H:%M')}",
                    "hours": segment_hours,
                    "unit_price": unit_price,
                    "surcharge": price_info['surcharge'],
                    "note": price_info['note'],  # Ví dụ: "Phụ phí cuối tuần"
                    "sub_total": day_fee
                })

                # Nhảy sang ngày tiếp theo
                current_time = segment_end

            return int(final_fee), fee_detail
        except Exception as e:
            raise ValidationError(f"detail: {e}")


    # HÀM: Cập nhật nhật phí gửi xe
    @staticmethod
    def update_parking(parking_lot_id, v: Vehicle, ):
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
        log.status = ParkingStatus.OUT
        duration = (log.check_out - log.check_in).total_seconds() / 60
        log.duration_minutes = duration

        bookings = Booking.objects.filter(
            vehicle=v,
            lot_id=parking_lot_id,
            status=BookingStatus.PARKING,
            start_time__lt=now,
            end_time__gt=log.check_in
        ).order_by('start_time')

        total_prepaid = 0
        penalty_fee = 0

        # Danh sách các mốc thời gian bận (đã có booking)
        occupied_times = []

        if bookings.exists():
            for b in bookings:
                total_prepaid += b.fee

                b_start = max(log.check_in, b.start_time)
                b_end = min(now, b.end_time)
                occupied_times.append((b_start, b_end))

                if now > b.end_time and b.vehicle==b.slot.current_vehicle:
                    penalty_fee += 50000  # Mức phạt cố định cho việc chiếm dụng ô đặt trước

                b.status = BookingStatus.COMPLETED
                b.save()

        # TÌM KHOẢNG TRỐNG (Thời gian kh có trong booking)
        # duyệt từ lúc check_in đến check_out để tìm các kẽ hở
        extra_time_fee = 0

        last_check = log.check_in
        for b_start, b_end in occupied_times:
            if last_check < b_start:
                # Có khoảng trống từ last_check đến b_start
                fee, detail = ParkingLogService.calculate_fee(
                    log.fee_rule, parking_lot_id, last_check, b_start
                )
                extra_time_fee += fee
            # Nhảy mốc kiểm tra lên cuối booking này
            last_check = max(last_check, b_end)

        # Kiểm tra khoảng trống cuối cùng (từ booking cuối đến lúc check-out)
        if last_check < now - timedelta(minutes=5):
            fee, detail = ParkingLogService.calculate_fee(
                log.fee_rule, parking_lot_id, last_check, now
            )
            extra_time_fee += fee

        # Tổng hợp tài chính
        log.fee = total_prepaid + extra_time_fee + penalty_fee
        log.final_amount_to_pay = extra_time_fee + penalty_fee

        log.save()
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
                status=ParkingStatus.IN,
                check_in=datetime.now()
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
