from rest_framework import serializers
from ..models import ParkingLog


class ParkingLogSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField(read_only=True)
    check_in = serializers.SerializerMethodField()
    check_out = serializers.SerializerMethodField()
    vehicle = serializers.SerializerMethodField()
    fee_rule = serializers.SerializerMethodField()

    class Meta:
        model = ParkingLog
        fields = ['id', 'user', 'vehicle', 'fee_rule', 'check_in', 'check_out', 'duration_minutes', 'fee', 'status']
        extra_kwargs = {
            'duration_minutes': { 'read_only': True },
            'check_in': { 'read_only': True }
        }

    def get_fee_rule(self, obj):
        return obj.fee_rule.fee_type

    def get_vehicle(self, obj):
        return {
            "name": obj.vehicle.name,
            "license_plate": obj.vehicle.license_plate
        }

    def get_user(self, obj):
        return obj.user.full_name

    def get_check_in(self, obj):
        return obj.check_in.strftime("%H:%M:%S %d/%m/%Y")

    def get_check_out(self, obj):
        return obj.check_out.strftime("%H:%M:%S %d/%m/%Y")


class LogHistoryAdminSerializer(serializers.ModelSerializer):
    check_in = serializers.SerializerMethodField()
    check_out = serializers.SerializerMethodField()
    owner_name = serializers.CharField(source='vehicle_face.owner_name', read_only=True)
    plate = serializers.CharField(source='vehicle.license_plate', read_only=True)

    class Meta:
        model = ParkingLog
        fields = ['id', 'plate', 'check_in', 'check_out', 'owner_name']

    def get_check_in(self, obj):
        if obj.check_in:
            return obj.check_in.strftime("%H:%M:%S %d/%m/%Y")
        return None

    def get_check_out(self, obj):
        if obj.check_out:
            return obj.check_out.strftime("%H:%M:%S %d/%m/%Y")
        return None


class LogDetailAdminSerializer(serializers.ModelSerializer):
    check_in = serializers.SerializerMethodField()
    check_out = serializers.SerializerMethodField()
    owner_name = serializers.CharField(source='vehicle_face.owner_name', read_only=True)
    plate = serializers.CharField(source='vehicle.license_plate', read_only=True)
    vehicle_image = serializers.CharField(source='vehicle.image.url', read_only=True)
    vehicle_name = serializers.CharField(source='vehicle.name', read_only=True)

    class Meta:
        model = ParkingLog
        fields = ['id', 'plate', 'owner_name', 'vehicle_image', 'vehicle_name', 'duration_minutes', 'fee', 'status', 'check_in', 'check_out' ]

    def get_check_in(self, obj):
        if obj.check_in:
            return obj.check_in.strftime("%H:%M:%S %d/%m/%Y")
        return None

    def get_check_out(self, obj):
        if obj.check_out:
            return obj.check_out.strftime("%H:%M:%S %d/%m/%Y")
        return None
