from rest_framework import serializers
from ..models import FeeRule


class FeeRuleSerializer(serializers.ModelSerializer):

    class Meta:
        model = FeeRule
        fields = ['id', 'fee_type', 'amount', 'active', 'effective_from', 'effective_to']

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