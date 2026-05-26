from rest_framework import serializers

from apps.parking.models import SubscriptionPackage


class BaseSubscriptionPackageSerializer(serializers.ModelSerializer):
    owner_name = serializers.ReadOnlyField(source='owner.username')
    parking_lot_name = serializers.ReadOnlyField(source='parking_lot.name')


    class Meta:
        model = SubscriptionPackage
        fields = ('id', 'owner_name', 'parking_lot_name', 'vehicle_type', 'package_name', 'price', 'active')


class CreateSubscriptionPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPackage
        fields = ('parking_lot', 'vehicle_type', 'package_name', 'price')

    def save(self, **kwargs):
        parking_lot = self.validated_data.get('parking_lot')
        vehicle_type = self.validated_data.get('vehicle_type')

        exists = SubscriptionPackage.objects.filter(
            parking_lot=parking_lot,
            vehicle_type=vehicle_type,
            active=True
        ).exists()

        if exists:
            raise serializers.ValidationError(
                {"detail": f"Loại xe '{vehicle_type}' đã có một gói cước tháng đang hoạt động trong bãi này."}
            )
        user = self.context['request'].user
        return super().save(owner=user, **kwargs)


class UpdateSubscriptionPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPackage
        fields = ('package_name', 'price', 'active')
