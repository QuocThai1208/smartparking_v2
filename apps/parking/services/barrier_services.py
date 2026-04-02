from django.utils import timezone

from apps.parking.models import Booking, BookingStatus


class BarrierService:
    @staticmethod
    def send_signal_to_hardware(open_status, vehicle_id, barrier_id):
        pass

    @staticmethod
    def open_barrier_event(open_flag, barrier_id, user_id, slot_id):
        # kiểm tra booking
        now = timezone.now()

        booking = Booking.objects.filter(
            user_id=user_id,
            slot_id=slot_id,
            status=BookingStatus.CHECK_IN,
            start_time__lte=now,  # Đã đến giờ hoặc sắp đến giờ
            expired_time__gte=now  # Chưa bị quá hạn
        ).first()

        if not booking:
            return False, "Bạn chưa đặt chỗ cho vị trí này."

        vehicle_id = booking.vehicle.id

        # Yêu cầu phần cứng mở cổng
        if open_flag:
            BarrierService.send_signal_to_hardware(True, vehicle_id, barrier_id)

        booking.status = BookingStatus.PARKING
        booking.save()
        return True, "Mở cổng thành công."
