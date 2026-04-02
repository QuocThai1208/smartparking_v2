from rest_framework import serializers

from apps.parking.models import Booking
from apps.parking.services.booking_services import BookingService

class BookingSerializer(serializers.ModelSerializer):
    start_time = serializers.SerializerMethodField()
    end_time = serializers.SerializerMethodField()
    expired_time = serializers.SerializerMethodField()
    user_full_name = serializers.ReadOnlyField(source='user.full_name')
    vehicle_name = serializers.ReadOnlyField(source='vehicle.name')
    slot_number = serializers.ReadOnlyField(source='slot.slot_number')

    class Meta:
        model = Booking
        fields = ['id', 'user_full_name', 'vehicle_name', 'slot_number', 'deposit_amount', 'status', 'start_time', 'end_time', 'expired_time']


    def get_start_time(self, obj):
        if obj.start_time:
            return obj.start_time.strftime("%H:%M:%S %d/%m/%Y")
        return None

    def get_end_time(self, obj):
        if obj.end_time:
            return obj.end_time.strftime("%H:%M:%S %d/%m/%Y")
        return None

    def get_expired_time(self, obj):
        if obj.expired_time:
            return obj.expired_time.strftime("%H:%M:%S %d/%m/%Y")
        return None

class BookingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ['vehicle', 'slot', 'start_time', 'end_time']

    def create(self, validated_data):
        user = self.context.get('request').user
        booking = BookingService.create_booking(user, **validated_data)
        return booking
