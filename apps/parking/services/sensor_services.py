from django.db import transaction

from apps.parking.models import Booking, BookingStatus, ParkingSlot

class SensorService:
    @staticmethod
    def process_sensor_signal(is_occupied, vehicle_id, slot_id):
        try:
            if not is_occupied:
                return False

            try:
                slot = ParkingSlot.objects.get(id=slot_id)
            except ParkingSlot.DoesNotExist:
                raise ValueError({"detail": "Không tìm thấy vị trí gửi xe."})

            booking = Booking.objects.filter(
                slot_id=slot_id,
                vehicle_id=vehicle_id,
                status=BookingStatus.ACTIVE
            ).first()

            if booking:
                with transaction.atomic():
                    booking.status = BookingStatus.PARKING
                    booking.save()
                    if slot:
                        slot.is_occupied = True
                        slot.current_vehicle_id=vehicle_id
                    slot.save()
                    return True
            if slot and is_occupied:
                slot.is_occupied = False
                slot.current_vehicle_id=None
                slot.save()
                return True
            return False
        except Exception as e:
            raise ValueError(e)