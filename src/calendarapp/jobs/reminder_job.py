import logging
from datetime import datetime, timedelta

from jakarta.inject import Singleton
from micronaut.scheduling.annotation import Scheduled

from ..repository.event_repository import EventRepository
from ..service.text_service import TextService
from ..web.live_updates_socket import LiveUpdatesSocket

LOG = logging.getLogger(__name__)


@Singleton
class ReminderJob:
    def __init__(self, event_repository: EventRepository, socket: LiveUpdatesSocket, texts: TextService):
        self.event_repository = event_repository
        self.socket = socket
        self.texts = texts

    @Scheduled(fixedDelay="${calendar.reminder-check-interval:30s}", initialDelay="5s")
    def send_due_reminders(self) -> int:
        now = datetime.now().replace(microsecond=0)
        sent = 0
        for event in self.event_repository.findPendingReminders(now):
            if event.start - timedelta(minutes=event.reminder_minutes) > now:
                continue
            if self.event_repository.markReminded(event.id) == 0:
                continue  # another run (scheduled or manual) got there first
            minutes = max(0, int((event.start - now).total_seconds() // 60))
            message = self.texts.reminder(event, minutes)
            LOG.info(message)
            self.socket.send({"type": "reminder", "id": event.id, "message": message})
            sent += 1
        return sent
