from django.urls import re_path
import sys
from . import consumers

print("Loading chat/routing.py - WebSocket patterns:", file=sys.stderr)
print(" - ws/chat/(?P<conversation_id>\\d+)/ -> ChatConsumer", file=sys.stderr)

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<conversation_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
] 