from rest_framework import serializers
from ..models import Vehicle
from ..services.vehicle_service import VehicleService


# Serializer dùng để hiển thị (Dùng cho GET)
class VehicleSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = Vehicle
        fields = ['id', 'user_name', 'name', 'license_plate', 'type', 'image', 'is_approved', 'color', 'brand', 'active']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['image'] = instance.image.url if instance.image else ''
        return data


# Serializer dùng để tạo mới (Dùng cho POST)
class VehicleCreateSerializer(serializers.ModelSerializer):
    image_front = serializers.ImageField(write_only=True)
    image_plate = serializers.ImageField(write_only=True)

    class Meta:
        model = Vehicle
        fields = ['name', 'image_front', 'image_plate']

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user

        vehicle = VehicleService.create_vehicle(
            user=user,
            name=validated_data['name'],
            image_front=validated_data['image_front'],
            image_plate=validated_data['image_plate'],
        )
        return vehicle