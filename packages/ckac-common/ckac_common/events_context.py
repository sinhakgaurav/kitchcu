"""Request-scoped EventPublisher for post-commit Redis flush."""

from contextvars import ContextVar

from ckac_common.event_bus import EventPublisher

_publisher_var: ContextVar[EventPublisher | None] = ContextVar("ckac_event_publisher", default=None)


def set_event_publisher(publisher: EventPublisher | None) -> None:
    _publisher_var.set(publisher)


def get_event_publisher() -> EventPublisher | None:
    return _publisher_var.get()
