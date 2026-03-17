from rest_framework import serializers
from ..services.vehicle_face_service import VehicleFaceService
from apps.parking.models import VehicleFace


class VehicleFaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleFace
        fields = ['id', 'vehicle', 'owner_name', 'face_img', 'is_default', 'created_date']


class FaceRegistrationInputSerializer(serializers.Serializer):
    vehicle_id = serializers.IntegerField(help_text="ID của xe cần đăng ký mặt")
    owner_name = serializers.CharField(max_length=100, help_text="Tên người lái")
    face_img = serializers.ImageField(help_text="Ảnh chụp khuôn mặt")
    is_default = serializers.BooleanField(default=False)

    def create(self, validated_data):
        service = VehicleFaceService()
        return service.register_new_face(**validated_data)

    #Kết quả trả về
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['face_img'] = instance.image.url if instance.image else ''
        return VehicleFaceSerializer(data).data