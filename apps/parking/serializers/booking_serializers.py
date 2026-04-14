from rest_framework import serializers

from apps.parking.models import Booking, FeeRule
from apps.parking.services.booking_services import BookingService
from apps.parking.services.parking_log_service import ParkingLogService


class BookingSerializer(serializers.ModelSerializer):
    start_time = serializers.SerializerMethodField()
    end_time = serializers.SerializerMethodField()
    expired_time = serializers.SerializerMethodField()
    lot_name = serializers.ReadOnlyField(source='lot.name')
    user_full_name = serializers.ReadOnlyField(source='user.full_name')
    vehicle_name = serializers.ReadOnlyField(source='vehicle.name')
    slot_number = serializers.ReadOnlyField(source='slot.slot_number')

    class Meta:
        model = Booking
        fields = ['id', 'user_full_name', 'vehicle_name', 'fee', 'slot_number', 'lot_name', 'status', 'start_time', 'end_time', 'expired_time']


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
        fields = ['vehicle', 'lot', 'start_time', 'end_time']

    def create(self, validated_data):
        user = self.context.get('request').user
        booking = BookingService.create_booking(user, **validated_data)
        return booking


class BookingReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ['vehicle', 'lot', 'start_time', 'end_time']

    def to_representation(self, instance):

        lot_obj = instance.get('lot')
        vehicle = instance.get('vehicle')
        vehicle_type = vehicle.type

        fee_rule = FeeRule.objects.filter(fee_type=vehicle_type, parking_lot=lot_obj).first()
        data = super().to_representation(instance)
        if fee_rule:
            final_fee, fee_detail = ParkingLogService.calculate_fee(fee_rule, instance.get("start_time"), instance.get("end_time"))
            data['final_fee'] = final_fee
            data['fee_detail'] = fee_detail
            return data
        raise serializers.ValidationError({"detail": "Dữ liệu không hợp lệ."})


