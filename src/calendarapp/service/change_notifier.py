import logging

from jakarta.inject import Singleton
from micronaut.cache import CacheManager
from micronaut.transaction.annotation import TransactionalEventListener

from ..domain.event_change import EventChange
from ..web.live_updates_socket import LiveUpdatesSocket
from .text_service import TextService

LOG = logging.getLogger(__name__)


@Singleton
class ChangeNotifier:
    """Forwards EventChange application events to the WebSocket once the transaction has committed."""

    def __init__(self, socket: LiveUpdatesSocket, texts: TextService, cache_manager: CacheManager):
        self.socket = socket
        self.texts = texts
        self.cache_manager = cache_manager

    @TransactionalEventListener
    def on_change(self, change: EventChange) -> None:
        if change.type.startswith("category-"):
            # @CacheInvalidate runs only when the service method returns; clear the cache now so clients
            # that react to this message never re-read (and re-cache) the old list.
            self.cache_manager.getCache("categories").invalidateAll()
        message = self.texts.change(change.type, change.title)
        LOG.info(message)
        self.socket.send({"type": change.type, "id": change.id, "message": message})
