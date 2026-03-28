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