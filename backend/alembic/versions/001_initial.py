"""Initial Postgres schema (columns, cards, labels) with realtime notify.

Revision ID: 001_initial
Revises:
Create Date: 2026-05-28
"""

from alembic import op

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    op.execute(
        """
        CREATE TABLE columns (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            slug        TEXT NOT NULL UNIQUE,
            name        TEXT NOT NULL,
            position    DOUBLE PRECISION NOT NULL,
            color       TEXT NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        """
        CREATE TABLE labels (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            slug        TEXT NOT NULL UNIQUE,
            name        TEXT NOT NULL,
            tone        TEXT NOT NULL,
            emoji       TEXT NOT NULL,
            description TEXT,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        """
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
        """
    )
    op.execute(
        """
        CREATE TABLE card_labels (
            card_id     TEXT NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
            label_id    UUID NOT NULL REFERENCES labels(id) ON DELETE CASCADE,
            PRIMARY KEY (card_id, label_id)
        );
        """
    )
    op.execute("CREATE INDEX idx_cards_column ON cards (column_id, position);")
    op.execute("CREATE INDEX idx_cards_due_at ON cards (due_at) WHERE due_at IS NOT NULL;")

    op.execute(
        """
        CREATE TABLE agent_history (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            command     TEXT NOT NULL,
            actions     JSONB NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION notify_board_change() RETURNS trigger AS $$
        BEGIN
            -- Some tables (e.g. card_labels) don't have an `id` column.
            -- Use JSONB extraction instead of NEW.id / OLD.id record access.
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
        """
    )

    for table in ("cards", "columns", "labels", "card_labels"):
        op.execute(
            f"""
            DROP TRIGGER IF EXISTS {table}_notify ON {table};
            CREATE TRIGGER {table}_notify
                AFTER INSERT OR UPDATE OR DELETE ON {table}
                FOR EACH ROW EXECUTE FUNCTION notify_board_change();
            """
        )

    # Seed defaults (idempotent via UNIQUE slugs).
    op.execute(
        """
        INSERT INTO columns (slug, name, position, color)
        VALUES
          ('backlog', 'Backlog', 1000, '#888690'),
          ('ideas', 'Ideas', 2000, '#58a6ff'),
          ('todo', 'To Do', 3000, '#e3b341'),
          ('inprogress', 'In Progress', 4000, '#6750a4'),
          ('production', 'Production', 5000, '#f85149'),
          ('done', 'Done', 6000, '#3fb950')
        ON CONFLICT (slug) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO labels (slug, name, tone, emoji, description)
        VALUES
          ('green', 'Done', 'green', '🟢', NULL),
          ('blue', 'Review', 'blue', '🔵', NULL),
          ('orange', 'Urgent', 'orange', '🟡', NULL),
          ('purple', 'AI', 'purple', '🟣', NULL),
          ('red', 'Bug', 'red', '🔴', NULL)
        ON CONFLICT (slug) DO NOTHING;
        """
    )


def downgrade() -> None:
    for table in ("cards", "columns", "labels", "card_labels"):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_notify ON {table};")
    op.execute("DROP FUNCTION IF EXISTS notify_board_change;")

    op.execute("DROP TABLE IF EXISTS agent_history;")
    op.execute("DROP TABLE IF EXISTS card_labels;")
    op.execute("DROP TABLE IF EXISTS cards;")
    op.execute("DROP TABLE IF EXISTS labels;")
    op.execute("DROP TABLE IF EXISTS columns;")
