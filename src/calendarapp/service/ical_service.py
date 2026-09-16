from datetime import datetime, timezone

from jakarta.inject import Singleton

from ..config.calendar_configuration import CalendarConfiguration
from ..domain.event import Event
from .text_service import TextService


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fmt(value: datetime) -> str:
    return value.strftime("%Y%m%dT%H%M%S")


@Singleton
class ICalService:
    """Renders events as an RFC 5545 iCalendar document."""

    def __init__(self, configuration: CalendarConfiguration, texts: TextService):
        self.configuration = configuration
        self.texts = texts

    def render(self, events: list[Event]) -> str:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Pyronaut//Calendar//EN",
            f"X-WR-CALNAME:{_escape(self.configuration.name)}",
        ]
        for event in events:
            lines += [
                "BEGIN:VEVENT",
                f"UID:event-{event.id}@pyronaut-calendar",
                f"DTSTAMP:{stamp}",
                f"DTSTART:{_fmt(event.start)}",
                f"DTEND:{_fmt(event.end)}",
                f"SUMMARY:{_escape(event.title or '')}",
            ]
            if event.location:
                lines.append(f"LOCATION:{_escape(event.location)}")
            description = self.texts.ical_description(event)
            if description:
                lines.append(f"DESCRIPTION:{_escape(description)}")
            if event.category is not None and event.category.name:
                lines.append(f"CATEGORIES:{_escape(event.category.name)}")
            if event.reminder_minutes is not None:
                lines += [
                    "BEGIN:VALARM",
                    "ACTION:DISPLAY",
                    f"DESCRIPTION:{_escape(event.title or '')}",
                    f"TRIGGER:-PT{event.reminder_minutes}M",
                    "END:VALARM",
                ]
            lines.append("END:VEVENT")
        lines.append("END:VCALENDAR")
        return "\r\n".join(lines) + "\r\n"
