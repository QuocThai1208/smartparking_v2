from apps.parking.models import ParkingSlot, BookingStatus


class SlotService():
    @staticmethod
    def is_available(slot: ParkingSlot) -> bool:
        return not slot.is_occupied and not slot.bookings.filter(status=BookingStatus.ACTIVE).exists()