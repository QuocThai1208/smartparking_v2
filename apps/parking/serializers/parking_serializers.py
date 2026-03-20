from rest_framework import serializers


class ParkingBaseSerializer(serializers.Serializer):
    pass


class CheckInSerializer(serializers.Serializer):
    face_img = serializers.ImageField(help_text="Ảnh chụp khuôn mặt")
    image_front = serializers.ImageField(help_text="Ảnh chụp đầu xe")
    image_plate = serializers.ImageField(help_text="Ảnh biển số xe")


class CheckOutSerializer(serializers.Serializer):
    face_img = serializers.ImageField(help_text="Ảnh chụp khuôn mặt")
    image_front = serializers.ImageField(help_text="Ảnh chụp đầu xe")
    image_plate = serializers.ImageField(help_text="Ảnh biển số xe")
