import pytest

from ego_data_core.storage.db import get_connection, get_database_status, run_migrations, transaction


KEY_TABLES = {
    "users",
    "devices",
    "sources",
    "raw_objects",
    "object_versions",
    "evidence",
    "evidence_text_chunks",
    "enhancements",
    "jobs",
    "audit_logs",
    "schema_migrations",
}


def test_run_migrations_creates_schema_and_enables_foreign_keys(tmp_path) -> None:
    database_path = tmp_path / "ego.sqlite"

    result = run_migrations(database_path)

    assert result.database_path == database_path
    assert result.applied == ("001_init",)
    assert result.skipped == ()
    assert database_path.exists()

    with get_connection(database_path) as connection:
        foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()[0]
        table_rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        tables = {row["name"] for row in table_rows}

    assert foreign_keys == 1
    assert KEY_TABLES.issubset(tables)


def test_run_migrations_is_idempotent_and_preserves_data(tmp_path) -> None:
    database_path = tmp_path / "ego.sqlite"
    run_migrations(database_path)

    with get_connection(database_path) as connection:
        connection.execute(
            """
            INSERT INTO users(user_id, display_name, created_at, updated_at)
            VALUES ('usr_test', 'Test User', '2026-05-29T00:00:00Z', '2026-05-29T00:00:00Z')
            """
        )
        connection.commit()

    result = run_migrations(database_path)

    assert result.applied == ()
    assert result.skipped == ("001_init",)
    with get_connection(database_path) as connection:
        user_count = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        migration_count = connection.execute(
            "SELECT COUNT(*) FROM schema_migrations"
        ).fetchone()[0]

    assert user_count == 1
    assert migration_count == 1


def test_database_status_runs_migrations(tmp_path) -> None:
    database_path = tmp_path / "ego.sqlite"

    status = get_database_status(database_path)

    assert status["status"] == "ok"
    assert status["foreign_keys"] is True
    assert status["migration_count"] == 1
    assert status["table_count"] >= len(KEY_TABLES)


def test_transaction_commits_and_rolls_back(tmp_path) -> None:
    database_path = tmp_path / "ego.sqlite"
    run_migrations(database_path)

    with get_connection(database_path) as connection:
        with transaction(connection):
            connection.execute(
                """
                INSERT INTO users(user_id, display_name, created_at, updated_at)
                VALUES ('usr_commit', 'Commit User', '2026-05-29T00:00:00Z', '2026-05-29T00:00:00Z')
                """
            )

        with pytest.raises(RuntimeError):
            with transaction(connection):
                connection.execute(
                    """
                    INSERT INTO users(user_id, display_name, created_at, updated_at)
                    VALUES ('usr_rollback', 'Rollback User', '2026-05-29T00:00:00Z', '2026-05-29T00:00:00Z')
                    """
                )
                raise RuntimeError("force rollback")

        rows = connection.execute("SELECT user_id FROM users").fetchall()
        user_ids = {row["user_id"] for row in rows}

    assert "usr_commit" in user_ids
    assert "usr_rollback" not in user_ids
