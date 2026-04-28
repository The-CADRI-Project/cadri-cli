from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml


@dataclass(frozen=True)
class AwsConfig:
    region: str
    profile: str | None = None


@dataclass(frozen=True)
class AppConfig:
    raw: dict[str, Any]

    @property
    def aws(self) -> AwsConfig:
        data = self.raw.get("aws", {})
        return AwsConfig(
            region=data.get("region", "us-west-2"),
            profile=data.get("profile"),
        )

    def section(self, name: str) -> dict[str, Any]:
        value = self.raw.get(name)
        if not isinstance(value, dict):
            raise ValueError(f"Missing required config section: {name}")
        return value


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a YAML mapping: {config_path}")

    return AppConfig(raw=data)


def require_values(section_name: str, section: dict[str, Any], keys: Iterable[str]) -> None:
    missing = [key for key in keys if section.get(key) in (None, "", [])]
    if missing:
        formatted = ", ".join(f"{section_name}.{key}" for key in missing)
        raise ValueError(f"Missing required config values: {formatted}")
