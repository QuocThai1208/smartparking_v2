from rest_framework import serializers

from apps.parking.models import PublicHoliday


class BasePublicHolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicHoliday
        fields = '__all__'