# Ego Data Core Demo Script

This demo uses only synthetic files in `demo/sample_workspace`.

## Run

```powershell
python scripts/run_demo.py
```

Or, from a shell with Bash:

```bash
bash scripts/run_demo.sh
```

The script prints JSON. The important fields are:

- `markdown_path`: local Markdown Daily Brief path.
- `markdown_uri`: vault URI for the same brief.
- `report_id`: generated report record.
- `audit_total`: number of matching `brief_generated` audit events.

## What It Shows

1. Initializes the local database.
2. Adds `demo/sample_workspace` as a filesystem source.
3. Scans files and copies versions into the local vault.
4. Parses document text into evidence chunks.
5. Runs a tag enhancement job through Night Shift.
6. Refreshes project discovery and work item extraction.
7. Generates an evidence-backed Daily Brief.
8. Prints the Markdown path so the operator can open the result.

## Expected Result

Open `markdown_path` after the script finishes. Each factual item should include
an `Evidence: [ev_...]` reference with a file title, relative path, timestamp,
and excerpt. The Markdown should not expose local absolute file paths.
