"""Safe local storage for vault:// URIs."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
from typing import Any
from urllib.parse import quote, unquote, urlparse

from ego_data_core.kernel.config import EgoSettings, load_settings


SUPPORTED_VAULT_COLLECTIONS = frozenset(
    {
        "objects",
        "versions",
        "evidence",
        "extracted_text",
        "model_outputs",
        "briefs",
    }
)


class InvalidVaultUriError(ValueError):
    """Raised when a vault:// URI is malformed or unsafe."""


class VaultStorage:
    def __init__(self, settings: EgoSettings | None = None) -> None:
        self.settings = settings or load_settings()

    def resolve_uri(self, uri: str) -> Path:
        collection, relative_path = _parse_vault_uri(uri)
        base_dir = self._collection_dir(collection)
        target_path = (base_dir / relative_path).resolve()
        _ensure_within_base(target_path, base_dir)
        return target_path

    def safe_write_text(self, uri: str, text: str, *, encoding: str = "utf-8") -> str:
        target_path = self.resolve_uri(uri)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(text, encoding=encoding)
        return uri

    def safe_write_json(self, uri: str, payload: Any) -> str:
        text = json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2)
        return self.safe_write_text(uri, text)

    def safe_copy_file(self, source_path: str | Path, destination_uri: str) -> str:
        source = Path(source_path).expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(f"Source file does not exist: {source}")
        target_path = self.resolve_uri(destination_uri)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target_path)
        return destination_uri

    def read_text(self, uri: str, *, encoding: str = "utf-8") -> str:
        return self.resolve_uri(uri).read_text(encoding=encoding)

    def _collection_dir(self, collection: str) -> Path:
        paths = self.settings.paths
        mapping = {
            "objects": paths.objects_dir,
            "versions": paths.versions_dir,
            "evidence": paths.evidence_dir,
            "extracted_text": paths.extracted_text_dir,
            "model_outputs": paths.model_outputs_dir,
            "briefs": paths.briefs_dir,
        }
        return mapping[collection].resolve()


def build_vault_uri(collection: str, filename: str | Path) -> str:
    normalized_collection = _normalize_collection(collection)
    safe_name = _validate_plain_filename(str(filename))
    encoded_name = quote(safe_name, safe="")
    return f"vault://{normalized_collection}/{encoded_name}"


def _parse_vault_uri(uri: str) -> tuple[str, Path]:
    parsed = urlparse(uri)
    if parsed.scheme != "vault":
        raise InvalidVaultUriError(f"Vault URI must start with vault://: {uri}")
    collection = _normalize_collection(parsed.netloc)
    if parsed.params or parsed.query or parsed.fragment:
        raise InvalidVaultUriError("Vault URI must not include params, query, or fragment")
    raw_path = unquote(parsed.path.lstrip("/"))
    path_parts = _validate_uri_path(raw_path)
    relative_path = Path(*path_parts)
    return collection, relative_path


def _normalize_collection(collection: str) -> str:
    normalized = collection.strip().lower()
    if normalized not in SUPPORTED_VAULT_COLLECTIONS:
        allowed = ", ".join(sorted(SUPPORTED_VAULT_COLLECTIONS))
        raise InvalidVaultUriError(
            f"Unsupported vault collection '{collection}'. Allowed: {allowed}"
        )
    return normalized


def _validate_plain_filename(filename: str) -> str:
    if not filename or filename.strip() == "":
        raise InvalidVaultUriError("Vault filename must be a plain file name")
    if any(separator in filename for separator in ("/", "\\")):
        raise InvalidVaultUriError("Vault filename must not contain path separators")
    if ":" in filename:
        raise InvalidVaultUriError("Vault filename must not contain drive separators")
    if filename in {".", ".."}:
        raise InvalidVaultUriError("Vault filename must be a plain file name")
    return filename


def _validate_uri_path(raw_path: str) -> tuple[str, ...]:
    if not raw_path:
        raise InvalidVaultUriError("Vault URI must include a relative path")
    if raw_path.startswith(("/", "\\")):
        raise InvalidVaultUriError("Vault URI path must be relative")
    if "\\" in raw_path:
        raise InvalidVaultUriError("Vault URI path must use forward slashes")
    path_parts = tuple(raw_path.split("/"))
    if any(part in {"", ".", ".."} for part in path_parts):
        raise InvalidVaultUriError("Vault URI path must not contain traversal segments")
    if any(":" in part for part in path_parts):
        raise InvalidVaultUriError("Vault URI path must not contain drive separators")
    return path_parts


def _ensure_within_base(target_path: Path, base_dir: Path) -> None:
    try:
        target_path.relative_to(base_dir)
    except ValueError as exc:
        raise InvalidVaultUriError("Vault URI resolves outside its collection") from exc
