from django.utils import timezone
from rest_framework import serializers
from ..models import FeeRule
from ..services.price_services import PriceEngine


class FeeRuleSerializer(serializers.ModelSerializer):
    parking_lot_id = serializers.ReadOnlyField(source='parking_lot.id')

    class Meta:
        model = FeeRule
        fields = ['id', 'parking_lot_id', 'fee_type', 'amount', 'active', 'effective_from', 'effective_to']

    def validate(self, attrs):
        # Ưu tiên dữ liệu mới gửi lên, nếu không có thì lấy từ instant đang update
        fee_type = attrs.get('fee_type')
        if fee_type is None and self.instance:
            fee_type = self.instance.fee_type

        active = attrs.get('active')
        if active is None and self.instance:
            active = self.instance.active
        # Nếu tạo mới hoàn toàn mà không gửi active, mặc định là True theo Model
        elif active is None:
            active = True

        if active:
            query = FeeRule.objects.filter(fee_type=fee_type, active=True)
            if self.instance:
                query = query.exclude(pk=self.instance.pk)
            if query.exists():
                raise serializers.ValidationError({
                    "fee_type": f"Loại xe {fee_type} đã có bảng giá đang áp dụng."
                })
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        date = self.context.get('date')

        if date:
            parking_lot_id = data.get('parking_lot_id')
            amount = data.get('amount')
            price_info = PriceEngine.calculate_final_price(parking_lot_id, amount, date)

            data['surcharge'] =  price_info['surcharge']
            data['total_fee'] =  price_info['total_fee']
            data['note'] =  price_info['note']

        return data
