"""Text generation with Micronaut Jakarta EL.

Two flavours are used:

* the notification texts below are fixed expressions owned by the code;
* the agenda / iCalendar templates are read from ``application.toml`` (``[calendar.templates]``), so the
  wording can change without touching the code.

Both are parsed by ``micronaut-jakarta-el-interpreter`` the first time they are used. Expressions see plain
``java.util.Map`` variables.

Compiling them at build time with ``@ELExpression`` / ``micronaut-jakarta-el-processor`` is not possible yet:
the Pyronaut 0.0.3 processor tool puts its own micronaut-sourcegen 2.1.0 first on the processor classpath,
and the EL processor fails to load ``ByteCodeGenerator`` against it.
"""
from datetime import datetime

from jakarta.el import ELManager
from jakarta.inject import Singleton
from java.lang import String as JString
from java.util import HashMap, Map
from micronaut.context import BeanContext
from micronaut.el import CompiledELContext

from ..config.calendar_configuration import CalendarConfiguration, TemplatesConfiguration
from ..domain.event import Event

REMINDER = (
    "⏰ ${event.title} starts ${minutes == 0 ? 'now' : 'in ' += minutes += (minutes == 1 ? ' minute' : ' minutes')}"
    "${empty event.location ? '' : ' at ' += event.location}"
)
CHANGE = (
    "${change.type == 'cleared' ? 'Calendar cleared: ' += change.title : ("
    "(change.type == 'created' ? 'Added' : change.type == 'updated' ? 'Updated' : change.type == 'deleted' ? 'Removed'"
    " : change.type == 'category-created' ? 'New category' : change.type == 'category-deleted' ? 'Deleted category'"
    " : 'Changed') += ' ' += (empty change.title ? 'event' : '“' += change.title += '”'))}"
)


def _time(value: datetime | None) -> str:
    return value.strftime("%H:%M") if value is not None else ""


def event_variables(event: Event) -> Map:
    values = HashMap()
    values.put("id", event.id)
    values.put("title", event.title or "")
    values.put("location", event.location or "")
    values.put("description", event.description or "")
    values.put("category", event.category.name if event.category is not None and event.category.name else "")
    values.put("start", _time(event.start))
    values.put("end", _time(event.end))
    values.put("date", event.start.strftime("%a %d %b %Y") if event.start is not None else "")
    values.put("multiDay", event.start is not None and event.end is not None and event.start.date() != event.end.date())
    values.put("reminderMinutes", event.reminder_minutes)
    return values


@Singleton
class TextService:
    def __init__(
        self,
        bean_context: BeanContext,
        configuration: CalendarConfiguration,
        templates: TemplatesConfiguration,
    ):
        self.bean_context = bean_context
        self.configuration = configuration
        self.templates = templates
        self.factory = ELManager.getExpressionFactory()

    def reminder(self, event: Event, minutes: int) -> str:
        return self._evaluate(REMINDER, event=event_variables(event), minutes=minutes)

    def change(self, type_: str, title: str | None) -> str:
        change = HashMap()
        change.put("type", type_)
        change.put("title", title or "")
        return self._evaluate(CHANGE, change=change)

    def agenda(self, day: datetime, events: list[Event]) -> str:
        templates = self.templates
        lines = [
            self._evaluate(
                templates.agenda_header,
                calendar=self.configuration.name,
                day=day.strftime("%A, %d %B %Y"),
                count=len(events),
            )
        ]
        lines += [self._evaluate(templates.agenda_line, event=event_variables(e)) for e in events]
        return "\n".join(lines) + "\n"

    def ical_description(self, event: Event) -> str:
        return self._evaluate(self.templates.ical_description, event=event_variables(event))

    def _evaluate(self, expression: str, **variables) -> str:
        context = CompiledELContext(self.bean_context)
        for name, value in variables.items():
            context.setBean(name, value)
        value = self.factory.createValueExpression(context, expression, JString).getValue(context)
        return str(value) if value is not None else ""
