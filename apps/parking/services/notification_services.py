from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from apps.parking.models import NotificationTypes, Notification
from apps.parking.serializers.notification_serializers import NotificationBaseSerializer


def create_and_send_notification(user_id: int, title: str, content: str, notification_type:NotificationTypes):
    notification = Notification.objects.create(
        user_id=user_id,
        title=title,
        content=content,
        notification_type=notification_type)

    channel_layer = get_channel_layer()
    new_data = {
        "type": "notification",
        "result": NotificationBaseSerializer(notification).data
    }

    async_to_sync(channel_layer.group_send)(
        f"notification_user_{user_id}",
        {
            "type": "send_update",
            "data": new_data
        }
    )
