# Data Core migration verification

Date: 2026-10-27. Scope: the current imported software, not historical versions,
EgoLink hardware, or a completed EgoLink-to-EgoBase product.

The imported runtime source, scripts, and tests come from original Ego commit
`070ca1ea75cb43967286c3b86e9ac924584eb93d`. This migration adds licensing and
navigation/documentation; it does not change those runtime files.

## Environment and checks

Windows, Python 3.12.14, a fresh virtual environment, and the dependencies
declared by `pyproject.toml` were used. Tests used isolated temporary data.

| Check | Result |
|---|---|
| Editable install with development dependencies | Passed |
| Existing pytest suite | **135 passed**, 1 warning, 71.69 seconds |
| Existing `scripts/run_demo.py` with bundled sample workspace | Passed: 5 files scanned and parsed, 5 evidence records, 0 parse failures, brief created |
| Demo action sequence | Blocked before authorization, then completed as a dry-run after authorization |

The warning is a third-party Starlette TestClient deprecation concerning HTTPX;
it did not fail a test. Direct dependency versions inspected were FastAPI
0.162.0, pypdf 6.21.2, python-docx 1.2.0, Uvicorn 0.54.0, HTTPX 0.28.1, and
pytest 8.4.2. These observations are not a dependency lock or a promise that all
future versions permitted by the existing version ranges will work.

Commands, run from the Data Core directory after environment activation:

```sh
python -m pip install -e ".[dev]"
python -m pytest -vv --maxfail=1 --basetemp <isolated-test-directory>
python scripts/run_demo.py --data-home <isolated-demo-directory>
```

An initial sandboxed test attempt produced no progress and was stopped. The
completed run above used the same migration copy and virtual environment with
normal local process access; no application change was needed.

These checks cover the existing local software behavior, including API, storage,
policies, parsing, brief generation, and action dry-runs. They do not establish
external action execution, long-term household use, hardware behavior, or the
full cross-device product loop. Older milestone commits were not individually
retested; their original dated development records remain in Git.
