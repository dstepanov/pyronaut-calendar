from micronaut.http.annotation import Controller, Get

from ..config.calendar_configuration import CalendarConfiguration, TestingConfiguration


@Controller("/api/settings")
class SettingsController:
    """Exposes the @ConfigurationProperties values the UI needs."""

    def __init__(self, configuration: CalendarConfiguration, testing: TestingConfiguration):
        self.configuration = configuration
        self.testing = testing

    @Get
    def settings(self) -> dict:
        return {
            "name": self.configuration.name,
            "defaultDurationMinutes": self.configuration.default_duration_minutes,
            "defaultReminderMinutes": self.configuration.default_reminder_minutes,
            "testingEnabled": self.testing.enabled,
        }
