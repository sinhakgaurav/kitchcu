-- Event-driven infrastructure (outbox pattern foundation)
CREATE TABLE IF NOT EXISTS ckac_events.outbox (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL UNIQUE,
    event_type VARCHAR(100) NOT NULL,
    aggregate_type VARCHAR(50) NOT NULL,
    aggregate_id VARCHAR(100) NOT NULL,
    producer VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    published BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_outbox_unpublished
    ON ckac_events.outbox (created_at)
    WHERE published = false;

CREATE TABLE IF NOT EXISTS ckac_events.processed_events (
    event_id UUID NOT NULL,
    consumer VARCHAR(50) NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (event_id, consumer)
);
