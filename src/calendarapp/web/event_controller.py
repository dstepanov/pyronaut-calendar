from datetime import date, datetime, time, timedelta
from typing import Annotated

from jakarta.validation import Valid
from micronaut.data.model import Page, Pageable
from micronaut.http import HttpHeaders, HttpResponse, HttpStatus, MediaType
from micronaut.http.annotation import Body, Controller, Delete, Get, Post, Produces, Put, QueryValue, Status
from micronaut.scheduling import TaskExecutors
from micronaut.scheduling.annotation import ExecuteOn

from ..domain.event import Event
from ..service.event_service import EventService
from ..service.ical_service import ICalService
from ..service.text_service import TextService


@Controller("/api/events")
@ExecuteOn(TaskExecutors.BLOCKING)
class EventController:
    def __init__(self, events: EventService, ical: ICalService, texts: TextService):
        self.events = events
        self.ical = ical
        self.texts = texts

    @Get
    def list_events(
        self,
        from_: Annotated[datetime | None, QueryValue("from")] = None,
        to: Annotated[datetime | None, QueryValue("to")] = None,
        category: Annotated[int | None, QueryValue] = None,
    ) -> list[Event]:
        """Events overlapping [from, to), optionally restricted to one category."""
        return self.events.find(from_, to, category)

    @Get("/search")
    def search(self, q: Annotated[str, QueryValue], pageable: Annotated[Pageable, Valid]) -> Page[Event]:
        """Case-insensitive search over title and description, paginated with ?page=&size=&sort=."""
        return self.events.search(q, pageable)

    @Get(value="/export.ics", produces="text/calendar")
    def export(self) -> HttpResponse[str]:
        """All events as an iCalendar file."""
        body = self.ical.render(self.events.find(None, None, None))
        return HttpResponse.ok(body).header(HttpHeaders.CONTENT_DISPOSITION, 'attachment; filename="calendar.ics"')

    @Get("/agenda")
    @Produces(MediaType.TEXT_PLAIN)
    def agenda(self, day: Annotated[date | None, QueryValue] = None) -> str:
        """A plain-text agenda for one day, rendered with Jakarta EL templates."""
        day = day or date.today()
        start = datetime.combine(day, time.min)
        return self.texts.agenda(start, self.events.find(start, start + timedelta(days=1), None))

    @Get("/{id}")
    def get(self, id: int) -> Event:
        return self.events.get(id)

    @Post
    def create(self, event: Annotated[Event, Body, Valid]) -> HttpResponse[Event]:
        saved = self.events.create(event)
        return HttpResponse.created(saved).header(HttpHeaders.LOCATION, f"/api/events/{saved.id}")

    @Put("/{id}")
    def update(self, id: int, event: Annotated[Event, Body, Valid]) -> Event:
        return self.events.update(id, event)

    @Delete("/{id}")
    @Status(HttpStatus.NO_CONTENT)
    def delete(self, id: int) -> None:
        self.events.delete(id)
