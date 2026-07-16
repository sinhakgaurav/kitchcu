-- Dead-letter queue for failed outbox → Redis publish attempts

CREATE TABLE IF NOT EXISTS ckac_events.outbox_dlq (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    stream_key VARCHAR(200) NOT NULL,
    error_message TEXT NOT NULL,
    retry_count INTEGER NOT NULL DEFAULT 0,
    payload JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_outbox_dlq_created
    ON ckac_events.outbox_dlq (created_at DESC);
