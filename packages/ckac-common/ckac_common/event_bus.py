import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ckac_common.events import EventEnvelope

PENDING_EVENTS_KEY = "ckac_pending_stream_events"
PUBLISHER_SESSION_KEY = "ckac_event_publisher"


class EventPublisher:
    """Redis Streams publisher with transactional outbox (EDD).

    When ``session`` is provided, events are written to the outbox inside the
    transaction and Redis publish happens only after commit via ``flush_pending``.
    """

    def __init__(self, redis_client) -> None:
        self._redis = redis_client

    async def publish(
        self,
        stream: str,
        event: EventEnvelope,
        session: AsyncSession | None = None,
    ) -> str | None:
        if session:
            await self._write_outbox(session, event)
            session.info.setdefault(PENDING_EVENTS_KEY, []).append((stream, event))
            session.info[PUBLISHER_SESSION_KEY] = self
            return None

        return await self._publish_to_redis(stream, event)

    async def flush_pending(self, session: AsyncSession) -> None:
        """Publish queued events to Redis after the domain transaction committed."""
        pending: list = session.info.pop(PENDING_EVENTS_KEY, [])
        session.info.pop(PUBLISHER_SESSION_KEY, None)
        if not pending:
            return
        if not self._redis:
            return

        from ckac_common.auth import event_to_stream_fields

        for stream, event in pending:
            try:
                await self._redis.xadd(stream, event_to_stream_fields(event))
                await self._mark_outbox_published(session, event.event_id)
            except Exception as exc:
                await self._write_dlq(session, stream, event, str(exc))
        await session.commit()

    async def _publish_to_redis(self, stream: str, event: EventEnvelope) -> str | None:
        if not self._redis:
            return None
        from ckac_common.auth import event_to_stream_fields

        return await self._redis.xadd(stream, event_to_stream_fields(event))

    @staticmethod
    async def _write_outbox(session: AsyncSession, event: EventEnvelope) -> None:
        await session.execute(
            text(
                """
                INSERT INTO ckac_events.outbox
                (event_id, event_type, aggregate_type, aggregate_id, producer, payload, published)
                VALUES (
                    CAST(:event_id AS uuid), :event_type, :aggregate_type, :aggregate_id, :producer,
                    CAST(:payload AS jsonb), false
                )
                """
            ),
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "aggregate_type": event.aggregate_type,
                "aggregate_id": event.aggregate_id,
                "producer": event.producer,
                "payload": json.dumps(event.payload),
            },
        )

    @staticmethod
    async def _mark_outbox_published(session: AsyncSession, event_id: str) -> None:
        await session.execute(
            text(
                "UPDATE ckac_events.outbox SET published = true "
                "WHERE event_id = CAST(:event_id AS uuid)"
            ),
            {"event_id": event_id},
        )

    @staticmethod
    async def _write_dlq(
        session: AsyncSession,
        stream: str,
        event: EventEnvelope,
        error_message: str,
    ) -> None:
        await session.execute(
            text(
                """
                INSERT INTO ckac_events.outbox_dlq
                (event_id, event_type, stream_key, error_message, payload)
                VALUES (
                    CAST(:event_id AS uuid), :event_type, :stream_key, :error_message,
                    CAST(:payload AS jsonb)
                )
                """
            ),
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "stream_key": stream,
                "error_message": error_message[:2000],
                "payload": json.dumps(event.payload),
            },
        )

    @staticmethod
    def build(
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        producer: str,
        payload: dict,
        correlation_id: str | None = None,
    ) -> EventEnvelope:
        if correlation_id is None:
            from ckac_common.observability import get_correlation_id

            correlation_id = get_correlation_id()
        return EventEnvelope(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            producer=producer,
            correlation_id=correlation_id,
            payload=payload,
        )
