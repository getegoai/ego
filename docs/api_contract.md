# Ego Data Core API Contract

Last updated: 2026-06-08

This document tracks the v0.1 local API contract implemented by FastAPI and the
known differences from `docs/ego_data_core_v0_1_openapi.yaml`.

The authoritative generated contract is available at:

```text
GET /openapi.json
```

The v0.1 API is local-first and mounted under:

```text
http://127.0.0.1:8765/api/v1
```

## Implemented Core Paths

These paths are covered by `tests/api/test_openapi_contract.py`:

| Area | Method | Path |
|---|---:|---|
| Health | GET | `/api/v1/health` |
| Sources | GET | `/api/v1/sources` |
| Sources | POST | `/api/v1/sources` |
| Vault/Search | GET | `/api/v1/search` |
| Twin | POST | `/api/v1/twin/enhance` |
| Twin | GET | `/api/v1/twin/enhancements` |
| Brief | POST | `/api/v1/briefs/generate` |
| Brief | GET | `/api/v1/briefs/daily/latest` |
| Actions | POST | `/api/v1/actions/propose` |
| Actions | POST | `/api/v1/actions/{action_id}/authorize` |
| Actions | POST | `/api/v1/actions/{action_id}/execute` |
| Audit | GET | `/api/v1/audit/logs` |

## Implemented v0.1 Extensions

These routes are part of the current implementation and are also contract-tested:

| Area | Method | Path |
|---|---:|---|
| Screen | POST | `/api/v1/screen/import` |
| Twin | POST | `/api/v1/twin/screens/ocr` |
| Projects | POST | `/api/v1/projects/discover` |
| Projects | GET | `/api/v1/projects` |
| Projects | POST | `/api/v1/projects/{project_id}/feedback` |
| Work Graph | POST | `/api/v1/workgraph/extract` |
| Work Graph | GET | `/api/v1/workgraph/items` |
| Work Graph | POST | `/api/v1/workgraph/items/{item_type}/{item_id}/feedback` |
| Automation | POST | `/api/v1/workgraph/automations/discover` |
| Automation | GET | `/api/v1/workgraph/automations` |

## Differences From Draft

The draft contains several endpoints that are intentionally not exposed in the
current v0.1 implementation:

| Draft Path | Current Status | Reason |
|---|---|---|
| `/vault/ingest` | Not implemented | Ingestion is currently driven through filesystem sources, scanner, parser, and CLI/demo services. Direct Vault ingest remains reserved for a later API pass. |
| `/vault/evidence/{evidence_id}` | Not implemented | Evidence is exposed through `/api/v1/search` and Daily Brief references. A dedicated evidence detail API is still future work. |
| `/projects/{project_id}` | Not implemented | v0.1 supports project discovery, listing, and feedback. Single-project detail can be added once UI needs it. |
| `/model-router/run` | Not implemented | Model Router is used internally by enhancement/workgraph services. Direct model execution is withheld from the public local API until policy controls are more complete. |

The implementation also adds routes that were not in the draft but are required
for the current closed loop:

- `/api/v1/search`
- `/api/v1/screen/import`
- `/api/v1/twin/screens/ocr`
- `/api/v1/workgraph/extract`
- `/api/v1/workgraph/items`
- `/api/v1/workgraph/automations`
- `/api/v1/actions/*`

## Stable Request Schemas

The contract test locks the key request schemas for:

- `CreateSourceRequest`
- `CreateEnhancementJobRequest`
- `GenerateBriefRequest`
- `ProposeActionRequest`
- `AuthorizeActionRequest`
- `ExecuteActionRequest`

Any future change to these schemas should be treated as a deliberate v0.1
contract change and reflected here.
