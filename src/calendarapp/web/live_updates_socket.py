import json
import logging

from micronaut.websocket import WebSocketBroadcaster, WebSocketSession
from micronaut.websocket.annotation import OnClose, OnMessage, OnOpen, ServerWebSocket

LOG = logging.getLogger(__name__)


def _json_default(value):
    # values that went through Java arrive as foreign objects, e.g. a null id is a ForeignNone
    text = str(value)
    return None if text in ("None", "null") else text


@ServerWebSocket("/ws/events")
class LiveUpdatesSocket:
    """Pushes calendar changes and reminders to every open browser tab."""

    def __init__(self, broadcaster: WebSocketBroadcaster):
        self.broadcaster = broadcaster

    @OnOpen()
    def on_open(self, session: WebSocketSession) -> None:
        LOG.info("Live updates client connected: %s", session.getId())

    @OnMessage
    def on_message(self, message: str, session: WebSocketSession) -> None:
        pass  # clients only listen

    @OnClose()
    def on_close(self, session: WebSocketSession) -> None:
        LOG.info("Live updates client disconnected: %s", session.getId())

    def send(self, payload: dict) -> None:
        self.broadcaster.broadcastSync(json.dumps(payload, default=_json_default))
