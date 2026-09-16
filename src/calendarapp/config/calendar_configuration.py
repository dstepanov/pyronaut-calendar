from dataclasses import dataclass, field

from micronaut.context.annotation import ConfigurationProperties
from micronaut.serde.annotation import Serdeable


@Serdeable
@ConfigurationProperties("calendar")
@dataclass(init=False)
class CalendarConfiguration:
    """Settings bound from the [calendar] section of application.toml."""

    name: str = "Calendar"
    default_duration_minutes: int = 60
    default_reminder_minutes: int | None = 15
    default_categories: list[str] = field(default_factory=list)
    reminder_check_interval: str = "30s"  # read by ReminderJob's @Scheduled placeholder

    def __init__(
        self,
        name: str = "Calendar",
        default_duration_minutes: int = 60,
        default_reminder_minutes: int | None = 15,
        default_categories: list[str] | None = None,
        reminder_check_interval: str = "30s",
    ):
        self.name = name
        self.default_duration_minutes = default_duration_minutes
        self.default_reminder_minutes = default_reminder_minutes
        self.default_categories = list(default_categories or [])
        self.reminder_check_interval = reminder_check_interval


@Serdeable
@ConfigurationProperties("calendar.templates")
@dataclass(init=False)
class TemplatesConfiguration:
    """Jakarta EL templates bound from [calendar.templates]; parsed at runtime.

    Written with the deferred ``#{...}`` syntax: Micronaut would treat ``${...}`` in configuration as a
    property placeholder.
    """

    agenda_header: str = "#{calendar}: #{count} event(s) on #{day}"
    agenda_line: str = "#{event.start}–#{event.end}  #{event.title}"
    ical_description: str = "#{event.description}"

    def __init__(
        self,
        agenda_header: str = "#{calendar}: #{count} event(s) on #{day}",
        agenda_line: str = "#{event.start}–#{event.end}  #{event.title}",
        ical_description: str = "#{event.description}",
    ):
        self.agenda_header = agenda_header
        self.agenda_line = agenda_line
        self.ical_description = ical_description


@Serdeable
@ConfigurationProperties("calendar.testing")
@dataclass(init=False)
class TestingConfiguration:
    """Enables the /api/testing endpoints and the UI's Testing menu. Keep it off in production."""

    enabled: bool = False

    def __init__(self, enabled: bool = False):
        self.enabled = enabled
