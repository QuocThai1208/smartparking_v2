from django.db import transaction

from apps.parking.models import Booking, BookingStatus, ParkingSlot
from apps.parking.task import cancel_task_check_booking_expired


class SensorService:
    @staticmethod
    def process_sensor_signal(is_occupied, vehicle_id, slot_id):
        try:
            if not is_occupied:
                return False

            booking = Booking.objects.filter(
                slot_id=slot_id,
                vehicle_id=vehicle_id,
                status=BookingStatus.PARKING
            ).first()
            if booking:
                with transaction.atomic():
                    booking.status = BookingStatus.COMPLETED
                    booking.save()

                    cancel_task_check_booking_expired(booking)

                    slot = ParkingSlot.objects.get(id=slot_id)
                    if slot:
                        slot.is_occupied = True
                    slot.save()

                    return True
            return False
        except Exception as e:
            raise ValueError(e)