"""Initialize the local Ego Data Core SQLite database."""

from __future__ import annotations

from ego_data_core.storage.db import run_migrations


def main() -> int:
    result = run_migrations()
    if result.applied:
        print(f"Applied migrations: {', '.join(result.applied)}")
    else:
        print("No pending migrations.")
    print(f"Database initialized at: {result.database_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
