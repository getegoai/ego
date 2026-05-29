"""Local configuration and directory layout."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Final


SUPPORTED_PROFILES: Final[frozenset[str]] = frozenset({"dev", "test", "prod"})
DEFAULT_PROFILE: Final[str] = "dev"
DATA_HOME_ENV: Final[str] = "EGO_DATA_HOME"
PROFILE_ENV: Final[str] = "EGO_PROFILE"


class InvalidProfileError(ValueError):
    """Raised when EGO_PROFILE is not one of dev/test/prod."""


@dataclass(frozen=True)
class EgoPaths:
    data_home: Path
    config_dir: Path
    db_dir: Path
    database_path: Path
    vault_dir: Path
    objects_dir: Path
    versions_dir: Path
    evidence_dir: Path
    extracted_text_dir: Path
    model_outputs_dir: Path
    briefs_dir: Path
    logs_dir: Path
    tmp_dir: Path

    def required_dirs(self) -> tuple[Path, ...]:
        return (
            self.data_home,
            self.config_dir,
            self.db_dir,
            self.vault_dir,
            self.objects_dir,
            self.versions_dir,
            self.evidence_dir,
            self.extracted_text_dir,
            self.model_outputs_dir,
            self.briefs_dir,
            self.logs_dir,
            self.tmp_dir,
        )


@dataclass(frozen=True)
class EgoSettings:
    profile: str
    paths: EgoPaths
    model_config_path: Path
    privacy_policy_path: Path


def load_settings(
    *,
    profile: str | None = None,
    data_home: str | os.PathLike[str] | None = None,
    create_dirs: bool = True,
) -> EgoSettings:
    active_profile = _resolve_profile(profile)
    root = _resolve_data_home(data_home)
    paths = _build_paths(root)
    settings = EgoSettings(
        profile=active_profile,
        paths=paths,
        model_config_path=paths.config_dir / f"models.{active_profile}.json",
        privacy_policy_path=paths.config_dir / f"policies.{active_profile}.json",
    )
    if create_dirs:
        ensure_directories(settings)
    return settings


def ensure_directories(settings: EgoSettings) -> None:
    for directory in settings.paths.required_dirs():
        directory.mkdir(parents=True, exist_ok=True)


def _resolve_profile(profile: str | None) -> str:
    raw_profile = profile if profile is not None else os.getenv(PROFILE_ENV, DEFAULT_PROFILE)
    normalized = raw_profile.strip().lower()
    if normalized not in SUPPORTED_PROFILES:
        allowed = ", ".join(sorted(SUPPORTED_PROFILES))
        raise InvalidProfileError(
            f"Unsupported Ego profile '{raw_profile}'. Allowed profiles: {allowed}"
        )
    return normalized


def _resolve_data_home(data_home: str | os.PathLike[str] | None) -> Path:
    raw_home = data_home if data_home is not None else os.getenv(DATA_HOME_ENV)
    if raw_home:
        return Path(raw_home).expanduser().resolve()
    return (Path.home() / ".ego_data_core").resolve()


def _build_paths(data_home: Path) -> EgoPaths:
    vault_dir = data_home / "vault"
    return EgoPaths(
        data_home=data_home,
        config_dir=data_home / "config",
        db_dir=data_home / "db",
        database_path=data_home / "db" / "ego_data_core.sqlite",
        vault_dir=vault_dir,
        objects_dir=vault_dir / "objects",
        versions_dir=vault_dir / "versions",
        evidence_dir=vault_dir / "evidence",
        extracted_text_dir=vault_dir / "extracted_text",
        model_outputs_dir=vault_dir / "model_outputs",
        briefs_dir=vault_dir / "briefs",
        logs_dir=data_home / "logs",
        tmp_dir=data_home / "tmp",
    )
