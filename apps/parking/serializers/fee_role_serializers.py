from rest_framework import serializers
from ..models import FeeRule


class FeeRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeRule
        fields = ['id', 'fee_type', 'amount', 'active', 'effective_from', 'effective_to']