CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE columns (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug        TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    position    DOUBLE PRECISION NOT NULL,
    color       TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE labels (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug        TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    tone        TEXT NOT NULL,
    emoji       TEXT NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE cards (
    id          TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    column_id   UUID NOT NULL REFERENCES columns(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    description TEXT,
    position    DOUBLE PRECISION NOT NULL,
    pinned      BOOLEAN NOT NULL DEFAULT FALSE,
    flame       BOOLEAN NOT NULL DEFAULT FALSE,
    due_at      TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE card_labels (
    card_id     TEXT NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    label_id    UUID NOT NULL REFERENCES labels(id) ON DELETE CASCADE,
    PRIMARY KEY (card_id, label_id)
);

CREATE INDEX idx_cards_column ON cards (column_id, position);
CREATE INDEX idx_cards_due_at ON cards (due_at) WHERE due_at IS NOT NULL;

CREATE TABLE agent_history (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    command     TEXT NOT NULL,
    actions     JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION notify_board_change() RETURNS trigger AS $$
BEGIN
    PERFORM pg_notify('board.changed', json_build_object(
        'op', TG_OP,
        'table', TG_TABLE_NAME,
        'id', COALESCE(
            to_jsonb(NEW)->>'id',
            to_jsonb(OLD)->>'id',
            to_jsonb(NEW)->>'card_id',
            to_jsonb(OLD)->>'card_id'
        )
    )::text);
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER cards_notify
    AFTER INSERT OR UPDATE OR DELETE ON cards
    FOR EACH ROW EXECUTE FUNCTION notify_board_change();

CREATE TRIGGER columns_notify
    AFTER INSERT OR UPDATE OR DELETE ON columns
    FOR EACH ROW EXECUTE FUNCTION notify_board_change();

CREATE TRIGGER labels_notify
    AFTER INSERT OR UPDATE OR DELETE ON labels
    FOR EACH ROW EXECUTE FUNCTION notify_board_change();

CREATE TRIGGER card_labels_notify
    AFTER INSERT OR UPDATE OR DELETE ON card_labels
    FOR EACH ROW EXECUTE FUNCTION notify_board_change();
