import os
from datetime import datetime
from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework import serializers
from ..models import Vehicle
# from ..services.yolo_detection import detect_vehicle

class VehicleSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField(read_only=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['image'] = instance.image.url if instance.image else ''
        return data

    class Meta:
        model = Vehicle
        fields = ['id', 'user', 'name', 'license_plate', 'vehicle_type', 'image', 'is_approved']
        extra_kwargs = {
            'user': {'read_only': True },
            'vehicle_type': {'read_only': True }
        }

    def get_user(self, obj):
        return obj.user.full_name

    def create(self, validated_data):
        user = self.context['request'].user
        image_file = validated_data.get('image')

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        ext = os.path.splitext(image_file.name)[1]  # lấy đuôi file
        new_filename = f"vehicle_{timestamp}{ext}"
        upload_dir = os.path.join(settings.MEDIA_ROOT, "vehicle")
        os.makedirs(upload_dir, exist_ok=True)
        save_path = os.path.join(upload_dir, new_filename)
        default_storage.save(save_path, image_file)

        try:
            # vehicle_type = detect_vehicle(save_path)
            vehicle_type = 0
            if not vehicle_type:
                raise serializers.ValidationError({'image': 'Không nhận diện được loại xe'})

            validated_data['user'] = user
            validated_data['vehicle_type'] = vehicle_type
            return super().create(validated_data)
        finally:
            if os.path.exists(save_path):
                os.remove(save_path)