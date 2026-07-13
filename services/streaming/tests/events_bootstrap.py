"""Ensure ckac_events schema exists for outbox assertions."""

import psycopg2


def ensure_events_schema(sync_url: str) -> None:
    conn = psycopg2.connect(sync_url)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS ckac_events")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ckac_events.outbox (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                event_id UUID NOT NULL,
                stream_key VARCHAR(255) NOT NULL,
                payload JSONB NOT NULL,
                published BOOLEAN DEFAULT false,
                created_at TIMESTAMPTZ DEFAULT now()
            )
            """
        )
    conn.close()
