"""
ASGI config for core project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""
import os
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
import apps.parking.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

application = ProtocolTypeRouter({
    # Xử lý các request HTTP bình thường
    "http": django_asgi_app,

    # Xử lý các kết nối WebSocket
    "websocket": AuthMiddlewareStack(
        URLRouter(
            apps.parking.routing.websocket_urlpatterns
        )
    ),
})
