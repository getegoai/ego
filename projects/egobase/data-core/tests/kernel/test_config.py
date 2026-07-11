from pathlib import Path

import pytest

from ego_data_core.kernel.config import (
    InvalidProfileError,
    SUPPORTED_PROFILES,
    load_settings,
)


def test_default_data_home_uses_user_home_without_creating_dirs(monkeypatch) -> None:
    monkeypatch.delenv("EGO_DATA_HOME", raising=False)
    monkeypatch.delenv("EGO_PROFILE", raising=False)

    settings = load_settings(create_dirs=False)

    assert settings.profile == "dev"
    assert settings.paths.data_home == (Path.home() / ".ego_data_core").resolve()


def test_env_data_home_override_creates_required_directories(tmp_path, monkeypatch) -> None:
    data_home = tmp_path / "ego_home"
    monkeypatch.setenv("EGO_DATA_HOME", str(data_home))
    monkeypatch.setenv("EGO_PROFILE", "test")

    settings = load_settings()

    assert settings.profile == "test"
    assert settings.paths.data_home == data_home.resolve()
    assert settings.paths.database_path == data_home.resolve() / "db" / "ego_data_core.sqlite"
    for directory in settings.paths.required_dirs():
        assert directory.exists()
        assert directory.is_dir()


def test_vault_and_runtime_directories_have_stable_names(tmp_path) -> None:
    settings = load_settings(data_home=tmp_path / "ego_home", profile="dev")
    paths = settings.paths

    assert paths.vault_dir.name == "vault"
    assert paths.objects_dir == paths.vault_dir / "objects"
    assert paths.versions_dir == paths.vault_dir / "versions"
    assert paths.evidence_dir == paths.vault_dir / "evidence"
    assert paths.extracted_text_dir == paths.vault_dir / "extracted_text"
    assert paths.model_outputs_dir == paths.vault_dir / "model_outputs"
    assert paths.briefs_dir == paths.vault_dir / "briefs"
    assert paths.logs_dir == paths.data_home / "logs"
    assert paths.tmp_dir == paths.data_home / "tmp"


def test_profiles_are_limited_to_dev_test_prod(tmp_path) -> None:
    assert SUPPORTED_PROFILES == {"dev", "test", "prod"}

    for profile in SUPPORTED_PROFILES:
        settings = load_settings(
            data_home=tmp_path / profile,
            profile=profile.upper(),
            create_dirs=False,
        )
        assert settings.profile == profile


def test_invalid_profile_raises_clear_error(tmp_path) -> None:
    with pytest.raises(InvalidProfileError, match="Unsupported Ego profile"):
        load_settings(data_home=tmp_path / "ego_home", profile="staging")


def test_model_and_policy_config_paths_are_profile_specific(tmp_path) -> None:
    settings = load_settings(data_home=tmp_path / "ego_home", profile="prod")

    assert settings.model_config_path == settings.paths.config_dir / "models.prod.json"
    assert settings.privacy_policy_path == settings.paths.config_dir / "policies.prod.json"
