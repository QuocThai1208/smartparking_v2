from rest_framework import serializers

from apps.parking.models import PriceStrategyTemplate


class PriceStrategySerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceStrategyTemplate
        fields = "__all__"