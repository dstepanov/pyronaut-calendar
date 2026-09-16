from dataclasses import dataclass
from datetime import datetime
from typing import Annotated

from jakarta.validation.constraints import Max, Min, NotBlank, NotNull, Size
from micronaut.data.annotation import (
    DateCreated,
    DateUpdated,
    GeneratedValue,
    Id,
    MappedEntity,
    MappedProperty,
    Relation,
    Version,
)
from micronaut.serde.annotation import Serdeable

from .category import Category


@dataclass
@Serdeable
@MappedEntity("calendar_event")
class Event:
    id: Annotated[int | None, Id, GeneratedValue] = None
    version: Annotated[int | None, Version] = None
    title: Annotated[str | None, NotBlank, Size(max=200)] = None
    start: Annotated[datetime | None, NotNull, MappedProperty("start_time")] = None
    end: Annotated[datetime | None, NotNull, MappedProperty("end_time")] = None
    description: Annotated[str | None, Size(max=2000)] = None
    location: Annotated[str | None, Size(max=200)] = None
    color: Annotated[str | None, Size(max=20)] = None
    category: Annotated[Category | None, Relation(value=Relation.Kind.MANY_TO_ONE)] = None
    reminder_minutes: Annotated[int | None, Min(0), Max(10080)] = None
    reminded: bool = False
    created_at: Annotated[datetime | None, DateCreated] = None
    updated_at: Annotated[datetime | None, DateUpdated] = None
