# Ego Data Core Development Status

**Last updated**: 2026-05-29
**Branch**: `main`
**Current phase**: M0/M1 foundation
**Active issue**: none; next recommended issue is `EDC-029`

## Collaboration Model

We will treat `docs/Ego_Data_Core_v0.1_Codex_Development_Taskbook.md` as the execution source of truth. Product and architecture docs define intent and constraints; the taskbook defines implementation order.

Working agreement:

1. Work on one EDC issue at a time.
2. Before coding, state the issue, acceptance criteria, expected files, and test plan.
3. Keep each commit atomic: one coherent change, one reason.
4. Update this status file when an issue starts, completes, blocks, or changes scope.
5. After each issue, report commit hash, changed areas, tests run, and remaining risks.
6. If docs conflict, prefer the taskbook for v0.1 delivery and record the decision here.

## Git Rules

Commit style:

- `chore: ...` for repo, docs, tooling, and maintenance.
- `EDC-000: ...` for issue implementation commits.
- `test: ...` only when the commit is test-only.
- `fix: ...` for narrow corrections after a completed issue.

Atomic commit examples:

- `EDC-000: add FastAPI health skeleton`
- `EDC-001: add SQLite migration runner`
- `EDC-006: scan files into raw object records`

Each implementation commit should include the relevant tests unless splitting is clearer.

## Progress Snapshot

| Area | Status | Notes |
|---|---|---|
| Git repository | Done | Initialized on `main`; design baseline committed. |
| Design docs | Done | Existing v0.1 docs committed unchanged. |
| Project skeleton | Done | `EDC-000` completed: src-layout FastAPI skeleton, health endpoint, README, env example, and tests. |
| Database and migrations | Done | `EDC-001` completed: SQLite migration runner, bundled schema, connection helper, transaction wrapper, and health DB status. |
| ID/config/test foundation | In progress | `EDC-002` and `EDC-003` completed; next `EDC-029`. |
| Audit/source/vault scan | Not started | M1 chain after DB foundation. |
| Document parsing | Not started | `EDC-008`. |
| Model/router/enhancement | Not started | RuleBasedAdapter first; Ollama optional. |
| Work graph and brief | Not started | Needed for demo value chain. |
| CLI/demo | Not started | CLI before UI for early demo speed. |

## Latest Iteration

### EDC-003 - Configuration System And Local Directory Layout

Status: completed.

Position in the project:

- This iteration turns the local runtime layout into an explicit contract before Source, Vault, Audit, and background jobs start writing data.
- It replaces the temporary workspace-local fallback from EDC-001 with the product-intended default: `~/.ego_data_core`, while tests continue to isolate data through temporary `EGO_DATA_HOME` values.

What changed:

- Added `src/ego_data_core/kernel/config.py`.
- Added `load_settings`, `EgoSettings`, `EgoPaths`, profile validation, and directory creation.
- Supported `dev`, `test`, and `prod` profiles through `EGO_PROFILE`.
- Formalized `EGO_DATA_HOME`, defaulting to `~/.ego_data_core`.
- Created stable runtime paths for `config`, `db`, `vault`, `objects`, `versions`, `evidence`, `extracted_text`, `model_outputs`, `briefs`, `logs`, and `tmp`.
- Updated the SQLite layer to read its default database path from the configuration system.
- Updated `.env.example`, `README.md`, and kernel exports.
- Added `tests/kernel/test_config.py`.

Validation:

- `.venv\Scripts\python -m pytest tests/kernel/test_config.py tests/storage/test_db_init.py tests/test_health.py` passed.
- Tests confirmed default home path without creating it, env override behavior, required directory creation, profile validation, and profile-specific config file paths.

Issues handled:

- We avoided creating real user-home data during tests by using `create_dirs=False` for default-path assertions and temporary `EGO_DATA_HOME` values for write behavior.
- The database layer no longer owns local path policy; it delegates default location to the kernel configuration module.

Next iteration:

- Start `EDC-029`: establish shared pytest fixtures for temporary `EGO_DATA_HOME`, database isolation, sample files, and API test client reuse.

### EDC-002 - Unified ID Generator

Status: completed.

Position in the project:

- This iteration gives all later persisted entities a common local ID format before we start creating Source, Object, Evidence, Job, or Audit records.
- It keeps ID generation independent of the database so future scanners and workers can create IDs without shared mutable state.

What changed:

- Added `src/ego_data_core/kernel/id_generator.py`.
- Added a whitelisted prefix set covering the v0.1 required prefixes: `usr`, `dev`, `src`, `obj`, `ver`, `ev`, `chk`, `enh`, `proj`, `task`, `q`, `risk`, `auto`, `brief`, `job`, `mi`, `act`, `aud`, `report`, and `item`.
- Implemented IDs in the form `<prefix>_<YYYYMMDD>_<secure_base32_suffix>`.
- Added prefix normalization, parsing, and clear invalid-prefix errors.
- Re-exported `generate_id` from `ego_data_core.kernel`.
- Added `tests/kernel/test_id_generator.py`.

Validation:

- `.venv\Scripts\python -m pytest tests/kernel/test_id_generator.py` passed.
- The collision test generated 100,000 `ev` IDs with no collision.

Issues handled:

- No external ULID package was added. The generator uses Python's `secrets` module and a Crockford-style Base32 alphabet, keeping the foundation light and offline.
- The date segment makes IDs easy to inspect and group even though within-day ordering is intentionally not promised yet.

Next iteration:

- Start `EDC-003`: formalize local configuration and directory layout so database, vault, logs, model outputs, and temporary files all use one explicit `EGO_DATA_HOME` strategy.

### EDC-001 - SQLite Initialization And Migration Management

Status: completed.

Position in the project:

- This iteration validates the first hard technical dependency for the evidence pipeline: a local SQLite database can be created repeatably from the v0.1 schema.
- It does not yet create Ego business records; it only proves that the storage layer can safely initialize the schema that later Source, Evidence, Audit, and Brief modules will use.

What changed:

- Added `src/ego_data_core/storage/db.py` with `get_connection`, `transaction`, `run_migrations`, and database health helpers.
- Bundled the schema as `src/ego_data_core/storage/migrations/001_init.sql`.
- Updated `/api/v1/health` to report real database status instead of the EDC-000 placeholder.
- Added FastAPI startup migration through application lifespan.
- Updated `scripts/init_db.py` to run migrations.
- Added `tests/storage/test_db_init.py` for schema creation, key tables, foreign keys, idempotence, and transactions.
- Updated `README.md` with current database initialization behavior.

Validation:

- `.venv\Scripts\python -m pytest tests/test_health.py tests/storage/test_db_init.py` passed.
- `.venv\Scripts\python scripts\init_db.py` created the local SQLite database on first run.
- A second `.venv\Scripts\python scripts\init_db.py` reported no pending migrations.
- FastAPI startup created the database before the first health request in a temporary `EGO_DATA_HOME`.
- `get_database_status()` returned `status=ok`, `foreign_keys=true`, `table_count=42`, and `migration_count=1`.

Issues handled:

- We avoided writing to the user home directory before `EDC-003` formalizes configuration. The temporary default is workspace-local `.ego_data_core/`, which is git-ignored.
- The schema is kept inside the Python package so runtime code and tests can find it consistently.

Next iteration:

- Start `EDC-002`: implement the unified ID generator used by users, devices, sources, objects, evidence, jobs, audit records, and later business entities.

### EDC-000 - Project Foundation

Status: completed.

Position in the project:

- This iteration turns the repo from a docs-only baseline into a runnable Python/FastAPI project.
- It creates the foundation needed by all later issues: imports, package metadata, API app factory, route layout, test entry point, and local startup commands.

What changed:

- Added `pyproject.toml` with FastAPI, Uvicorn, pytest, and httpx dev dependencies.
- Added `src/ego_data_core/` using the planned module boundaries.
- Added `GET /api/v1/health` with version and database status.
- Added `README.md`, `.env.example`, and non-destructive `scripts/init_db.py` placeholder.
- Added `tests/test_health.py`.

Validation:

- `.venv\Scripts\python -m pytest tests/test_health.py` passed.
- `.venv\Scripts\python scripts\init_db.py` confirmed no files were modified.
- `.venv\Scripts\python -m ego_data_core.main` started the API.
- `GET http://127.0.0.1:8765/api/v1/health` returned `ok`, version `0.1.0`, and database status `not_configured`.

Issues handled:

- The system Python did not have `pytest`; a local `.venv` was created and dependencies were installed there.
- Uvicorn did not stop cleanly from the TTY during smoke testing; the smoke-test process was stopped by PID after the health check succeeded.

Next iteration:

- Start `EDC-001`: add SQLite initialization and migration management using `docs/ego_data_core_v0_1_schema.sqlite.sql`.

## Near-Term Execution Order

```text
EDC-000 -> EDC-001 -> EDC-002 -> EDC-003 -> EDC-029 -> EDC-028
  -> EDC-004 -> EDC-005 -> EDC-006 -> EDC-007
  -> EDC-008 -> EDC-010 -> EDC-011 -> EDC-013
  -> EDC-014/EDC-015 minimal -> EDC-017 -> EDC-018 -> EDC-025 -> EDC-026
```

## Current Decisions

| Date | Decision | Reason |
|---|---|---|
| 2026-05-29 | Use taskbook priority when product and task docs differ. | The taskbook is already issue-shaped and better for incremental delivery. |
| 2026-05-29 | CLI and Markdown brief come before polished UI. | Fastest path to a reliable evidence-backed demo. |
| 2026-05-29 | RuleBasedAdapter is required before optional model adapters. | Demo must run without Ollama or cloud APIs. |
| 2026-05-29 | Use workspace-local `.ego_data_core/` until EDC-003 formalizes config. | Avoid surprising writes to the user home directory while validating database mechanics. |
| 2026-05-29 | EDC-003 restores the product default `~/.ego_data_core`; tests must use temporary `EGO_DATA_HOME`. | Align runtime behavior with the v0.1 docs while keeping development verification isolated. |

## Status Report Format

At the end of each work unit, Codex should report:

- Current issue and status.
- Commit hash and message.
- Files changed.
- Tests run and result.
- Any risks, blockers, or doc conflicts.
- Recommended next issue.
