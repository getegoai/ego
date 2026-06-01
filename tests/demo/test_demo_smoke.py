import json
from pathlib import Path
import subprocess
import sys

from ego_data_core.kernel.time import local_today


def test_demo_script_generates_evidence_backed_brief(tmp_path: Path) -> None:
    data_home = tmp_path / "ego_demo_home"
    target_date = local_today()

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_demo.py",
            "--data-home",
            str(data_home),
            "--date",
            target_date,
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    markdown_path = Path(payload["markdown_path"])
    assert markdown_path.exists()
    markdown = markdown_path.read_text(encoding="utf-8")

    assert payload["markdown_uri"].startswith("vault://briefs/")
    assert payload["scan"]["created_count"] >= 4
    assert payload["scan"]["parsed_count"] >= 4
    assert payload["enhance"]["job"]["status"] == "succeeded"
    assert payload["audit_total"] >= 1
    assert "Ego Project Plan" in markdown
    assert "Evidence: [ev_" in markdown
    assert "Evidence: none" not in markdown
    assert str(Path("demo/sample_workspace").resolve()) not in markdown
