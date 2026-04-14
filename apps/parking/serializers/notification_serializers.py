from rest_framework import serializers

from apps.parking.models import Notification


class NotificationBaseSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    created_date = serializers.SerializerMethodField()
    class Meta:
        model = Notification
        fields = ['id', 'user', 'title', 'content', 'is_read', 'notification_type', 'created_date']

    def get_created_date(self, obj):
        return obj.created_date.strftime("%H:%M %d/%m/%Y")
