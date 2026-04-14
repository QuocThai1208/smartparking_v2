from django.urls import re_path

from apps.parking import consumers

websocket_urlpatterns = [
    re_path(r'ws/analytics/$', consumers.AnalyticsConsumer.as_asgi()),
    re_path(r'ws/notification/(?P<user_id>\d+)/$', consumers.NotificationConsumer.as_asgi()),
]