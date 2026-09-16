from datetime import datetime

from jakarta.inject import Singleton
from jakarta.transaction import Transactional
from micronaut.context.event import ApplicationEventPublisher
from micronaut.data.model import Page, Pageable

from ..config.calendar_configuration import CalendarConfiguration
from ..domain.event import Event
from ..domain.event_change import EventChange
from ..repository.category_repository import CategoryRepository
from ..repository.event_repository import EventRepository
from ..domain.errors import InvalidRequestException, NotFoundException


@Singleton
class EventService:
    def __init__(
        self,
        event_repository: EventRepository,
        category_repository: CategoryRepository,
        configuration: CalendarConfiguration,
        publisher: ApplicationEventPublisher,
    ):
        self.event_repository = event_repository
        self.category_repository = category_repository
        self.configuration = configuration
        self.publisher = publisher

    def find(self, from_: datetime | None, to: datetime | None, category_id: int | None) -> list[Event]:
        if from_ is None or to is None:
            return self.event_repository.listOrderByStart()
        if category_id is not None:
            return self.event_repository.findByCategoryIdAndStartLessThanAndEndGreaterThanOrderByStart(
                category_id, to, from_
            )
        return self.event_repository.findByStartLessThanAndEndGreaterThanOrderByStart(to, from_)

    def search(self, query: str, pageable: Pageable) -> Page[Event]:
        pattern = f"%{query}%"
        return self.event_repository.findByTitleIlikeOrDescriptionIlike(pattern, pattern, pageable)

    def next_event(self, now: datetime) -> Event | None:
        return self.event_repository.findFirstByStartGreaterThanEqualsOrderByStart(now).orElse(None)

    def get(self, id: int) -> Event:
        event = self.event_repository.getById(id).orElse(None)
        if event is None:
            raise NotFoundException(f"Event {id} not found")
        return event

    @Transactional
    def create(self, event: Event) -> Event:
        event.id = None
        event.version = None
        event.reminded = False
        self._prepare(event)
        saved = self.event_repository.save(event)
        self.publisher.publishEvent(EventChange("created", saved.id, saved.title))
        return self.get(saved.id)

    @Transactional
    def update(self, id: int, changes: Event) -> Event:
        event = self.get(id)
        if event.start != changes.start or event.reminder_minutes != changes.reminder_minutes:
            event.reminded = False
        for name in ("title", "start", "end", "description", "location", "color", "category", "reminder_minutes"):
            setattr(event, name, getattr(changes, name))
        self._prepare(event)
        self.event_repository.update(event)
        self.publisher.publishEvent(EventChange("updated", id, event.title))
        return self.get(id)

    @Transactional
    def delete(self, id: int) -> None:
        event = self.get(id)
        self.event_repository.deleteById(id)
        self.publisher.publishEvent(EventChange("deleted", id, event.title))

    def _prepare(self, event: Event) -> None:
        if event.end < event.start:
            raise InvalidRequestException("Event end must not be before its start")
        if event.category is not None:
            if event.category.id is None:
                event.category = None
            else:
                category = self.category_repository.findById(event.category.id).orElse(None)
                if category is None:
                    raise InvalidRequestException(f"Category {event.category.id} does not exist")
                event.category = category

    @Transactional
    def delete_all(self) -> int:
        count = self.event_repository.count()
        self.event_repository.deleteAll()
        self.publisher.publishEvent(EventChange("cleared", None, f"{count} events"))
        return count

    @Transactional
    def reset_reminders(self) -> int:
        return self.event_repository.resetReminders()
