from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

from ckac_common.database import Base
from app.models import KitchenStreamSettings, LiveSession  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    import os

    if url := os.environ.get("DATABASE_SYNC_URL"):
        return url
    if url := os.environ.get("DATABASE_URL"):
        return (
            url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
            .replace("postgresql+asyncpg", "postgresql+psycopg2")
        )
    url = config.get_main_option("sqlalchemy.url")
    return url.replace("postgresql+asyncpg", "postgresql+psycopg2") if url else ""


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        include_schemas=True,
        version_table_schema="ckac_streaming",
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS ckac_streaming"))
        connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            version_table_schema="ckac_streaming",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
