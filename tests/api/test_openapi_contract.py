from pathlib import Path
import re

from fastapi.testclient import TestClient


DRAFT_PATH = Path("docs/ego_data_core_v0_1_openapi.yaml")
CONTRACT_DOC_PATH = Path("docs/api_contract.md")

CORE_OPERATIONS = {
    ("get", "/api/v1/health"),
    ("get", "/api/v1/sources"),
    ("post", "/api/v1/sources"),
    ("get", "/api/v1/search"),
    ("post", "/api/v1/twin/enhance"),
    ("get", "/api/v1/twin/enhancements"),
    ("post", "/api/v1/briefs/generate"),
    ("get", "/api/v1/briefs/daily/latest"),
    ("post", "/api/v1/actions/propose"),
    ("post", "/api/v1/actions/{action_id}/authorize"),
    ("post", "/api/v1/actions/{action_id}/execute"),
    ("get", "/api/v1/audit/logs"),
}

IMPLEMENTED_V0_1_EXTENSIONS = {
    ("post", "/api/v1/screen/import"),
    ("post", "/api/v1/twin/screens/ocr"),
    ("post", "/api/v1/projects/discover"),
    ("get", "/api/v1/projects"),
    ("post", "/api/v1/projects/{project_id}/feedback"),
    ("post", "/api/v1/workgraph/extract"),
    ("get", "/api/v1/workgraph/items"),
    ("post", "/api/v1/workgraph/items/{item_type}/{item_id}/feedback"),
    ("post", "/api/v1/workgraph/automations/discover"),
    ("get", "/api/v1/workgraph/automations"),
}

DRAFT_ONLY_PATHS = {
    "/vault/ingest",
    "/vault/evidence/{evidence_id}",
    "/projects/{project_id}",
    "/model-router/run",
}


def test_openapi_json_is_available(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["openapi"].startswith("3.")
    assert payload["info"]["title"] == "Ego Data Core Local API"
    assert payload["info"]["version"] == "0.1.0"


def test_core_paths_match_v0_1_implemented_contract(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    operations = _implemented_operations(spec)

    missing = sorted(CORE_OPERATIONS - operations)
    assert missing == []

    extension_missing = sorted(IMPLEMENTED_V0_1_EXTENSIONS - operations)
    assert extension_missing == []


def test_contract_covers_draft_core_paths_and_documents_differences(
    client: TestClient,
) -> None:
    draft_operations = _draft_operations(DRAFT_PATH.read_text(encoding="utf-8"))
    contract_doc = CONTRACT_DOC_PATH.read_text(encoding="utf-8")

    for method, path in {
        ("get", "/health"),
        ("get", "/sources"),
        ("post", "/sources"),
        ("post", "/twin/enhance"),
        ("get", "/twin/enhancements"),
        ("post", "/briefs/generate"),
        ("get", "/briefs/daily/latest"),
        ("post", "/actions/propose"),
        ("post", "/actions/{action_id}/authorize"),
        ("post", "/actions/{action_id}/execute"),
        ("get", "/audit/logs"),
    }:
        assert (method, path) in draft_operations

    for path in DRAFT_ONLY_PATHS:
        assert path in contract_doc

    assert "/api/v1/search" in contract_doc
    assert "/api/v1/workgraph/automations" in contract_doc


def test_key_request_schemas_remain_stable(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    schemas = spec["components"]["schemas"]

    source_schema = schemas["CreateSourceRequest"]
    assert set(source_schema["required"]) == {"source_type", "name", "root_uri"}
    assert source_schema["properties"]["source_type"]["enum"] == [
        "filesystem",
        "screen",
        "browser",
        "operator",
        "sensor",
        "manual",
    ]
    assert source_schema["properties"]["privacy_level"]["default"] == "private"

    enhance_schema = schemas["CreateEnhancementJobRequest"]
    assert set(enhance_schema["required"]) == {"evidence_ids", "enhancement_type"}
    assert "strategy" in enhance_schema["properties"]

    screenshot_schema = schemas["ImportScreenshotRequest"]
    assert set(screenshot_schema["required"]) == {"source_id", "image_path"}
    assert "active_window" in screenshot_schema["properties"]
    assert "app_name" in screenshot_schema["properties"]
    assert "metadata" in screenshot_schema["properties"]

    screenshot_ocr_schema = schemas["RunScreenshotOCRRequest"]
    assert set(screenshot_ocr_schema["required"]) == {"evidence_ids"}
    assert screenshot_ocr_schema["properties"]["adapter"]["default"] == "unsupported"
    assert "mock_text" in screenshot_ocr_schema["properties"]

    brief_schema = schemas["GenerateBriefRequest"]
    assert "report_type" in brief_schema["properties"]
    assert "report_date" in brief_schema["properties"]
    assert "force_regenerate" in brief_schema["properties"]

    action_schema = schemas["ProposeActionRequest"]
    assert action_schema["required"] == ["automation_id"]
    assert "authorization_type" in schemas["AuthorizeActionRequest"]["properties"]
    assert schemas["ExecuteActionRequest"]["properties"]["dry_run"]["default"] is True


def _implemented_operations(spec: dict) -> set[tuple[str, str]]:
    return {
        (method.lower(), path)
        for path, operations in spec["paths"].items()
        for method in operations
    }


def _draft_operations(text: str) -> set[tuple[str, str]]:
    operations: set[tuple[str, str]] = set()
    current_path: str | None = None
    in_paths = False
    for line in text.splitlines():
        if line == "paths:":
            in_paths = True
            continue
        if line == "components:":
            break
        if not in_paths:
            continue
        path_match = re.match(r"^  (/[^:]+):", line)
        if path_match:
            current_path = path_match.group(1)
            continue
        method_match = re.match(r"^    (get|post|put|patch|delete):", line)
        if method_match and current_path:
            operations.add((method_match.group(1), current_path))
    return operations
