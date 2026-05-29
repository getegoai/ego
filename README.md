# Ego Data Core

Ego Data Core v0.1 is a local-first, evidence-first personal data core.

This repository is currently in `EDC-000`: project foundation. The implemented surface is intentionally small: a FastAPI application skeleton and a health endpoint. Database migrations, vault ingest, source scanning, model routing, and brief generation are later EDC issues.

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

## Initialize The Database

```powershell
python scripts/init_db.py
```

The command creates or updates the local SQLite database under `EGO_DATA_HOME`
when set, or under `~/.ego_data_core` by default.

Supported profiles:

```powershell
$env:EGO_PROFILE = "dev"   # dev, test, or prod
```

## Run Tests

```powershell
pytest tests/test_health.py
```

## Safety Boundary

The current code does not scan, modify, move, rename, delete, upload, or transmit user files. All user-data ingestion and vault behavior starts in later issues and must remain non-destructive by default.
