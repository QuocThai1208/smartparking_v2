from channels.generic.websocket import AsyncWebsocketConsumer
import json



class AnalyticsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("analytics_group", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("analytics_group", self.channel_name)

    # Hàm nhận tin nhắn từ group và gửi xuống Client
    async def send_update(self, event):
        await self.send(text_data=json.dumps(event["data"]))


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        print(f"truy xuất user thành công user_id={self.user_id}")

        if self.user_id:
            self.group_name = f"notification_user_{self.user_id}"
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
            print(f"Đã kết nối thành công cho user {self.user_id}")
        else:
            await self.close() # từ chối nếu chưa đăng nhập

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # Hàm nhận tin nhắn từ group và gửi xuống Client
    async def send_update(self, event):
        await self.send(text_data=json.dumps(event["data"]))