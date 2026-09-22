from django.urls import path

from .consumers import ChatConsumer, UserChatConsumer


websocket_urlpatterns = [
    path(
        "ws/chat/user/",
        UserChatConsumer.as_asgi(),
    ),
    path(
        "ws/chat/<int:conversation_id>/",
        ChatConsumer.as_asgi(),
    ),
]