import logging

from jakarta.inject import Singleton
from jakarta.transaction import Transactional
from micronaut.cache.annotation import CacheConfig, CacheInvalidate, Cacheable
from micronaut.context.event import ApplicationEventPublisher

from ..domain.category import Category
from ..domain.event_change import EventChange
from ..repository.category_repository import CategoryRepository
from ..repository.event_repository import EventRepository
from ..domain.errors import InvalidRequestException, NotFoundException

LOG = logging.getLogger(__name__)


@Singleton
@CacheConfig("categories")
class CategoryService:
    def __init__(
        self,
        category_repository: CategoryRepository,
        event_repository: EventRepository,
        publisher: ApplicationEventPublisher,
    ):
        self.category_repository = category_repository
        self.event_repository = event_repository
        self.publisher = publisher

    @Cacheable
    def all(self) -> list[Category]:
        LOG.info("Loading categories from the database (cache miss)")
        return list(self.category_repository.listOrderByName())

    @Transactional
    @CacheInvalidate(all=True)
    def create(self, category: Category) -> Category:
        if self.category_repository.existsByName(category.name):
            raise InvalidRequestException(f"Category '{category.name}' already exists")
        category.id = None
        saved = self.category_repository.save(category)
        self.publisher.publishEvent(EventChange("category-created", saved.id, saved.name))
        return saved

    @Transactional
    @CacheInvalidate(all=True)
    def delete(self, id: int) -> None:
        category = self.category_repository.findById(id).orElse(None)
        if category is None:
            raise NotFoundException(f"Category {id} not found")
        self.event_repository.clearCategory(id)
        self.category_repository.deleteById(id)
        self.publisher.publishEvent(EventChange("category-deleted", id, category.name))
