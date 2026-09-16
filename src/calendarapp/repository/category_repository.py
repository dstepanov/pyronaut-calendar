from micronaut.data.jdbc.annotation import JdbcRepository
from micronaut.data.model.query.builder.sql import Dialect
from micronaut.data.repository import CrudRepository

from ..domain.category import Category


@JdbcRepository(dialect=Dialect.H2)
class CategoryRepository(CrudRepository[Category, int]):
    def listOrderByName(self) -> list[Category]: ...

    def existsByName(self, name: str) -> bool: ...
