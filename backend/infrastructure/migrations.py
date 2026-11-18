"""Apply the idempotent SQL files in backend/migrations in filename order."""

from pathlib import Path

from backend.infrastructure.database import connect

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"
ADVISORY_LOCK_KEY = 782630194


def initialize(db_url: str | None = None) -> None:
    """Apply each SQL migration once, preserving the existing database schema."""
    migrations = sorted(MIGRATIONS_DIR.glob("*.sql"))
    with connect(db_url) as conn:
        conn.execute(f"SELECT pg_advisory_xact_lock({ADVISORY_LOCK_KEY})")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS schema_migrations (
                   filename TEXT PRIMARY KEY,
                   applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
               )"""
        )

        # Databases created before migration tracking already have migration 001.
        if migrations:
            first = migrations[0].name
            conn.execute(
                """INSERT INTO schema_migrations (filename)
                   SELECT %s
                   WHERE to_regclass('public.posture_events') IS NOT NULL
                   ON CONFLICT (filename) DO NOTHING""",
                (first,),
            )

        for migration in migrations:
            exists = conn.execute(
                "SELECT 1 FROM schema_migrations WHERE filename = %s",
                (migration.name,),
            ).fetchone()
            if exists:
                continue
            sql = migration.read_text(encoding="utf-8")
            if sql.strip():
                conn.execute(sql, prepare=False)
            conn.execute(
                "INSERT INTO schema_migrations (filename) VALUES (%s)",
                (migration.name,),
            )
