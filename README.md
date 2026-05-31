# Ego Data Core

Ego Data Core v0.1 is a local-first, evidence-first personal data core.

The current development build can scan a local folder, store evidence in the
vault, parse document text, generate rule-based enhancements, discover work
graph items, and export an evidence-backed Daily Brief as Markdown.

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
Daily Brief `markdown_path`.

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
