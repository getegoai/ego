# Ego Data Core Development Status

**Last updated**: 2026-07-12
**Branch**: `main`
**Current phase**: v0.1 technical loop complete / EgoBase product reset
**Active issue**: paused; `EDC-024` is frozen pending EgoLink-EgoBase contract validation

## Parent Program Note

This project moved to `projects/egobase/data-core` on 2026-07-12. It is now
treated as the software evidence/agent runtime prototype for EgoBase, not the
complete Ego product or a finalized hardware definition. The original v0.1
taskbook remains historical execution evidence; new work follows the parent
program status at `../../../../docs/DEVELOPMENT_STATUS.md`.

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
| ID/config/test foundation | Done | `EDC-002`, `EDC-003`, `EDC-028`, and `EDC-029` completed. |
| Audit/source/vault scan | Done | `EDC-004` through `EDC-007` completed; scanner now writes version payloads through `VaultStorage`. |
| Document parsing/search | Done | `EDC-008` and `EDC-009` completed: parsed evidence chunks are searchable through local FTS with LIKE fallback. |
| Model/router/enhancement | Done | `EDC-010`, `EDC-011`, `EDC-013`, and `EDC-020` completed. |
| Work graph and brief | Done | `EDC-014`, `EDC-015`, `EDC-016`, `EDC-017`, `EDC-018`, and `EDC-027` completed. |
| Operator Bridge | Done | `EDC-021` completed: automation opportunities can become authorized dry-run action plans without executing computer actions. |
| API contract | Done | `EDC-030` completed: generated OpenAPI is contract-tested and draft differences are documented. |
| Screen capture | Done | `EDC-022` completed: existing image files can be imported as screenshot evidence through API or CLI. |
| Screenshot OCR | Done | `EDC-023` completed: screenshot evidence can produce OCR text and screen-state enhancements with an unsupported fallback. |
| Local Web UI | Done | `EDC-019` completed: root URL serves a local-only browser workspace for dashboard, sources, search, brief, and audit. |
| CLI/demo | Done | `EDC-025` and `EDC-026` completed: CLI loop plus synthetic one-command demo. |

## Latest Iteration

### EDC-023 - Screenshot OCR Enhancement

Status: completed.

Position in the project:

- This turns screenshot evidence into Twin-level enhancements rather than leaving images as opaque vault payloads.
- It completes the minimum screen evidence loop: import screenshot -> create screenshot evidence -> generate OCR/screen-state enhancements -> query linked enhancements.
- It keeps optional OCR engines out of the critical path. v0.1 can record `unsupported` cleanly when OCR is unavailable.

What changed:

- Added `src/ego_data_core/twin/screenshot_ocr.py`.
- Added `OCRAdapter`, `UnsupportedOCRAdapter`, and `MockOCRAdapter`.
- Added `ScreenshotOCRService.enhance_screenshots(...)`.
- Added `ocr_text` enhancements linked to screenshot evidence.
- Added `screen_state` enhancements preserving `active_window`, `app_name`, regions, and `image_pixels` coordinate metadata.
- Added `POST /api/v1/twin/screens/ocr`.
- Added `ego screen ocr <evidence_id>`.
- Updated README and API contract docs.
- Added `tests/twin/test_screenshot_ocr.py`.

Validation:

- `.venv\Scripts\python -m pytest tests/twin/test_screenshot_ocr.py -q` passed with 5 tests.
- `.venv\Scripts\python -m pytest tests/connectors/test_screen_capture.py tests/twin/test_screenshot_ocr.py tests/api/test_openapi_contract.py tests/cli/test_cli.py -q` passed with 16 tests.
- `.venv\Scripts\python -m pytest -q` passed with 135 tests.

Issues handled:

- No OCR environment is treated as an explicit unsupported result, not a crash.
- The database status column cannot store `unsupported`; the `ocr_text` enhancement uses `status=error` while its content carries `status=unsupported`.
- OCR and screen-state enhancements both link back to the source screenshot evidence.
- The mock adapter exists only as a deterministic local/dev path until a real OCR adapter is selected.

Historical next iteration:

- `EDC-024` was originally next. It is now frozen pending the parent EgoBase product and EgoLink contract reset.

### EDC-022 - Manual Screenshot Capture Connector

Status: completed.

Position in the project:

- This extends the evidence pipeline beyond filesystem documents into screen-state evidence.
- It is the required upstream step for `EDC-023` Screenshot OCR Enhancement.
- It keeps v0.1 capture manual and bounded: existing image import only, no continuous recording and no HDMI driver.

What changed:

- Added `src/ego_data_core/connectors/screen/capture.py`.
- Added `ScreenCaptureService.import_image_file(...)`.
- Added `POST /api/v1/screen/import`.
- Added `ego screen import <image_path> --source-id <src_id>`.
- Screenshot import now creates `raw_objects`, `object_versions`, and `evidence` with `evidence_type=screenshot`.
- Screenshot metadata records optional `active_window` and `app_name`.
- Updated README and API contract docs.
- Added `tests/connectors/test_screen_capture.py`.

Validation:

- `.venv\Scripts\python -m pytest tests/connectors/test_screen_capture.py -q` passed with 4 tests.
- `.venv\Scripts\python -m pytest tests/api/test_openapi_contract.py -q` passed with 4 tests.

Issues handled:

- API and CLI responses return vault IDs and `vault://` URIs, not the original absolute image path.
- Source validation happens before vault copy to avoid orphan payloads for invalid source IDs.
- Unsupported image MIME types fail with a validation error instead of entering the vault.

Next iteration:

- Start `EDC-023`: generate OCR-related enhancements from screenshot evidence. The first pass should tolerate missing OCR engines and write an explicit unsupported status.

### EDC-030 - OpenAPI Contract Tests

Status: completed.

Position in the project:

- This stabilizes the API surface after the minimum closed loop was completed.
- It locks the core local API paths used by sources, vault/search, twin, briefs, actions, and audit.
- It documents known differences between the original OpenAPI draft and the implemented v0.1 local API.

What changed:

- Added `tests/api/test_openapi_contract.py`.
- Added `docs/api_contract.md`.
- Updated README to identify `/openapi.json` as the generated v0.1 local API contract.
- Contract tests now verify `/openapi.json`, core implemented paths, implementation extensions, draft-only differences, and key request schemas.

Validation:

- `.venv\Scripts\python -m pytest tests/api/test_openapi_contract.py` passed with 4 tests.

Issues handled:

- Draft-only `/vault/ingest`, `/vault/evidence/{evidence_id}`, `/projects/{project_id}`, and `/model-router/run` are documented as intentional current differences.
- `/api/v1/search` is documented as the current Evidence/Vault search surface.
- Work Graph and Automation routes are documented as v0.1 implementation extensions needed by the closed loop.

Next iteration:

- Start `EDC-022`: manual screenshot capture connector. API contract is now stable enough to extend ingestion beyond filesystem documents.

### EDC-021 - Operator Bridge Action Plan Dry-run

Status: completed.

Position in the project:

- This completes the v0.1 minimum closed loop: local files become evidence, evidence becomes work context and automation opportunities, opportunities become action plans, and action plans can be dry-run under authorization control.
- It keeps Operator Bridge strictly non-destructive in v0.1. No files, windows, network calls, uploads, sends, or computer controls are executed.
- It gives the demo a concrete end-to-end safety story: execution is blocked before authorization and remains dry-run after authorization.

What changed:

- Added `src/ego_data_core/operator/bridge.py`.
- Added `ActionPlanRecord`.
- Added `OperatorBridge.propose_action(...)`.
- Added `OperatorBridge.authorize_action(...)`.
- Added `OperatorBridge.execute_action(...)`.
- Added `POST /api/v1/actions/propose`.
- Added `POST /api/v1/actions/{action_id}/authorize`.
- Added `POST /api/v1/actions/{action_id}/execute`.
- Extended the demo loop to discover automation opportunities and run an authorized dry-run action plan.
- Added `tests/operator/test_action_dry_run.py`.
- Extended `tests/demo/test_demo_smoke.py`.

Validation:

- `.venv\Scripts\python -m pytest tests/operator/test_action_dry_run.py` passed with 2 tests.
- `.venv\Scripts\python -m pytest tests/operator/test_action_dry_run.py tests/demo/test_demo_smoke.py` passed with 3 tests.
- `.venv\Scripts\python -m pytest` passed with 122 tests.
- `.venv\Scripts\python scripts/run_demo.py --data-home .\.ego_data_core\closed_loop_demo --date 2026-06-04` completed the minimum closed loop: 5 evidence items parsed, 1 automation opportunity found, action execution blocked before authorization, and authorized dry-run completed with 4 dry-run steps.

Issues handled:

- `execute` before authorization returns `requires_authorization`.
- `authorize` writes an authorization record and audit event.
- Authorized `execute` returns `dry_run_completed` and marks action steps as skipped with `dry_run_only`.
- propose, authorize, blocked execute, and dry-run execute all write audit events.

Next iteration:

- Start `EDC-030`: OpenAPI contract tests. The minimum closed loop now has enough API surface that contract drift becomes the next practical risk.

### EDC-016 - Automation Opportunity Discovery

Status: completed.

Position in the project:

- This moves Ego from observing work items to proposing safe next actions.
- It is the required upstream input for Operator Bridge dry-run.
- It keeps the safety boundary intact: opportunities are proposed only, and no files are moved, deleted, sent, uploaded, or modified.

What changed:

- Added `src/ego_data_core/workgraph/automation_opportunities.py`.
- Added `AutomationOpportunityService`.
- Added `AutomationOpportunityRecord` and `automation_opportunity_to_dict(...)`.
- Added `POST /api/v1/workgraph/automations/discover`.
- Added `GET /api/v1/workgraph/automations`.
- Daily Brief now includes automation opportunities as `automation` report items.
- Added `tests/workgraph/test_automation_opportunities.py`.

Validation:

- `.venv\Scripts\python -m pytest tests/workgraph/test_automation_opportunities.py` passed with 2 tests.
- `.venv\Scripts\python -m pytest tests/workgraph/test_automation_opportunities.py tests/brief/test_daily_brief.py tests/brief/test_markdown_export.py` passed with 7 tests.

Issues handled:

- Duplicate files generate high-risk review proposals with evidence links.
- Loose intake folders such as `Downloads` generate high-risk review proposals before any move action.
- Any candidate action containing move, delete, send, or upload is forced to high risk and requires authorization.
- Discovery is idempotent through a stable `discovery_key`.

Next iteration:

- Start `EDC-021`: Operator Bridge dry-run. It will convert automation opportunities into action plans, enforce authorization, and produce dry-run steps without controlling the computer.

### EDC-019 - Local Web UI Minimum Version

Status: completed.

Position in the project:

- This is the first browser-visible product surface.
- It turns the existing local API into a usable operator workspace without adding a frontend framework.
- It lets the user inspect system health, source authorization, searchable evidence, latest Daily Brief, and audit events from `http://127.0.0.1:8765`.

What changed:

- Added `src/ego_data_core/ui/static/index.html`.
- Added `src/ego_data_core/ui/static/styles.css`.
- Added `src/ego_data_core/ui/static/app.js`.
- Added `src/ego_data_core/ui/__init__.py`.
- Mounted the UI root at `/` and static assets under `/ui`.
- Added `tests/api/test_static_ui.py`.
- Updated README with local UI run instructions.

Validation:

- `.venv\Scripts\python -m pytest tests/api/test_static_ui.py` passed with 3 tests.
- `.venv\Scripts\python -m pytest` passed with 118 tests.
- Local demo smoke passed against `http://127.0.0.1:8765`: root page returned 200, Search for `project` returned 4 FTS evidence results, and a Chrome headless screenshot was generated.

Issues handled:

- The UI uses only local `/api/v1/*` endpoints.
- API routes still work after mounting the static UI.
- Source views intentionally do not render `root_uri`, keeping local filesystem paths off the main screen.
- Evidence visibility is provided through Search results until a dedicated Evidence list API is added.

Next iteration:

- Start `EDC-016`: Automation Opportunity discovery. This unblocks `EDC-021` Operator Bridge dry-run and moves the product from observing work toward proposing safe next actions.

### EDC-009 - Local Full-Text Search

Status: completed.

Position in the project:

- This closes the skipped M2 search prerequisite before the local Web UI.
- It gives future UI screens a concrete Evidence search API instead of asking the interface to query raw tables.
- It keeps privacy boundaries intact by returning evidence IDs, chunk IDs, titles, snippets, dates, source IDs, and match information without returning `original_uri` or absolute local paths.

What changed:

- Added `src/ego_data_core/vault/search.py`.
- Added `LocalSearchService.search(...)`.
- Added `SearchResult` and `search_to_dict(...)`.
- Added `GET /api/v1/search`.
- Search uses SQLite FTS5 when available.
- Search falls back to case-insensitive LIKE matching when FTS5 is unavailable or disabled.
- Search supports `source_id`, `date_from`, `date_to`, and `limit`.
- Added `tests/vault/test_search.py`.

Validation:

- `.venv\Scripts\python -m pytest tests/vault/test_search.py` passed with 4 tests.

Issues handled:

- FTS output is shaped for UI use: `evidence_id`, `chunk_id`, `title`, `snippet`, `captured_at`, `source_id`, `chunk_index`, `score`, and `match_type`.
- API payloads intentionally omit local filesystem paths.
- LIKE fallback is tested directly with `prefer_fts=False`.
- Empty queries return the standard validation error payload through the API layer.

Next iteration:

- Start `EDC-019`: local Web UI minimum version. The UI can now show real data surfaces: data health, daily brief, source status, and searchable evidence.

### EDC-020 - Safety Kernel: Privacy and External-Call Policy

Status: completed.

Position in the project:

- This completes the missing privacy policy layer under Model Router and Enhancement Pipeline.
- It turns ad hoc model-call checks into shared Safety Kernel decisions that other modules can reuse.
- It makes critical data stricter than before: critical evidence cannot enter any model context by default, including local rule-based adapters, unless there is per-call authorization.

What changed:

- Added `src/ego_data_core/safety/policy.py`.
- Added `PolicyDecision`.
- Added `can_use_external_model(...)`.
- Added `can_include_evidence_in_context(...)`.
- Added `requires_authorization(...)`.
- Added privacy normalization and effective privacy calculation helpers.
- Policy blocks now append `policy_blocked` audit events from the Safety Kernel.
- Updated Model Router to call Safety Kernel for external model decisions and context inclusion decisions.
- Added `tests/safety/test_policy.py`.
- Extended `tests/model_router/test_rule_based.py` with a critical-data block case.

Validation:

- `.venv\Scripts\python -m pytest tests/safety/test_policy.py tests/model_router/test_rule_based.py` passed with 11 tests.

Issues handled:

- `public` data can use external models.
- `private` external model use requires `allow_external`.
- `sensitive` defaults to local-only/rule behavior; external use requires explicit `allow_external`.
- `critical` requires per-call authorization before model/context use.
- Existing sensitive external-call behavior remains compatible with explicit `allow_external`.

Next iteration:

- Start `EDC-009`: local full-text search. This is a skipped M2 prerequisite for `EDC-019` UI, because the UI is expected to show Evidence search.

### EDC-028 - Unified Errors and Logging

Status: completed.

Position in the project:

- This improves the reliability layer underneath API, CLI, and background jobs.
- It makes API failures predictable for future UI/CLI clients by returning stable JSON with `code`, `message`, and `request_id`.
- It adds a small logging safety layer so internal logs can keep IDs and operational context without dumping raw text fields.

What changed:

- Added `src/ego_data_core/kernel/errors.py`.
- Added `src/ego_data_core/kernel/logging.py`.
- Added `EgoError` plus `PolicyBlockedError`, `NotFoundError`, `ValidationError`, `ConnectorError`, `ModelError`, and `StorageError`.
- Added FastAPI exception handlers for Ego errors, request validation errors, `ValueError`, HTTP exceptions, and unhandled exceptions.
- API error responses now include stable `code`, `message`, and `request_id`; `x-request-id` is preserved when supplied.
- Night Shift worker failures now use a safe error message and log redacted job context.
- Added `tests/kernel/test_errors.py`.

Validation:

- `.venv\Scripts\python -m pytest tests/kernel/test_errors.py tests/api/test_sources.py tests/test_health.py tests/nightshift/test_queue.py` passed with 19 tests.

Issues handled:

- Existing services still raise some `ValueError`s. The API layer now normalizes those into stable `validation_error` responses while deeper service-specific errors can migrate to `EgoError` subclasses over time.
- Log redaction is conservative: fields such as `text`, `body`, `prompt`, `input`, and `output` are replaced with size markers while IDs remain visible.

Next iteration:

- Start `EDC-020`: Safety Kernel. Now that error responses and policy-block audit handling are stable, the privacy policy rules can be pulled out of Model Router into a shared safety layer.

### EDC-027 - Daily Brief Data Health

Status: completed.

Position in the project:

- This closes the M5 Daily Brief quality loop: the brief now explains not only what changed, but also how trustworthy the data pipeline was for that day.
- It gives the user a compact health panel for coverage, parser failures, enhancement completion, pending work, and privacy-policy blocks.
- It improves operator control before we add more UI, because the Markdown output itself now says what needs attention.

What changed:

- Added `src/ego_data_core/brief/data_health.py`.
- Added `DataHealthService.snapshot(...)` and `DataHealthSnapshot`.
- Daily Brief generation now appends a `data_health` report item every day.
- Data Health reports new file count, evidence count, parse success rate, parse failures, parse pending count, enhancement job completion, enhanced evidence coverage, policy-blocked external calls, failed jobs, pending jobs, severity, and recommendations.
- Markdown export now renders evidence-free system items as `System: data_health` instead of `Evidence: none`.
- Report metadata now includes the data health snapshot.
- Added `tests/brief/test_data_health.py`.

Validation:

- `.venv\Scripts\python -m pytest tests/brief/test_data_health.py tests/brief/test_daily_brief.py tests/brief/test_markdown_export.py tests/demo/test_demo_smoke.py` passed with 8 tests.

Issues handled:

- Unsupported document parse failures are surfaced through failed `document_parse` jobs and reflected in Data Health.
- Privacy policy blocks are counted from `policy_blocked` audit events, not inferred from text.
- No-data days now produce next-step setup guidance instead of a generic empty update.

Next iteration:

- Start `EDC-028`: unified errors and logging. This should make API and background-job failures easier to understand and safer to expose.

### EDC-026 - Demo Seed Data and One-Command Script

Status: completed.

Position in the project:

- This is the first product-level demo path.
- It lets a fresh local environment generate an evidence-backed Daily Brief without requiring a real private folder.
- It makes the current state easier to validate: the user can inspect one generated Markdown file and trace each factual item back to evidence.

What changed:

- Added synthetic demo files under `demo/sample_workspace/`.
- Included project plan, meeting notes, quote draft, todo list, and a duplicate file.
- Added `scripts/run_demo.py`.
- Added `scripts/run_demo.sh`.
- Added `docs/demo_script.md`.
- Updated `README.md` with the demo command.
- Added `tests/demo/test_demo_smoke.py`.

Validation:

- `.venv\Scripts\python -m pytest tests/demo/test_demo_smoke.py` passed with 1 test.

Issues handled:

- The taskbook asks for `scripts/run_demo.sh`; because this development machine is Windows, `scripts/run_demo.py` is the cross-platform implementation and `run_demo.sh` is a thin shell wrapper.
- Demo data is synthetic and intentionally avoids real private paths or personal content.
- The smoke test verifies that generated Markdown includes evidence references and does not expose the sample workspace absolute path.

Next iteration:

- Start `EDC-027`: Daily Brief Data Health. This should make the brief explain coverage, parse failures, missing enhancements, blocked jobs, and recommended next actions.

### EDC-025 - CLI Tools: Scan, Enhance, Generate Brief

Status: completed.

Position in the project:

- This is the first practical operator surface for local validation.
- It lets a user run the core loop without reading code or calling FastAPI directly.
- It intentionally comes before UI because it is faster to test, easier to automate, and enough for the first demo loop.

What changed:

- Added `src/ego_data_core/cli.py` using the standard library `argparse`.
- Added the `ego` console script in `pyproject.toml`.
- Added `ego init-db`.
- Added `ego source add <path>` and `ego source list`.
- Added `ego scan <source_id>`, which scans and parses unparsed document versions.
- Added `ego enhance --date YYYY-MM-DD --type tag|summary`, which creates and runs an enhancement job through Night Shift.
- Added `ego brief daily --date YYYY-MM-DD`, which refreshes Project Discovery and Work Item extraction before generating the Daily Brief.
- Added `ego audit tail`.
- Updated `README.md` with a CLI verification loop.
- Added `tests/cli/test_cli.py`.

Validation:

- `.venv\Scripts\python -m pytest tests/cli/test_cli.py` passed with 3 tests.

Issues handled:

- The taskbook lists `scan`, `enhance`, and `brief daily` but not a separate parse command. For a usable local loop, `ego scan` also parses unparsed document versions.
- `ego brief daily` refreshes Work Graph by default so the brief contains project/task/question/risk context without requiring hidden extra commands. `--skip-workgraph` exists for cases where the user wants report-only behavior.
- CLI errors return non-zero and write the error message to stderr.

Next iteration:

- Start `EDC-026`: demo seed data and one-command demo script. This should give the user the clearest possible product-level validation path.

### EDC-018 - Markdown Exporter and Evidence Reference Format

Status: completed.

Position in the project:

- This hardens the first visible product artifact from `EDC-017`.
- Daily Brief output now has a dedicated Markdown exporter instead of generator-local formatting.
- This makes CLI and demo work easier because they can reuse one export path and one evidence citation format.

What changed:

- Added `src/ego_data_core/brief/export_markdown.py`.
- Added `BriefMarkdownExporter.render_report(...)` and `export_report(...)`.
- Added stable evidence reference lines in the format `[ev_xxx] title / path / time / excerpt`.
- Evidence references use file title and scanner relative path; absolute local file URIs are not written into Markdown.
- Updated `DailyBriefService` to export Markdown through `BriefMarkdownExporter`.
- Exported `BriefMarkdownExporter` and `EvidenceReference` from the brief module.
- Added `tests/brief/test_markdown_export.py`.

Validation:

- `.venv\Scripts\python -m pytest tests/brief/test_markdown_export.py tests/brief/test_daily_brief.py` passed with 5 tests.

Issues handled:

- `EDC-017` already wrote Markdown. This iteration keeps that behavior but extracts the formatting into a reusable module, avoiding duplicate report rendering later.
- Evidence references intentionally do not use `raw_objects.original_uri`, because that field can contain a local absolute path.

Next iteration:

- Start `EDC-025`: CLI commands for init-db, source add, scan, enhance, brief daily, and audit tail. This is the fastest path for the user to run a complete local product loop without reading code.

### EDC-017 - Daily Brief Generator v0

Status: completed.

Position in the project:

- This is the first concrete user-facing product output: Ego can now turn scanned files, extracted evidence, enhancements, project candidates, tasks, questions, and risks into a daily Markdown brief.
- It moves the project from backend foundations into M5 Daily Brief, while still preserving the evidence-first rule: factual brief items carry evidence references.
- It gives the next development loop a visible artifact to improve instead of only internal tables and API payloads.

What changed:

- Added `src/ego_data_core/brief/daily.py`.
- Added `DailyBriefService.generate_daily_brief(...)`, `get_latest_daily_brief(...)`, `get_report(...)`, and `apply_item_feedback(...)`.
- Added `POST /api/v1/briefs/generate`.
- Added `GET /api/v1/briefs/daily/latest`.
- Added `POST /api/v1/briefs/items/{report_item_id}/feedback`.
- Daily Brief generation now writes `reports`, `report_items`, and `report_item_evidence_links`.
- Markdown exports are written to `vault://briefs` and saved back to report metadata as `markdown_uri`.
- Brief generation appends a `brief_generated` audit event.
- Empty days produce a `data_health` item rather than inventing unsupported conclusions.
- Added `tests/brief/test_daily_brief.py`.

Validation:

- `.venv\Scripts\python -m pytest tests/brief/test_daily_brief.py` passed with 3 tests.

Issues handled:

- `EDC-018` asks for a standalone Markdown exporter. For `EDC-017`, Markdown export is intentionally embedded in the generator so the product output exists now; `EDC-018` can extract and formalize citation formatting without blocking the first visible artifact.
- Automation opportunities are not implemented yet because the automation module is still pending. The brief generator leaves that lane out instead of inventing automation suggestions without a source.
- If no evidence exists for a date, the system outputs data health status only.

Next iteration:

- Start `EDC-018`: split/formalize Markdown export and evidence reference format, then proceed toward CLI/demo so the user can run a complete local loop without reading code.

### EDC-015 - Task / Question / Risk Extraction v0

Status: completed.

Position in the project:

- This turns evidence-backed text into actionable Work Graph items.
- It builds on Project Discovery, Enhancement Pipeline, and RuleBasedAdapter output, while keeping every generated item linked back to Evidence.
- It is the last major prerequisite before generating a useful Daily Brief.

What changed:

- Added `src/ego_data_core/workgraph/extractors.py`.
- Added `WorkItemExtractor.extract_items(...)` to generate tasks, questions, and risks.
- Added `WorkItemExtractor.apply_feedback(...)` for `confirm`, `reject`, `edit`, `later`, and `convert_to_task`.
- Added `POST /api/v1/workgraph/extract`.
- Added `GET /api/v1/workgraph/items`.
- Added `POST /api/v1/workgraph/items/{item_type}/{item_id}/feedback`.
- Task/risk candidates use `ModelRouter` with `RuleBasedAdapter` purposes `task_candidate` and `risk_candidate`.
- Question candidates use local question-cue rules.
- Generated tasks, questions, and risks are linked to Evidence through `graph_edges`.
- Generated items are linked to discovered projects through `project_links` when a project relationship exists.
- Added `tests/workgraph/test_extractors.py`.

Validation:

- `.venv\Scripts\python -m pytest tests/workgraph/test_extractors.py` passed with 3 tests.
- `.venv\Scripts\python -m pytest` passed with 87 tests.

Issues handled:

- The existing task/question/risk tables do not include a `proposed` enum value. For v0.1, proposed state is represented as `status='open'`, `user_confirmed=0`, and `metadata.workflow_status='proposed'`.
- There is no dedicated task-evidence link table. Evidence traceability is represented through `graph_edges` with `relation_type='supports'` and `evidence_id` set.

Next iteration:

- Start `EDC-017`: Daily Brief generator v0. It can now aggregate Evidence, Enhancements, Projects, Tasks, Questions, and Risks into the first real user-facing brief.

### EDC-014 - Project Discovery v0

Status: completed.

Position in the project:

- This is the first Work Graph step. Ego can now group evidence into project candidates instead of treating all evidence as isolated files.
- It uses rule-first discovery from directories, file names, and tag enhancements, keeping model output as a hint rather than a fact.
- It prepares the next extraction layer: tasks, questions, and risks can attach to a project candidate.

What changed:

- Added `src/ego_data_core/workgraph/project_discovery.py`.
- Added `ProjectDiscoveryService.discover_projects(...)`, `list_projects(...)`, `get_project(...)`, and `apply_feedback(...)`.
- Added `POST /api/v1/projects/discover`.
- Added `GET /api/v1/projects`.
- Added `POST /api/v1/projects/{project_id}/feedback`.
- Project candidates are stored in `projects` with `user_confirmed=0`.
- Evidence and raw objects are linked through `project_links` with confidence scores.
- User feedback supports `confirm`, `reject`, and `edit`.
- Rejected project candidates are not regenerated unless `force_regenerate=true`.
- Added `tests/workgraph/test_project_discovery.py`.

Validation:

- `.venv\Scripts\python -m pytest tests/workgraph/test_project_discovery.py` passed with 3 tests.
- `.venv\Scripts\python -m pytest` passed with 84 tests.

Issues handled:

- The schema has no separate project candidate table or rejected status. For v0.1, candidates use `projects.user_confirmed=0`; rejected candidates use `status='archived'` plus metadata.
- Discovery is explicitly inferential. Confidence and metadata identify the rule-based discovery method.

Next iteration:

- Start `EDC-015`: Task / Question / Risk extraction v0. This will turn enhanced evidence and text chunks into actionable work graph objects.

### EDC-013 - Enhancement Pipeline summary/tag

Status: completed.

Position in the project:

- This is the first traceable insight pipeline. Ego can now create a job, read evidence text chunks, run the Model Router, and store an Enhancement linked back to Evidence.
- It connects the previous foundations: Document Parser, Night Shift Queue, Model Router, Vault model outputs, `enhancements`, and `enhancement_evidence_links`.
- This is the first product-relevant loop where scanned local files become a structured summary or tag result that can later feed Work Graph and Daily Brief.

What changed:

- Added `src/ego_data_core/twin/enhance.py`.
- Added `EnhancementService.create_enhancement_job(...)` for summary/tag jobs.
- Added `EnhancementService.handle_job(...)` and `run_enhancement(...)` for Night Shift worker execution.
- Added `register_enhancement_handlers(...)` so a `NightShiftWorker` can execute enhancement jobs.
- Added `POST /api/v1/twin/enhance` to create enhancement jobs.
- Added `GET /api/v1/twin/enhancements?evidence_id=...` to query generated enhancements.
- Enhancement execution reads `evidence_text_chunks`, calls `ModelRouter`, writes an `enhancements` row, and creates one or more `enhancement_evidence_links`.
- Enhancement metadata records `model_invocation_id`, `output_ref_uri`, `job_id`, and adapter id.
- Added `tests/twin/test_enhance_summary_tag.py`.

Validation:

- `.venv\Scripts\python -m pytest tests/twin/test_enhance_summary_tag.py` passed with 4 tests.
- `.venv\Scripts\python -m pytest` passed with 81 tests.

Issues handled:

- Model output remains model output, not Evidence. The Evidence link records what source material supported the Enhancement.
- API job creation and worker execution are separate on purpose. This preserves the async-first design and keeps long-running work out of request handling.
- Missing evidence fails clearly before any Enhancement row is created.

Next iteration:

- Start `EDC-014`: Project Discovery v0. This will use evidence, tags, summaries, and file context to propose project candidates.

### EDC-011 - Model Router Interface And RuleBasedAdapter

Status: completed.

Position in the project:

- This is the no-network intelligence layer. Ego can now produce deterministic summaries, tags, task candidates, and risk candidates without Ollama or cloud APIs.
- It gives the upcoming enhancement pipeline a stable model interface while keeping v0.1 runnable on a clean local machine.
- It also starts recording model-like work in `model_invocations`, which is needed for traceability and later compute/model routing.

What changed:

- Added `src/ego_data_core/model_router/router.py`.
- Added `ModelRouter.run(...)` as the service entry point.
- Added `RuleBasedAdapter` with support for `summary`, `tag`, `task_candidate`, and `risk_candidate`.
- Added structured inputs through `ModelInputRef` and structured results through `ModelRunResult`.
- Wrote model outputs to `vault://model_outputs/{invocation_id}.json`.
- Wrote every run to `model_invocations` with purpose, input ref, output ref, prompt hash, token estimates, latency, privacy level, external-call flag, status, and metadata.
- Added a local rule model/provider record for the built-in adapter.
- Wrote `model_invoked` audit events for successful, failed, and blocked runs.
- Blocked external adapters from reading `sensitive` or `critical` input by default, writing both a blocked `model_invocations` row and a `policy_blocked` audit event.
- Added `tests/model_router/test_rule_based.py`.

Validation:

- `.venv\Scripts\python -m pytest tests/model_router/test_rule_based.py` passed with 5 tests.
- `.venv\Scripts\python -m pytest` passed with 77 tests.

Issues handled:

- Model-generated output is not written as Evidence. It is stored under `vault://model_outputs` and referenced from `model_invocations`.
- Audit and invocation metadata avoid storing full input text; the raw text stays in extracted text/chunks, while invocation metadata stores refs and hashes.
- External model policy is intentionally minimal here. `EDC-020` will expand it into the full Safety Kernel.

Next iteration:

- Start `EDC-013`: Enhancement Pipeline for summary/tag. This will connect evidence text chunks, Night Shift jobs, Model Router, and the `enhancements` tables into the first end-to-end "Ego read this and produced a traceable insight" flow.

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

## Historical v0.1 Execution Order

This sequence records the original Data Core plan. It no longer authorizes
`EDC-024`; current work is governed by the parent program status.

```text
EDC-000 -> EDC-001 -> EDC-002 -> EDC-003 -> EDC-029 -> EDC-028
  -> EDC-004 -> EDC-005 -> EDC-006 -> EDC-007
  -> EDC-008 -> EDC-010 -> EDC-011 -> EDC-013
  -> EDC-014/EDC-015 minimal -> EDC-017 -> EDC-018 -> EDC-025 -> EDC-026
  -> EDC-027 -> EDC-020 -> EDC-009 -> EDC-019 -> EDC-016 -> EDC-021
  -> EDC-030 -> EDC-022 -> EDC-023 -> EDC-024
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
