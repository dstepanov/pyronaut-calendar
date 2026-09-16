import logging

from jakarta.inject import Singleton
from micronaut.context.event import ApplicationEventListener, StartupEvent

from ..config.calendar_configuration import CalendarConfiguration
from ..domain.category import Category
from ..repository.category_repository import CategoryRepository
from .category_service import CategoryService

LOG = logging.getLogger(__name__)

PALETTE = ["#2f6fed", "#1f9d55", "#d97706", "#d33a3a", "#8b5cf6", "#0e9aa7"]


@Singleton
class CategorySeeder(ApplicationEventListener[StartupEvent]):
    """Creates the categories listed in calendar.default-categories when the context starts with an empty table."""

    def __init__(self, repository: CategoryRepository, service: CategoryService, configuration: CalendarConfiguration):
        self.repository = repository
        self.service = service
        self.configuration = configuration

    def onApplicationEvent(self, event: StartupEvent) -> None:
        if self.repository.count() > 0:
            return
        for index, name in enumerate(self.configuration.default_categories):
            # through the service, so the "categories" cache is invalidated
            self.service.create(Category(None, name, PALETTE[index % len(PALETTE)]))
        LOG.info("Seeded %d categories", len(self.configuration.default_categories))
