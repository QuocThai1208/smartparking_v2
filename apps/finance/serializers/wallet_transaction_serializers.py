from rest_framework import serializers
from ..models import WalletTransaction


class WalletTransactionSerializer(serializers.ModelSerializer):
    created_date = serializers.SerializerMethodField()

    class Meta:
        model = WalletTransaction
        fields = ['id', 'wallet', 'amount', 'transaction_type', 'description', 'created_date']

    def get_created_date(self, obj):
        return obj.created_date.strftime("%H:%M:%S %d/%m/%Y")