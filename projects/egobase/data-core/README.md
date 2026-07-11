# Ego Data Core

> Workspace role: this directory is the current software-runtime prototype under
> `projects/egobase`. Ego Data Core is a reusable evidence and agent substrate;
> it is not, by itself, the complete EgoBase product or hardware definition.

Ego Data Core v0.1 is a local-first, evidence-first personal data core.

The current development build can scan a local folder, store evidence in the
vault, import manual screenshot evidence, generate screenshot OCR enhancements,
parse document text, generate rule-based enhancements, discover work graph
items, and export an evidence-backed Daily Brief as Markdown.

## Requirements

- Python 3.11 or newer
- pip

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Run The Local API

The API remains the v0.1 local API. FastAPI exposes the generated contract at
`/openapi.json`, and `docs/api_contract.md` records differences from the draft
OpenAPI file.

```powershell
python -m ego_data_core.main
```

Or:

```powershell
uvicorn ego_data_core.api.app:app --host 127.0.0.1 --port 8765
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/api/v1/health
```

## Run The Local Web UI

Start the local API, then open:

```powershell
http://127.0.0.1:8765
```

The UI shows the local API status, source authorization status, evidence search,
latest Daily Brief, and audit log. It uses only local `/api/v1/*` endpoints.

## Run A CLI Loop

```powershell
ego init-db
ego source add "C:\path\to\your\folder" --name "My Documents"
ego scan src_xxxxxxxxxxxxxxxxxxxxxxxxxx
ego enhance --date 2026-05-31 --type tag
ego brief daily --date 2026-05-31 --force
ego audit tail --event-type brief_generated
```

`source add` prints the generated `source_id`; pass that value to `ego scan`.
`brief daily` prints `metadata.markdown_uri`, which points to the exported
Markdown file under the local `vault/briefs` directory.

## Import Screenshot Evidence

Create a screen source through the local API:

```powershell
$source = Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8765/api/v1/sources `
  -ContentType "application/json" `
  -Body '{"source_type":"screen","name":"Manual Screenshots","root_uri":"screen://manual"}'
```

Then import an existing image as screenshot evidence:

```powershell
ego screen import "C:\path\to\screenshot.png" `
  --source-id $source.source_id `
  --active-window "Example Window" `
  --app-name "Example App"
```

The command prints `raw_object_id`, `version_id`, and `evidence_id`. The image is
copied into the local vault; the CLI/API response does not return the original
absolute image path.

Generate OCR-related enhancements from the screenshot evidence:

```powershell
ego screen ocr ev_xxxxxxxxxxxxxxxxxxxxxxxxxx
```

Without a configured OCR engine, the command writes an explicit `unsupported`
OCR enhancement instead of failing the workflow. For local demos and tests, use
the mock adapter:

```powershell
ego screen ocr ev_xxxxxxxxxxxxxxxxxxxxxxxxxx `
  --adapter mock `
  --mock-text "Visible text from the screenshot"
```

You can also run the CLI module directly:

```powershell
python -m ego_data_core.cli brief daily --date 2026-05-31
```

The database and vault are stored under `EGO_DATA_HOME` when set, or under
`~/.ego_data_core` by default.

## Run The Demo

```powershell
python scripts/run_demo.py
```

The demo uses synthetic files in `demo/sample_workspace` and prints the generated
Daily Brief `markdown_path`. It also runs the minimum closed loop: scan, parse,
enhance, discover automation opportunities, create an Operator Bridge action
plan, block execution before authorization, authorize, and complete a dry-run.

Supported profiles:

```powershell
$env:EGO_PROFILE = "dev"   # dev, test, or prod
```

## Run Tests

```powershell
pytest
```

## Safety Boundary

Filesystem ingestion is read-only. Ego copies scanned file versions into its
local vault and does not modify, move, rename, delete, upload, or transmit user
files.
