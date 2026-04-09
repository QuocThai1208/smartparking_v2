from datetime import timedelta
from django.utils import timezone

from django.db import transaction

from apps.parking.models import Vehicle, ParkingSlot, Booking, FeeRule, BookingStatus, ParkingStatus, ParkingLog, \
    FeeType, ParkingLot
from .parking_log_service import ParkingLogService
from ..task import check_booking_expired, notify_overtime_booking
from ...finance.models import PaymentType
from ...finance.services.payment_service import PaymentService
from ...users.models import User, UserRole
from rest_framework import serializers


class BookingService:

    @staticmethod
    def booking_validation(user, vehicle, lot, start_time, end_time):
        now = timezone.now()

        if start_time >= end_time:
            raise serializers.ValidationError({"end_time": "Thời gian kết thúc phải sau thời gian bắt đầu."})

        max_booking_time = now + timedelta(minutes=10)
        if start_time > max_booking_time:
            raise serializers.ValidationError({
                "start_time": f"Chỉ được đặt chỗ trễ nhất đến {max_booking_time.strftime('%H:%M')}"
            })

        if start_time < (now - timedelta(minutes=2)):
            raise serializers.ValidationError({"start_time": "Thời gian bắt đầu không được ở quá khứ."})

        duration_hours = (end_time - start_time).total_seconds() / 3600
        if duration_hours < 1:
            raise serializers.ValidationError({"time": "Thời gian thuê tối thiểu là 1 giờ."})

        if user.user_role != UserRole.CUSTOMER:
            raise serializers.ValidationError({"user": "Chỉ khách hàng mới được đặt vị trí."})

        if user != vehicle.user:
            raise serializers.ValidationError({"vehicle": "Bạn không phải chủ sở hữu phương tiện này."})

        # kiểm tra booking chéo
        if Booking.objects.filter(
                lot=lot,
                vehicle=vehicle,
                status=BookingStatus.ACTIVE,
                start_time__lte=end_time,
                end_time__gte=start_time,

        ).exists():
            raise serializers.ValidationError({"vehicle": f"Xe này hiện đã có lịch đặt chỗ trong khung giờ bạn chon."})

        # kiểm tra sức chứa thực tế
        slot_mapping = {
            FeeType.CAR: lot.car_slots,
            FeeType.BUS: lot.bus_slots,
            FeeType.TRUCK: lot.truck_slots,
        }
        total_slots = slot_mapping.get(vehicle.type, 0) # tổng chỗ theo loại của phương tiện
        # số chỗ hiện tại có trong bãi
        current_occupancy = ParkingLog.objects.filter(
            parking_lot=lot,
            status=ParkingStatus.IN,
            vehicle__type=vehicle.type).count()
        # số chỗ các xe sắp đến
        pending_bookings = Booking.objects.filter(
            lot=lot,
            vehicle__type=vehicle.type,
            status=BookingStatus.ACTIVE,
        ).count()

        if (current_occupancy + pending_bookings) >= total_slots:
            raise serializers.ValidationError({"lot": "Bãi xe hiện đã hết suất đỗ khả dụng."})

    @staticmethod
    def create_booking(user: User, vehicle: Vehicle, lot: ParkingLot, start_time, end_time):
        BookingService.booking_validation(user=user,
                                          vehicle=vehicle,
                                          lot=lot,
                                          start_time=start_time,
                                          end_time=end_time)

        fee_rule = FeeRule.objects.filter(
            parking_lot=lot,
            fee_type=vehicle.type,
            active=True,
        ).first()

        if not fee_rule:
            raise serializers.ValidationError({"fee": "Bãi xe chưa cấu hình bảng phí cho loại xe này."})

        final_fee, _ = ParkingLogService.calculate_fee(fee_rule, start_time, end_time)

        with transaction.atomic():
            try:
                ok, msg = PaymentService.create_payment(
                    user,
                    final_fee,
                    f'Thanh toán đặt chỗ bãi {lot.name} cho xe {vehicle.license_plate}',
                    PaymentType.BASE)
                if not ok:
                    raise serializers.ValidationError(msg)
                booking = Booking.objects.create(
                    user=user,
                    vehicle=vehicle,
                    lot=lot,
                    start_time=start_time,
                    end_time=end_time,
                    expired_time=start_time + timedelta(minutes=10),
                    fee=final_fee,
                    status=BookingStatus.ACTIVE
                )

                # eta yêu cầu thời gian dạng UTC
                task = check_booking_expired.apply_async(
                    args=[booking.id],
                    eta=booking.expired_time
                )

                overtime_task = notify_overtime_booking.apply_async(
                    args=[booking.id],
                    eta=booking.end_time
                )

                booking.task_id = task.id
                booking.overtime_task_id = overtime_task.id
                booking.save()
                return booking
            except Exception as e:
                raise serializers.ValidationError({"system": f"Lỗi hệ thống khi tạo đơn đặt: {str(e)}"})
