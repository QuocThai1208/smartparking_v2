from rest_framework import serializers

from .MapSvgSerializers import MapSvgSerializer
from .parking_slot_serializers import SlotSerializer
from ..models import ParkingLot, MapSvg

class LotSerializer(serializers.ModelSerializer):
    owner_name = serializers.ReadOnlyField(source='owner.username')

    class Meta:
        model = ParkingLot
        fields = ['id', 'owner_name', 'name', 'address', 'latitude', 'longitude', 'moto_slots', 'car_slots', 'bus_slots', 'truck_slots']


class LotCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParkingLot
        fields = ['name', 'address', 'latitude', 'longitude', 'moto_slots', 'car_slots', 'bus_slots', 'truck_slots']

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['owner'] = user
        return super().create(validated_data)


class LotUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParkingLot
        fields = ['name', 'address', 'latitude', 'longitude', 'moto_slots', 'car_slots', 'bus_slots', 'truck_slots']

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['owner'] = user
        return super().create(validated_data)


class LotDetailSerializer(serializers.ModelSerializer):
    map_svgs = MapSvgSerializer(many=True, read_only=True)
    slots = SlotSerializer(many=True, read_only=True)
    owner_name = serializers.ReadOnlyField(source='owner.username')
    class Meta:
        model = ParkingLot
        fields = ['id', 'owner_name', 'name', 'address', 'latitude', 'longitude', 'moto_slots', 'car_slots',
                  'bus_slots', 'truck_slots', 'map_svgs', 'slots']

class LotSelectSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParkingLot
        fields = ['id', 'name']