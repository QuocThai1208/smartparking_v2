from datetime import date, datetime
import math
import calendar

from django.db.models.functions import ExtractHour
from django.utils import timezone
from typing import Optional, Any

from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404

from ...finance.models import PaymentType
from ...finance.services.payment_service import PaymentService
from ...users.models import UserRole, User
from ..models import ParkingLog, ParkingStatus, Vehicle, FeeRule, FeeType, VehicleFace, Booking, BookingStatus, \
    ParkingLot
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
    def get_parking_current_stats(lot_id: int, vehicle_type: FeeType):
        mapping = {
            "MOTORCYCLE": "moto_slots",
            "CAR": "car_slots",
            "TRUCK": "truck_slots",
            "BUS": "bus_slots",
        }

        field_name = mapping.get(vehicle_type)

        if not lot_id:
            raise ValidationError({"lot_id": f"Bãi xe không hợp lệ."})

        if not field_name:
            raise ValidationError({"vehicle_type": f"Loại xe {vehicle_type} không hợp lệ"})

        lot = get_object_or_404(ParkingLot, id=lot_id)
        total_slots=getattr(lot, field_name)

        occupied = ParkingLog.objects.filter(status=ParkingStatus.IN, vehicle__type=vehicle_type).count()
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
    @staticmethod
    def get_fee_detail(log: ParkingLog):
        booking = log.booking
        full_detail = []
        if booking:
            booking_fee, fee_booking_detail = ParkingLogService.calculate_fee(log.fee_rule,
                                                                              booking.start_time,
                                                                              booking.end_time)
            for item in fee_booking_detail:
                item['type'] = "Phí đặt chỗ"
                full_detail.append(item)

            penalty_fee = 0
            if booking.end_time < log.check_out:
                base_penalty, fee_penalty_detail = ParkingLogService.calculate_fee(log.fee_rule, booking.end_time, log.check_out)
                penalty_fee = base_penalty * 3
                for item in fee_penalty_detail:
                    item['type'] = "Phí phạt đỗ quá hạn"
                    item['unit_price'] *= 3
                    item['sub_total'] *= 3
                    full_detail.append(item)

            final_fee = booking_fee + penalty_fee
            return final_fee, full_detail
        else:
            actual_fee, fee_detail = ParkingLogService.calculate_fee(
                log.fee_rule, log.check_in, log.check_out
            )
            for item in fee_detail:
                item['type'] = "Phí vãng lai"

            return actual_fee, fee_detail

    # HÀM: tính phí giữ xe
    @staticmethod
    def calculate_fee(fee_rule: FeeRule, start_time, end_time,):
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
                segment_hours = math.ceil((segment_minutes - 5) / 60) # cho khách hàng 5p để di chuyển từ ô đỗ ra cổng

                unit_price = fee_rule.amount  # Giá mỗi giờ
                day_fee = segment_hours * unit_price
                final_fee += day_fee

                fee_detail.append({
                    "date": current_time.strftime("%d/%m/%Y"),
                    "period": f"{current_time.strftime('%H:%M')} - {segment_end.strftime('%H:%M')}",
                    "hours": segment_hours,
                    "unit_price": unit_price,
                    "sub_total": day_fee
                })

                # Nhảy sang ngày tiếp theo
                current_time = segment_end

            return int(final_fee), fee_detail
        except Exception as e:
            raise ValidationError(f"detail: {e}")


    # HÀM: Cập nhật nhật phí gửi xe
    @staticmethod
    def update_parking(parking_lot_id, v: Vehicle):
        try:
            log = (
                ParkingLog.objects
                .select_for_update()  # khóa bảng ghi cho đến khi hoàn tất
                .get(user=v.user,
                     parking_lot_id=parking_lot_id,
                     vehicle=v,
                     status=ParkingStatus.IN)
            )
        except  ParkingLog.DoesNotExist:
            return False, "Không tìm thấy xe lượt vào bãi"
        print("tìm thấy log.")

        now = timezone.now()
        log.check_out = now
        log.status = ParkingStatus.OUT
        duration = (log.check_out - log.check_in).total_seconds() // 60
        log.duration_minutes = duration

        booking = Booking.objects.filter(
            vehicle=v,
            lot_id=parking_lot_id,
            status=BookingStatus.PARKING,
        ).first()

        fees_detail = [] # danh sách các chi phí cần thanh toán
        final_amount_to_pay = 0
        if booking:
            print("tìm thấy booking.")
            total_fee = booking.fee
            if log.check_out > booking.end_time:
                base_penalty, _ = ParkingLogService.calculate_fee(log.fee_rule, booking.end_time, log.check_out)
                fee_penalty = base_penalty * 3 # Phạt tiền đỗ gấp 3 lần giá gốc
                final_amount_to_pay = fee_penalty
                log.fee = total_fee + fee_penalty
                fees_detail.append({'fee': fee_penalty, 'type': PaymentType.PENALTY, 'description': 'Thanh toán phí phạt đỗ quá hạn'})
            else:
                # Đỗ đúng giờ hoặc ra sớm
                final_amount_to_pay = 0
                log.fee = total_fee
            booking.status = BookingStatus.COMPLETED
            booking.save()
            print("Cập nhật booking thành công.")
        else:
            print("Không tìm thấy booking.")
            actual_fee, _ = ParkingLogService.calculate_fee(
                log.fee_rule,
                log.check_in,
                log.check_out
            )
            print(f"Tính phí thành công {actual_fee}.")
            log.fee = actual_fee
            final_amount_to_pay = actual_fee
            fees_detail.append({'fee': actual_fee, 'type': PaymentType.BASE, 'description': 'Thanh toán phí đỗ'})
        log.final_amount_to_pay = final_amount_to_pay
        log.save()
        print("Lưu log thành công.")
        return True, log, fees_detail

    # HÀM: Tạo mới nhật kí gửi xe
    @staticmethod
    def create_parking_log(parking_lot_id, v: Vehicle, fee_type: FeeType, face: VehicleFace, booking: Booking) -> tuple[bool, str]:
        try:
            exist_p = ParkingLog.objects.filter(user=v.user, vehicle=v, status=ParkingStatus.IN).first()
            if exist_p:
                return False, 'Phương tiện này đang có trong bãi'
            p = ParkingLog.objects.create(
                parking_lot_id=parking_lot_id,
                booking=booking,
                user=v.user,
                vehicle_face=face,
                vehicle=v,
                fee_rule=FeeRule.objects.get(fee_type=fee_type),
                status=ParkingStatus.IN,
                check_in=datetime.now()
            )
            if p:
                return True, f"Xin mời vào vị trí {booking.slot.slot_number}" if booking else "Xin mời vào."
            return False, "Không hợp lệ."
        except Exception as e:
            print("Lỗi: ", e)

    @staticmethod
    def get_top5_history():
        logs = ParkingLog.objects.all().order_by('-id')[:10]
        return logs

    @staticmethod
    def get_my_logs(user: User, day: int, month: int, year: int, parking_lot_id: int):
        df, dt = ParkingLogService.create_df_dt(day, month, year)

        filters: dict[str, Any] = {
            'user': user,
            'active': True
        }

        if df:
            filters['created_date__date__gte'] = df
        if dt:
            filters['created_date__date__lte'] = dt
        if parking_lot_id:
            filters['parking_lot_id'] = parking_lot_id

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
