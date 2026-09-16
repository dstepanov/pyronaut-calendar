from dataclasses import dataclass

from micronaut.serde.annotation import Serdeable


@Serdeable
@dataclass
class EventChange:
    """Application event published whenever calendar data changes; also the WebSocket payload."""

    type: str
    id: int | None = None
    title: str | None = None
