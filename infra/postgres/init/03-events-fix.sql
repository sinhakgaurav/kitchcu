-- Idempotent fixes for existing CKAC databases (safe to re-run)

ALTER TABLE IF EXISTS ckac_events.outbox
    ALTER COLUMN id SET DEFAULT uuid_generate_v4();

ALTER TABLE IF EXISTS ckac_events.processed_events
    DROP CONSTRAINT IF EXISTS processed_events_pkey;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'ckac_events' AND table_name = 'processed_events'
    ) AND NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'processed_events_pkey'
          AND conrelid = 'ckac_events.processed_events'::regclass
    ) THEN
        ALTER TABLE ckac_events.processed_events
            ADD PRIMARY KEY (event_id, consumer);
    END IF;
END $$;
