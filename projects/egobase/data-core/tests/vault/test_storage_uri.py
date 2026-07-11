from pathlib import Path

import pytest

from ego_data_core.kernel.config import load_settings
from ego_data_core.vault.storage import (
    InvalidVaultUriError,
    SUPPORTED_VAULT_COLLECTIONS,
    VaultStorage,
    build_vault_uri,
)


def test_resolve_uri_supports_all_required_collections(tmp_data_home: Path) -> None:
    storage = VaultStorage()

    for collection in SUPPORTED_VAULT_COLLECTIONS:
        uri = f"vault://{collection}/sample.txt"
        path = storage.resolve_uri(uri)

        assert path.is_relative_to(tmp_data_home / "vault")
        assert path.name == "sample.txt"


def test_safe_write_and_read_text() -> None:
    storage = VaultStorage()
    uri = "vault://extracted_text/note.txt"

    result_uri = storage.safe_write_text(uri, "hello vault")

    assert result_uri == uri
    assert storage.read_text(uri) == "hello vault"


def test_safe_write_json_uses_stable_json() -> None:
    storage = VaultStorage()
    uri = "vault://model_outputs/result.json"

    storage.safe_write_json(uri, {"b": 2, "a": 1})

    assert '"a": 1' in storage.read_text(uri)
    assert '"b": 2' in storage.read_text(uri)


def test_safe_copy_file_does_not_use_original_absolute_path(tmp_path: Path) -> None:
    source = tmp_path / "sensitive original name.txt"
    source.write_text("secret-ish test content", encoding="utf-8")
    storage = VaultStorage()
    destination_uri = build_vault_uri("versions", "ver_test.txt")

    result_uri = storage.safe_copy_file(source, destination_uri)
    copied_path = storage.resolve_uri(result_uri)

    assert result_uri == "vault://versions/ver_test.txt"
    assert copied_path.read_text(encoding="utf-8") == "secret-ish test content"
    assert str(tmp_path) not in result_uri
    assert source.name not in result_uri


@pytest.mark.parametrize(
    "uri",
    [
        "file://versions/file.txt",
        "vault://unknown/file.txt",
        "vault://versions/../escape.txt",
        "vault://versions/%2E%2E/escape.txt",
        "vault://versions/%5Cescape.txt",
        "vault://versions/C:/escape.txt",
        "vault://versions",
        "vault://versions/file.txt?x=1",
        "vault://versions/nested\\file.txt",
    ],
)
def test_rejects_malformed_or_unsafe_uris(uri: str) -> None:
    storage = VaultStorage()

    with pytest.raises(InvalidVaultUriError):
        storage.resolve_uri(uri)


def test_build_vault_uri_accepts_only_plain_filename() -> None:
    assert build_vault_uri("briefs", "brief.md") == "vault://briefs/brief.md"
    assert build_vault_uri("briefs", "note with space.md") == "vault://briefs/note%20with%20space.md"

    with pytest.raises(InvalidVaultUriError):
        build_vault_uri("briefs", "..")
    with pytest.raises(InvalidVaultUriError):
        build_vault_uri("briefs", r"C:\Users\name\brief.md")


def test_safe_copy_missing_file_raises(tmp_path: Path) -> None:
    storage = VaultStorage()

    with pytest.raises(FileNotFoundError):
        storage.safe_copy_file(tmp_path / "missing.txt", "vault://versions/missing.txt")


def test_explicit_settings_are_supported(tmp_path: Path) -> None:
    settings = load_settings(data_home=tmp_path / "explicit_home")
    storage = VaultStorage(settings=settings)

    path = storage.resolve_uri("vault://briefs/today.md")

    assert path == settings.paths.briefs_dir / "today.md"
