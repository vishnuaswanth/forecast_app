"""
WebSocket URL routing for chat_app.
Defines WebSocket endpoints for real-time chat communication.
"""
from django.urls import re_path, path
from . import consumers

websocket_urlpatterns = [
    # Main chat WebSocket endpoint
    path('ws/chat/', consumers.ChatConsumer.as_asgi()),

    # Test WebSocket endpoint for debugging
    re_path(r'ws/test/$', consumers.TestConsumer.as_asgi()),
]
