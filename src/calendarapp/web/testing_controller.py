import random
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Annotated

from jakarta.validation import Valid
from jakarta.validation.constraints import NotBlank, Size
from micronaut.context.annotation import Requires
from micronaut.http import HttpResponse
from micronaut.http.annotation import Body, Controller, Delete, Post
from micronaut.scheduling import TaskExecutors
from micronaut.scheduling.annotation import ExecuteOn
from micronaut.serde.annotation import Serdeable

from ..domain.category import Category
from ..domain.event import Event
from ..jobs.reminder_job import ReminderJob
from ..repository.category_repository import CategoryRepository
from ..service.event_service import EventService
from ..service.text_service import TextService
from .live_updates_socket import LiveUpdatesSocket

SAMPLES = [
    # (day offset from Monday, start hour, duration minutes, title, category, location, reminder)
    (0, 9, 30, "Team standup", "Work", "Room 1", 10),
    (0, 12, 60, "Lunch with Alex", "Personal", "Café Louvre", None),
    (1, 14, 90, "Sprint planning", "Work", "Room 3", 15),
    (2, 7, 45, "Morning run", "Health", "Letná park", None),
    (2, 18, 120, "Parents' evening", "Family", "School", 60),
    (3, 10, 60, "Architecture review", "Work", "Zoom", 5),
    (4, 16, 30, "Dentist", "Health", "Clinic", 1440),
    (5, 10, 240, "Hiking trip", "Family", "Český ráj", None),
]

RANDOM_TITLES = [
    "Coffee chat", "Code review", "Yoga", "Book club", "1:1 with manager", "Grocery run", "Piano lesson",
    "Release retro", "Birthday party", "Car service", "Pair programming", "Team lunch", "Swimming",
]
RANDOM_LOCATIONS = ["Room 1", "Room 2", "Zoom", "Home", "City centre", "Gym", None]
RANDOM_REMINDERS = [None, None, 0, 5, 15, 30, 60]


@Serdeable
@dataclass
class Broadcast:
    message: Annotated[str, NotBlank, Size(max=200)]
    reminder: bool = False


@Controller("/api/testing")
@ExecuteOn(TaskExecutors.BLOCKING)
@Requires(property="calendar.testing.enabled", value="true")
class TestingController:
    """Development helpers behind the UI's Testing menu (enabled with calendar.testing.enabled)."""

    def __init__(
        self,
        events: EventService,
        categories: CategoryRepository,
        reminder_job: ReminderJob,
        socket: LiveUpdatesSocket,
        texts: TextService,
    ):
        self.events = events
        self.categories = categories
        self.reminder_job = reminder_job
        self.socket = socket
        self.texts = texts

    @Post("/sample-events")
    def sample_events(self) -> dict:
        """Creates a week of sample events, starting with the Monday of the current week."""
        by_name = {c.name: c for c in self.categories.listOrderByName()}
        today = datetime.now().date()
        monday = datetime.combine(today - timedelta(days=today.weekday()), time.min)
        created = 0
        for day, hour, minutes, title, category, location, reminder in SAMPLES:
            start = monday + timedelta(days=day, hours=hour)
            self.events.create(Event(
                title=title,
                start=start,
                end=start + timedelta(minutes=minutes),
                location=location,
                category=by_name.get(category) or None,
                reminder_minutes=reminder,
            ))
            created += 1
        return {"created": created}

    @Post("/random-event")
    def random_event(self) -> HttpResponse[Event]:
        """Creates one random event on a random day of the current month."""
        today = datetime.now().date()
        first = today.replace(day=1)
        next_month = (first + timedelta(days=32)).replace(day=1)
        day = first + timedelta(days=random.randrange((next_month - first).days))
        start = datetime.combine(day, time(hour=random.randint(7, 19), minute=random.choice([0, 15, 30, 45])))
        categories = list(self.categories.listOrderByName())
        event = self.events.create(Event(
            title=random.choice(RANDOM_TITLES),
            start=start,
            end=start + timedelta(minutes=random.choice([15, 30, 45, 60, 90, 120])),
            location=random.choice(RANDOM_LOCATIONS),
            category=random.choice(categories) if categories and random.random() < 0.8 else None,
            reminder_minutes=random.choice(RANDOM_REMINDERS),
        ))
        return HttpResponse.created(event)

    @Post("/reminder")
    def reminder(self) -> dict:
        """Pushes a reminder for the next upcoming event right away, without changing any data.

        With no upcoming event, the reminder is for a sample event that is not saved.
        """
        now = datetime.now().replace(second=0, microsecond=0)
        event = self.events.next_event(now)
        if event is None:
            event = Event(title="Sample event", start=now + timedelta(minutes=5), location="Testing menu")
        minutes = max(0, int((event.start - datetime.now()).total_seconds() // 60))
        message = self.texts.reminder(event, minutes)
        self.socket.send({"type": "reminder", "id": event.id, "message": message})
        return {"id": event.id, "message": message}

    @Post("/run-reminders")
    def run_reminders(self) -> dict:
        """Runs the @Scheduled reminder job immediately."""
        return {"sent": self.reminder_job.send_due_reminders()}

    @Post("/reset-reminders")
    def reset_reminders(self) -> dict:
        """Marks every event as not reminded yet, so reminders fire again."""
        return {"reset": self.events.reset_reminders()}

    @Post("/broadcast")
    def broadcast(self, body: Annotated[Broadcast, Body, Valid]) -> dict:
        """Pushes a message to every connected browser over the WebSocket."""
        self.socket.send({"type": "reminder" if body.reminder else "notice", "id": None, "message": body.message})
        return {"sent": True}

    @Delete("/events")
    def delete_all(self) -> dict:
        """Deletes every event."""
        return {"deleted": self.events.delete_all()}
