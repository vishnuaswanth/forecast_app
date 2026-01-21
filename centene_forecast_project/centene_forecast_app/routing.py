from django.urls import re_path
from .consumers import UploadProgressConsumer, TestConsumer
websocket_urlpatterns = [
   re_path(r'ws/up/$', TestConsumer.as_asgi()),
]
