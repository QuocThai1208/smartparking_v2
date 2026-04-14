from rest_framework import serializers

from apps.parking.models import ParkingSlot, BookingStatus


class SlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParkingSlot
        fields = ('id', 'slot_number', 'vehicle_type', 'is_occupied')


class SlotCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParkingSlot
        fields = ('slot_number', 'vehicle_type')
