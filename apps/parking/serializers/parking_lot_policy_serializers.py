from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from apps.parking.models import ParkingLotPolicy


class BaseLotPolicySerializer(serializers.ModelSerializer):
    parking_lot_name = serializers.ReadOnlyField(source='parking_lot.name')
    strategy_code = serializers.ReadOnlyField(source='strategy.code')
    holiday_name = serializers.ReadOnlyField(source='holiday.name')

    class Meta:
        model=ParkingLotPolicy
        fields= ['id', 'parking_lot_name', 'strategy_code', 'holiday_name', 'multiplier']


class LotPolicyCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model=ParkingLotPolicy
        fields=['strategy', 'holiday', 'multiplier']

    def validate(self, data):
        lot_id = self.context['view'].kwargs.get('pk')
        strategy = data.get('strategy')
        holiday = data.get('holiday')

        # Ngược lại: Nếu strategy KHÔNG PHẢI là HOLIDAY mà lại chọn holiday
        if strategy and strategy.code != 'HOLIDAY' and holiday:
            raise serializers.ValidationError({
                "holiday": f"Chiến lược {strategy.code} không yêu cầu chọn ngày lễ cụ thể. Vui lòng để trống."
            })

        exists = ParkingLotPolicy.objects.filter(
            parking_lot_id=lot_id,
            strategy=strategy,
            holiday=holiday
        ).exists()

        if exists:
            raise serializers.ValidationError(
                "Chính sách giá cho chiến lược và ngày lễ này đã tồn tại trong bãi xe."
            )
        data['parking_lot_id'] = lot_id
        return data
