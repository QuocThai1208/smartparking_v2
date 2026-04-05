from rest_framework import serializers

from apps.parking.models import ParkingSlot, BookingStatus


class SlotSerializer(serializers.ModelSerializer):
    is_booked = serializers.SerializerMethodField()
    class Meta:
        model = ParkingSlot
        fields = ('id', 'slot_number', 'vehicle_type', 'is_vip', 'is_occupied', 'is_booked')

    def get_is_booked(self, obj):
        return obj.bookings.filter(status__in=[BookingStatus.ACTIVE]).exists()


class SlotCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParkingSlot
        fields = ('slot_number', 'vehicle_type', 'is_vip')
