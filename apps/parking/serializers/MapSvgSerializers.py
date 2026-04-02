from rest_framework import serializers

from apps.parking.models import MapSvg

class MapSvgSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['map_svg'] = instance.map_svg.url if instance.map_svg else None
        return data

    class Meta:
        model = MapSvg
        fields = ['id', 'map_svg', 'floor', 'floor_display']

class MapSvgCreateSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['map_svg'] = instance.map_svg.url if instance.map_svg else None
        return data

    class Meta:
        model = MapSvg
        fields = ('map_svg', 'floor', 'floor_display')