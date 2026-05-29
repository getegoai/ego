"""SQLite connection and migration helpers."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
from typing import Iterator


DATABASE_FILENAME = "ego_data_core.sqlite"
MIGRATIONS_DIR = Path(__file__).with_name("migrations")


@dataclass(frozen=True)
class MigrationResult:
    database_path: Path
    applied: tuple[str, ...]
    skipped: tuple[str, ...]


def get_data_home() -> Path:
    """Return the current local Ego data home.

    EDC-003 will formalize profiles and user-home defaults. Until then, the
    fallback stays repo-local to avoid surprising writes outside the workspace.
    """

    configured_home = os.getenv("EGO_DATA_HOME")
    if configured_home:
        return Path(configured_home).expanduser().resolve()
    return (Path.cwd() / ".ego_data_core").resolve()


def get_default_database_path() -> Path:
    return get_data_home() / "db" / DATABASE_FILENAME


def resolve_database_path(database_path: str | os.PathLike[str] | None = None) -> Path:
    if database_path is None:
        return get_default_database_path()
    return Path(database_path).expanduser().resolve()


def get_connection(
    database_path: str | os.PathLike[str] | None = None,
) -> sqlite3.Connection:
    path = resolve_database_path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def transaction(connection: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    try:
        yield connection
    except Exception:
        connection.rollback()
        raise
    else:
        connection.commit()


def run_migrations(
    database_path: str | os.PathLike[str] | None = None,
    migrations_dir: str | os.PathLike[str] | None = None,
) -> MigrationResult:
    path = resolve_database_path(database_path)
    migration_path = Path(migrations_dir).resolve() if migrations_dir else MIGRATIONS_DIR
    migration_files = sorted(migration_path.glob("*.sql"))

    with get_connection(path) as connection:
        _ensure_migration_table(connection)
        applied_versions = _get_applied_versions(connection)
        applied: list[str] = []
        skipped: list[str] = []

        for migration_file in migration_files:
            version = migration_file.stem
            if version in applied_versions:
                skipped.append(version)
                continue
            sql = migration_file.read_text(encoding="utf-8")
            connection.executescript(sql)
            connection.execute(
                """
                INSERT INTO schema_migrations(version, name, applied_at)
                VALUES (?, ?, ?)
                """,
                (version, migration_file.name, _utc_now()),
            )
            connection.commit()
            applied.append(version)
            applied_versions.add(version)

    return MigrationResult(path, tuple(applied), tuple(skipped))


def get_database_status(
    database_path: str | os.PathLike[str] | None = None,
) -> dict[str, object]:
    try:
        run_migrations(database_path)
        with get_connection(database_path) as connection:
            foreign_keys = bool(connection.execute("PRAGMA foreign_keys").fetchone()[0])
            table_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                """
            ).fetchone()[0]
            migration_count = connection.execute(
                "SELECT COUNT(*) FROM schema_migrations"
            ).fetchone()[0]
        return {
            "status": "ok",
            "foreign_keys": foreign_keys,
            "table_count": table_count,
            "migration_count": migration_count,
        }
    except Exception as exc:
        return {
            "status": "error",
            "detail": str(exc),
        }


def _ensure_migration_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          version TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          applied_at TEXT NOT NULL
        )
        """
    )
    connection.commit()


def _get_applied_versions(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute("SELECT version FROM schema_migrations").fetchall()
    return {row["version"] for row in rows}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

