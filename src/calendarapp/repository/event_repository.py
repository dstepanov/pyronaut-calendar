from datetime import datetime

from java.util import Optional
from micronaut.data.annotation import Join, Query
from micronaut.data.jdbc.annotation import JdbcRepository
from micronaut.data.model import Page, Pageable
from micronaut.data.model.query.builder.sql import Dialect
from micronaut.data.repository import CrudRepository

from ..domain.event import Event


@JdbcRepository(dialect=Dialect.H2)
class EventRepository(CrudRepository[Event, int]):
    @Join(value="category", type=Join.Type.LEFT_FETCH)
    def getById(self, id: int) -> Optional[Event]: ...

    @Join(value="category", type=Join.Type.LEFT_FETCH)
    def findByStartLessThanAndEndGreaterThanOrderByStart(self, to: datetime, from_: datetime) -> list[Event]: ...

    @Join(value="category", type=Join.Type.LEFT_FETCH)
    def findByCategoryIdAndStartLessThanAndEndGreaterThanOrderByStart(
        self, category_id: int, to: datetime, from_: datetime
    ) -> list[Event]: ...

    @Join(value="category", type=Join.Type.LEFT_FETCH)
    def listOrderByStart(self) -> list[Event]: ...

    @Join(value="category", type=Join.Type.LEFT_FETCH)
    def findByTitleIlikeOrDescriptionIlike(self, title: str, description: str, pageable: Pageable) -> Page[Event]: ...

    @Query(
        "SELECT * FROM calendar_event WHERE reminded = FALSE AND reminder_minutes IS NOT NULL "
        "AND start_time >= :now ORDER BY start_time"
    )
    def findPendingReminders(self, now: datetime) -> list[Event]: ...

    @Join(value="category", type=Join.Type.LEFT_FETCH)
    def findFirstByStartGreaterThanEqualsOrderByStart(self, now: datetime) -> Optional[Event]: ...

    def countByCategoryId(self, category_id: int) -> int: ...

    @Query("UPDATE calendar_event SET reminded = TRUE WHERE id = :id AND reminded = FALSE")
    def markReminded(self, id: int) -> int: ...

    @Query("UPDATE calendar_event SET reminded = FALSE")
    def resetReminders(self) -> int: ...

    @Query("UPDATE calendar_event SET category_id = NULL WHERE category_id = :categoryId")
    def clearCategory(self, categoryId: int) -> None: ...
