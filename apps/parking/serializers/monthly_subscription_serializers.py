from rest_framework import serializers
from django.utils import timezone
from apps.parking.models import MonthlySubscription, MonthlyStatus
from apps.parking.services.monthly_subscription_services import create_monthly_subscription


class BaseMonthlySubscriptionSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username')
    class Meta:
        model = MonthlySubscription
        fields = ('id', 'username', 'vehicle', 'package', 'start_date', 'price', 'end_date', 'status')

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        if instance.vehicle:
            representation['vehicle'] = {
                'name': instance.vehicle.name,
                'license_plate': instance.vehicle.license_plate
            }
        else:
            representation['vehicle'] = None

        if instance.package:
            representation['package'] = {
                'package_name': instance.package.package_name,
                'parking_lot_name': instance.package.parking_lot.name if instance.package.parking_lot else "Không rõ"
            }
        else:
            representation['package'] = None
        return representation


class CreateMonthlySubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthlySubscription
        fields = ('vehicle', 'package')

    def validate(self, attrs):
        vehicle = attrs.get('vehicle')
        package = attrs.get('package')
        today = timezone.now().date()

        existing_active = MonthlySubscription.objects.filter(
            vehicle=vehicle,
            status=MonthlyStatus.ACTIVE,
            start_date__lte=today,
            end_date__gte=today
        ).exists()

        if existing_active:
            raise serializers.ValidationError({
                "detail": "Phương tiện này hiện đang có một gói vé tháng đang hoạt động và còn thời hạn!"
            })

        if vehicle.type != package.vehicle_type:
            raise serializers.ValidationError({
                "detail": f"Gói cước này chỉ áp dụng cho loại xe '{package.get_vehicle_type_display()}', "
                           f"không khớp với loại xe '{vehicle.get_type_display()}' của phương tiện này."
            })

        return attrs

    def save(self, **kwargs):
        user = self.context['request'].user
        vehicle = self.validated_data.get('vehicle')
        package = self.validated_data.get('package')
        monthly_subscription, is_success, msg = create_monthly_subscription(user=user, vehicle=vehicle, package=package)

        if not is_success:
            raise serializers.ValidationError({
                "detail": f"Thanh toán thất bại: {msg}"
            })

        return monthly_subscription