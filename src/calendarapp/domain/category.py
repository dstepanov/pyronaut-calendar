from dataclasses import dataclass
from typing import Annotated

from jakarta.validation.constraints import NotBlank, Pattern, Size
from micronaut.data.annotation import GeneratedValue, Id, MappedEntity
from micronaut.serde.annotation import Serdeable


@dataclass
@Serdeable
@MappedEntity("category")
class Category:
    id: Annotated[int | None, Id, GeneratedValue] = None
    name: Annotated[str | None, NotBlank, Size(max=60)] = None
    color: Annotated[str | None, Pattern(regexp="^#[0-9a-fA-F]{6}$")] = None
