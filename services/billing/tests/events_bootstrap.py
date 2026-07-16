"""Ensure ckac_events schema exists for pytest."""

from pathlib import Path

import psycopg2

_ROOT = Path(__file__).resolve().parents[3]
_EVENTS_SQL = _ROOT / "infra" / "postgres" / "init" / "02-events.sql"
_EVENTS_FIX_SQL = _ROOT / "infra" / "postgres" / "init" / "03-events-fix.sql"
_EVENTS_DLQ_SQL = _ROOT / "infra" / "postgres" / "init" / "04-outbox-dlq.sql"
_bootstrapped_urls: set[str] = set()


def ensure_events_schema(sync_db_url: str) -> None:
    if sync_db_url in _bootstrapped_urls:
        return
    conn = psycopg2.connect(sync_db_url)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
            cur.execute("CREATE SCHEMA IF NOT EXISTS ckac_events")
            if _EVENTS_SQL.is_file():
                cur.execute(_EVENTS_SQL.read_text(encoding="utf-8"))
            if _EVENTS_FIX_SQL.is_file():
                cur.execute(_EVENTS_FIX_SQL.read_text(encoding="utf-8"))
            if _EVENTS_DLQ_SQL.is_file():
                cur.execute(_EVENTS_DLQ_SQL.read_text(encoding="utf-8"))
    finally:
        conn.close()
    _bootstrapped_urls.add(sync_db_url)
