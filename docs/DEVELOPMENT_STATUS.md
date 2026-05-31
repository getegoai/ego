# Ego Data Core Development Status

**Last updated**: 2026-05-31
**Branch**: `main`
**Current phase**: M1 DB + Source + Vault
**Active issue**: none; next recommended issue is `EDC-011`

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
| ID/config/test foundation | Done | `EDC-002`, `EDC-003`, and `EDC-029` completed. |
| Audit/source/vault scan | Done | `EDC-004` through `EDC-007` completed; scanner now writes version payloads through `VaultStorage`. |
| Document parsing | Done | `EDC-008` completed: scanned versions can produce extracted text and evidence text chunks. |
| Model/router/enhancement | In progress | `EDC-010` completed; next `EDC-011` RuleBasedAdapter, then `EDC-013` enhancement pipeline. |
| Work graph and brief | Not started | Needed for demo value chain. |
| CLI/demo | Not started | CLI before UI for early demo speed. |

## Latest Iteration

### EDC-010 - Night Shift Job Queue v0

Status: completed.

Position in the project:

- This is the local background-work control layer. Ego now has an explicit way to represent work, retries, failures, and completion.
- It prepares the project for model enhancement and daily brief generation, where work should run as traceable jobs rather than hidden direct calls.
- It also gives the user a clearer future status surface: pending, running, succeeded, failed, blocked, and cancelled.

What changed:

- Added `src/ego_data_core/nightshift/queue.py`.
- Added `NightShiftQueue.create_job(...)`, `claim_next_job()`, `mark_succeeded(...)`, `mark_failed(...)`, `mark_blocked(...)`, `cancel_job(...)`, and `get_job(...)`.
- Jobs are claimed by `priority ASC`, then `created_at ASC`.
- Failed jobs record `error_message`, increment `retry_count`, and return to `pending` until `max_retries` is exhausted.
- Every job lifecycle transition writes an audit event.
- Added `src/ego_data_core/nightshift/worker.py`.
- Added `NightShiftWorker` with handler registration, `run_once()`, `run_forever(...)`, and `request_stop()`.
- Worker jobs without handlers are marked `blocked` instead of disappearing silently.
- Added `tests/nightshift/test_queue.py`.

Validation:

- `.venv\Scripts\python -m pytest tests/nightshift/test_queue.py` passed with 8 tests.
- `.venv\Scripts\python -m pytest` passed with 72 tests.

Issues handled:

- Numeric priority is treated as a queue priority where lower values run first, matching the existing SQLite index shape.
- Retries are explicit: a failure can reschedule the job as `pending`, and final exhaustion becomes `failed`.
- Worker shutdown is cooperative; it finishes the current job and then stops.

Next iteration:

- Start `EDC-011`: Model Router interface and RuleBasedAdapter. This will give the enhancement pipeline a no-network, deterministic model substitute for summaries and tags.

### EDC-008 - Document Parser v0

Status: completed.

Position in the project:

- This is the first content-understanding step. Ego can now turn scanned document versions into extracted text and chunk records.
- It connects the ingestion foundation to later search, model routing, enhancement, and daily brief generation.
- This is the first layer where the product starts moving from "I found files" toward "I can read and reason over evidence".

What changed:

- Added `src/ego_data_core/connectors/documents/parser.py`.
- Added `DocumentParser.parse_version(version_id)` for parsing a single object version.
- Added `DocumentParser.parse_unparsed_versions(...)` for batch parsing without stopping on unsupported or failed files.
- Supported `.txt`, `.md`, `.pdf`, and `.docx` extraction.
- Added `pypdf` and `python-docx` as lightweight parser dependencies, while keeping imports lazy so parser failures can be handled cleanly.
- Wrote extracted text to `vault://extracted_text/{version_id}.txt`.
- Wrote paragraph-aware text chunks to `evidence_text_chunks` with `evidence_id`, `chunk_index`, `text`, `token_count`, `char_start`, and `char_end`.
- Wrote the same chunks into `evidence_text_fts` so later local search can build on the parser output.
- Unsupported file types create a failed `jobs` row and an `error` audit event, while other files continue parsing.
- Added `tests/connectors/test_document_parser.py`.

Validation:

- `.venv\Scripts\python -m pytest tests/connectors/test_document_parser.py` passed with 5 tests.
- `.venv\Scripts\python -m pytest` passed with 64 tests.

Issues handled:

- PDF and DOCX parsing require optional parser libraries. They are now project dependencies, and the parser still reports a clean failure if a dependency is unavailable in another environment.
- Unsupported files such as `.xlsx` are not silently ignored; they produce a failed parse result, a failed job record, and an error audit record.
- Empty but valid documents, such as a blank PDF, are treated as successful parses with zero chunks.

Next iteration:

- Start `EDC-010`: local job queue. This will let scanning, parsing, and later enhancement run as explicit work units instead of only direct service calls.

### EDC-007 - Vault File Storage And URI Rules

Status: completed.

Position in the project:

- This is the local storage safety layer for every later artifact: object versions, evidence files, extracted text, model outputs, and briefs.
- It keeps the ingestion pipeline from directly stitching local filesystem paths together.
- It is a required bridge from "files can be scanned" to "files can be parsed, summarized, and exported".

What changed:

- Added `src/ego_data_core/vault/storage.py`.
- Added `VaultStorage.resolve_uri(...)` for mapping `vault://...` URIs into `EGO_DATA_HOME/vault/...`.
- Added safe helpers for `safe_write_json`, `safe_write_text`, `safe_copy_file`, and `read_text`.
- Supported `vault://objects`, `vault://versions`, `vault://evidence`, `vault://extracted_text`, `vault://model_outputs`, and `vault://briefs`.
- Rejected malformed or unsafe vault URIs, including traversal, encoded traversal, backslashes, drive separators, query strings, fragments, and unknown collections.
- Added `build_vault_uri(...)` for generated vault filenames; it only accepts plain filenames and URL-encodes safe names.
- Updated the filesystem scanner so version payload copies go through `VaultStorage` rather than manually writing under the versions directory.
- Added `tests/vault/test_storage_uri.py`.

Validation:

- `.venv\Scripts\python -m pytest tests/vault/test_storage_uri.py tests/connectors/test_filesystem_scanner.py` passed with 23 tests.
- `.venv\Scripts\python -m pytest` passed with 59 tests.

Issues handled:

- The first draft could accidentally preserve a Windows-style path string inside a generated vault URI. This was tightened so generated vault URIs reject path-like names.
- Vault storage filenames now avoid exposing the original absolute source path. Source identity is still recorded in the database as `original_uri`, while stored payload files use generated IDs.

Next iteration:

- Start `EDC-008`: document parser v0. This should turn scanned object versions into extracted text and text chunks, which is the first more concrete product-facing layer after ingestion.

### EDC-006 - Read-Only Filesystem Scanner

Status: completed.

Position in the project:

- This is the first concrete evidence-ingestion step. Ego can now scan an authorized filesystem source and turn files into database records.
- It is still not a full product UI, but it proves the core pipeline shape: Source -> Raw Object -> Object Version -> Evidence -> Audit.

What changed:

- Added `src/ego_data_core/connectors/filesystem/scanner.py`.
- Added `FilesystemScanner.scan_source(source_id)`.
- The scanner reads `sources.root_uri` and `scan_policy_json`.
- It recursively scans files with `max_depth`, `include_globs`, and `exclude_globs`.
- It calculates SHA-256, file size, mtime, and MIME type.
- It creates `raw_objects`, `object_versions`, and `evidence`.
- It copies version payloads into the local versions vault without modifying source files.
- Same-hash duplicates reuse the existing version storage URI and mark duplicate metadata.
- Repeated scans skip unchanged files.
- Modified files create a new object version and new evidence.
- Scan-created objects and evidence write audit events.
- Added `tests/connectors/test_filesystem_scanner.py`.

Validation:

- `.venv\Scripts\python -m pytest tests/connectors/test_filesystem_scanner.py` passed.

Issues handled:

- Duplicate-file testing initially used text write on Windows, which changed line endings and produced a different hash. The test now copies bytes to verify true same-hash duplicate behavior.
- The scanner only reads from the source directory. It does not move, rename, delete, or rewrite user files.

Next iteration:

- Start `EDC-007`: formalize `vault://` URI resolution and safe file operations so version/evidence/model/brief storage has a shared safety layer.

### EDC-005 - Source Management API

Status: completed.

Position in the project:

- This is the first user-visible data setup step. Ego can now register an authorized data source before any scanner touches files.
- It connects the control-plane work from previous iterations: Source records go into SQLite and creation is written to Audit.

What changed:

- Added `src/ego_data_core/connectors/source_service.py`.
- Added `GET /api/v1/sources` and `POST /api/v1/sources`.
- Source creation supports `source_type`, `name`, `root_uri`, `privacy_level`, `scan_policy`, and `retention_policy`.
- `privacy_level` defaults to `private`.
- `POST /sources` creates a local default user if no user exists yet, keeping the app single-user without adding authentication scope.
- `POST /sources` writes a `source_created` audit event.
- Added `tests/api/test_sources.py`.

Validation:

- `.venv\Scripts\python -m pytest tests/api/test_sources.py` passed.

Issues handled:

- The OpenAPI create-source request does not include `user_id`, while the schema requires one. For v0.1 local single-user mode, the service ensures a local default user and attaches sources to it.
- This issue intentionally does not scan or read the configured `root_uri`; it only records authorization intent.

Next iteration:

- Start `EDC-006`: filesystem scanner v0. This is the first real data-ingestion step: read an authorized source directory, hash files, and create Raw Object / Version / Evidence records without modifying user files.

### EDC-004 - Audit Log Minimal Implementation

Status: completed.

Position in the project:

- This is the first control-plane feature. Before Ego starts creating sources, scanning files, or generating evidence, it can now record what happened.
- Audit is the user's future "black box recorder": it lets us explain data changes, errors, policy blocks, model calls, and authorizations.

What changed:

- Added `src/ego_data_core/audit/service.py`.
- Added `AuditService.append_audit_log(...)` and `list_audit_logs(...)`.
- Added append-only behavior at the service API level: no update/delete audit methods are exposed.
- Added hash chaining with `prev_hash` and `event_hash`.
- Added support for key event types such as `source_created`, `object_ingested`, `evidence_created`, `job_created`, `model_invoked`, `policy_blocked`, `brief_generated`, `action_authorized`, and `error`.
- Added `GET /api/v1/audit/logs` with pagination and basic filters.
- Added `tests/audit/test_audit_service.py`.

Validation:

- `.venv\Scripts\python -m pytest tests/audit/test_audit_service.py` passed.

Issues handled:

- Audit payloads are required to be JSON serializable so records can safely enter SQLite.
- Invalid actor types fail early with a clear error.
- Error events are explicitly supported and tested.

Next iteration:

- Start `EDC-005`: Source Management API. This is the first user-facing data setup step: creating/listing authorized data sources, with audit records on creation.

### EDC-029 - Test Foundation And Temporary Workspace Fixtures

Status: completed.

Position in the project:

- This iteration makes future development safer and easier to verify. It ensures tests do not depend on a developer's real local data directory.
- It prepares the project for the next product-relevant chain: Audit, Source, file scanning, and Evidence creation.

What changed:

- Added `tests/conftest.py` with shared fixtures:
  - `tmp_data_home`
  - `db_path`
  - `migrated_db_path`
  - `client`
  - `sample_workspace`
  - `sample_documents`
- Added safe sample files under `tests/fixtures/sample_workspace/`.
- Updated the health test to use the shared API client fixture.
- Added `tests/test_fixtures.py` to prove fixtures isolate data, create a migrated DB, reuse the API client, and provide sample txt/md files.

Validation:

- `.venv\Scripts\python -m pytest` passed with 23 tests.

Issues handled:

- A first assertion assumed pytest temp directories would never live under the user home. On Windows, pytest temp paths can sit under the user's AppData temp directory. The test was corrected to assert the real safety condition: fixtures do not write to the default `~/.ego_data_core`.
- PDF/DOCX sample support is intentionally represented as `None` for now; text and Markdown samples are enough for the scanner/parser foundation until optional document dependencies are introduced.

Next iteration:

- Start `EDC-004`: append-only Audit Log service and `/api/v1/audit/logs`, so data mutations and errors can be traced before Source and scanner features start creating records.

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
