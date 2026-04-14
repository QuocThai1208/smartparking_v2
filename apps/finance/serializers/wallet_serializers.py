from rest_framework import serializers
from ..models import Wallet


class WalletSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = ['user', 'balance', 'active']

    def get_user(self, obj):
        return obj.user.full_name


class DepositSerializer(serializers.Serializer):
    amount = serializers.IntegerField()
    description = serializers.CharField(default='Nạp tiền vào ví', allow_blank=True, allow_null=True)