from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from ckac_common.config import get_settings
from ckac_common.event_bus import PENDING_EVENTS_KEY, PUBLISHER_SESSION_KEY
from ckac_common.events_context import get_event_publisher


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_async_engine(
    settings.database_url,
    echo=settings.app_env == "development",
    pool_pre_ping=True,
)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
            publisher = session.info.get(PUBLISHER_SESSION_KEY) or get_event_publisher()
            if publisher:
                await publisher.flush_pending(session)
        except Exception:
            await session.rollback()
            session.info.pop(PENDING_EVENTS_KEY, None)
            session.info.pop(PUBLISHER_SESSION_KEY, None)
            raise


async def check_db_connection() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        return True
    except Exception:
        return False
