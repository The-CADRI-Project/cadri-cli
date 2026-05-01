from __future__ import annotations

from dataclasses import dataclass
import os
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
        defaults = self.raw.get("defaults", {})
        if defaults is None:
            defaults = {}
        if not isinstance(defaults, dict):
            raise ValueError("Config defaults must be a YAML mapping")

        value = self.raw.get(name, {})
        if value is None:
            value = {}
        if not isinstance(value, dict):
            raise ValueError(f"Config section {name} must be a YAML mapping")

        section_defaults = defaults.get(name, {})
        if section_defaults is None:
            section_defaults = {}
        if not isinstance(section_defaults, dict):
            raise ValueError(f"Config defaults.{name} must be a YAML mapping")

        has_section = name in self.raw
        has_section_defaults = name in defaults
        if not (has_section or has_section_defaults):
            raise ValueError(f"Missing required config section: {name}")

        instance_defaults = (
            defaults.get("instance", {})
            if section_name_uses_instance_defaults(name)
            else {}
        )
        merged = deep_merge(instance_defaults, section_defaults)
        merged = deep_merge(merged, value)
        apply_machine_defaults(name, merged)
        return merged


def deep_merge(*values: Any) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for value in values:
        if value is None:
            continue
        if not isinstance(value, dict):
            raise ValueError("Config defaults must be YAML mappings")
        for key, item in value.items():
            if isinstance(item, dict) and isinstance(merged.get(key), dict):
                merged[key] = deep_merge(merged[key], item)
            else:
                merged[key] = item
    return merged


def apply_machine_defaults(section_name: str, section: dict[str, Any]) -> None:
    if not section_name_uses_instance_defaults(section_name):
        return
    if section.get("key_name"):
        return

    key_name = os.getenv("CADRI_KEY_NAME") or configured_key_name()
    if key_name:
        section["key_name"] = key_name


def section_name_uses_instance_defaults(section_name: str) -> bool:
    return section_name in {"empty_instance", "launch", "image"}


def user_config_path() -> Path:
    override = os.getenv("CADRI_USER_CONFIG")
    if override:
        return Path(override).expanduser()

    config_home = os.getenv("XDG_CONFIG_HOME")
    if config_home:
        return Path(config_home).expanduser() / "cadri" / "config.yaml"
    return Path.home() / ".config" / "cadri" / "config.yaml"


def load_user_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path).expanduser() if path else user_config_path()
    if not config_path.exists():
        return {}

    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if not isinstance(data, dict):
        raise ValueError(f"User config file must contain a YAML mapping: {config_path}")
    return data


def configured_key_name() -> str | None:
    key_name = load_user_config().get("key_name")
    if isinstance(key_name, str) and key_name:
        return key_name
    return None


def set_configured_key_name(key_name: str, path: str | Path | None = None) -> Path:
    if not key_name:
        raise ValueError("key_name must not be empty")

    config_path = Path(path).expanduser() if path else user_config_path()
    data = load_user_config(config_path)
    data["key_name"] = key_name

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=True)
    return config_path


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
