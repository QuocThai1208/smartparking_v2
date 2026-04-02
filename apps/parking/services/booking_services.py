from datetime import timedelta
from django.utils import timezone

from django.db import transaction

from apps.parking.models import Vehicle, ParkingSlot, Booking, FeeRule, BookingStatus
from ..task import check_booking_expired
from ...finance.services.payment_service import PaymentService
from ...users.models import User, UserRole
from rest_framework import serializers


class BookingService:
    @staticmethod
    def is_slot_available(slot, start_time, end_time):
        filters = {
            "slot": slot,
            "status__in": ['pending', 'active'],
            "start_time__lte": end_time,
            "end_time__gte": start_time,
        }
        overlapping_bookings = Booking.objects.filter(**filters)
        return not overlapping_bookings.exists()

    @staticmethod
    def booking_validation(user, vehicle, slot, start_time, end_time):
        now = timezone.now()

        if start_time >= end_time:
            raise serializers.ValidationError({"end_time": "Thời gian kết thúc phải sau thời gian bắt đầu."})

        if start_time < (now - timedelta(minutes=5)):
            raise serializers.ValidationError({"start_time": "Thời gian bắt đầu không được ở quá khứ."})

        duration_hours = (end_time - start_time).total_seconds() / 3600
        if duration_hours < 1:
            raise serializers.ValidationError({"time": "Thời gian thuê tối thiểu là 1 giờ."})

        if user.user_role != UserRole.CUSTOMER:
            raise serializers.ValidationError({"user": "Chỉ khách hàng mới được đặt vị trí."})

        if user != vehicle.user:
            raise serializers.ValidationError({"vehicle": "Bạn không phải chủ sở hữu phương tiện này."})

        if vehicle.type != slot.vehicle_type:
            raise serializers.ValidationError({"slot": "Loại xe không phù hợp với vị trí đỗ này."})

        if not slot.is_vip:
            raise serializers.ValidationError({"slot": "Vị trí không hỗ trợ đặt trước."})

        if slot.is_occupied:
            raise serializers.ValidationError({"slot": "Vị trí này hiện đang có xe đỗ thực tế."})

        if not BookingService.is_slot_available(slot, start_time, end_time):
            raise serializers.ValidationError({"slot": "Vị trí này đã được người khác đặt trong khung giờ này."})

        # kiểm tra booking chéo
        if Booking.objects.filter(
                vehicle=vehicle,
                status=BookingStatus.ACTIVE,
                start_time__lte= end_time,
                end_time__gte= start_time,

        ).exists():
           raise serializers.ValidationError({"vehicle": f"Xe này hiện đã một vị trí khác trong khung giờ bạn chon."})

    @staticmethod
    def create_booking(user: User, vehicle: Vehicle, slot: ParkingSlot, start_time, end_time):
        BookingService.booking_validation(user=user,
                                          vehicle=vehicle,
                                          slot=slot,
                                          start_time=start_time,
                                          end_time=end_time)

        fee_rule = FeeRule.objects.filter(
            parking_lot=slot.parking_lot,
            fee_type=slot.vehicle_type,
            active=True,
        ).first()

        deposit_amount = fee_rule.amount / 2

        expired_time = start_time + timedelta(hours=0.5)

        with transaction.atomic():
            try:
                ok, msg = PaymentService.create_payment(user, deposit_amount,
                                                        f'Thanh toán phí đặt cho vị trí {slot.slot_number}')
                if not ok:
                    raise serializers.ValidationError(msg)
                booking = Booking.objects.create(
                    user=user,
                    vehicle=vehicle,
                    slot=slot,
                    start_time=start_time,
                    end_time=end_time,
                    expired_time=expired_time,
                    deposit_amount=deposit_amount,
                    status=BookingStatus.ACTIVE
                )

                # eta yêu cầu thời gian dạng UTC
                task = check_booking_expired.apply_async(
                    args=[booking.id],
                    eta=booking.expired_time
                )

                booking.task_id = task.id
                booking.save()
                return booking
            except Exception as e:
                raise serializers.ValidationError({"system": f"Lỗi hệ thống khi tạo đơn đặt: {str(e)}"})
