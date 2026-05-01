from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cadri_cli.config import AppConfig, configured_key_name, set_configured_key_name


def configured_key_name_from_path(path: Path) -> str | None:
    with patch.dict(os.environ, {"CADRI_USER_CONFIG": str(path)}, clear=True):
        return configured_key_name()


def isolated_user_config():
    temp_dir = tempfile.TemporaryDirectory()
    user_config = Path(temp_dir.name) / "missing.yaml"
    env = patch.dict(os.environ, {"CADRI_USER_CONFIG": str(user_config)}, clear=True)

    class IsolatedUserConfig:
        def __enter__(self) -> None:
            temp_dir.__enter__()
            env.__enter__()

        def __exit__(self, *args: object) -> None:
            env.__exit__(*args)
            temp_dir.__exit__(*args)

    return IsolatedUserConfig()


class ConfigTest(unittest.TestCase):
    def test_section_merges_instance_and_section_defaults(self) -> None:
        config = AppConfig(
            raw={
                "defaults": {
                    "instance": {
                        "instance_type": "c5a.16xlarge",
                        "tags": {"Project": "cadri"},
                    },
                    "empty_instance": {
                        "volume_size_gb": 100,
                        "tags": {"Role": "general-purpose"},
                    },
                },
                "empty_instance": {
                    "ami_id": "ami-0123456789abcdef0",
                    "tags": {"Generator": "doppeltest"},
                },
            }
        )

        with isolated_user_config():
            self.assertEqual(
                config.section("empty_instance"),
                {
                    "instance_type": "c5a.16xlarge",
                    "volume_size_gb": 100,
                    "ami_id": "ami-0123456789abcdef0",
                    "tags": {
                        "Project": "cadri",
                        "Role": "general-purpose",
                        "Generator": "doppeltest",
                    },
                },
            )

    def test_cadri_key_name_fills_missing_machine_key(self) -> None:
        config = AppConfig(raw={"empty_instance": {"ami_id": "ami-test"}})

        with patch.dict(os.environ, {"CADRI_KEY_NAME": "workstation-key"}, clear=False):
            self.assertEqual(
                config.section("empty_instance")["key_name"],
                "workstation-key",
            )

    def test_config_key_name_overrides_machine_key(self) -> None:
        config = AppConfig(
            raw={"empty_instance": {"ami_id": "ami-test", "key_name": "config-key"}}
        )

        with patch.dict(os.environ, {"CADRI_KEY_NAME": "workstation-key"}, clear=False):
            self.assertEqual(config.section("empty_instance")["key_name"], "config-key")

    def test_configured_key_name_fills_missing_machine_key(self) -> None:
        config = AppConfig(raw={"empty_instance": {"ami_id": "ami-test"}})

        with tempfile.TemporaryDirectory() as temp_dir:
            user_config = Path(temp_dir) / "config.yaml"
            set_configured_key_name("configured-key", user_config)
            with patch.dict(
                os.environ,
                {"CADRI_USER_CONFIG": str(user_config)},
                clear=True,
            ):
                self.assertEqual(
                    config.section("empty_instance")["key_name"],
                    "configured-key",
                )

    def test_environment_key_name_overrides_configured_key_name(self) -> None:
        config = AppConfig(raw={"empty_instance": {"ami_id": "ami-test"}})

        with tempfile.TemporaryDirectory() as temp_dir:
            user_config = Path(temp_dir) / "config.yaml"
            set_configured_key_name("configured-key", user_config)
            with patch.dict(
                os.environ,
                {
                    "CADRI_USER_CONFIG": str(user_config),
                    "CADRI_KEY_NAME": "env-key",
                },
                clear=True,
            ):
                self.assertEqual(config.section("empty_instance")["key_name"], "env-key")

    def test_set_configured_key_name_writes_user_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            user_config = Path(temp_dir) / "config.yaml"

            self.assertEqual(
                set_configured_key_name("configured-key", user_config),
                user_config,
            )
            self.assertEqual(configured_key_name_from_path(user_config), "configured-key")

    def test_instance_section_can_be_supplied_by_defaults(self) -> None:
        config = AppConfig(
            raw={
                "defaults": {
                    "instance": {"subnet_id": "subnet-test"},
                    "empty_instance": {"ami_id": "ami-test"},
                }
            }
        )

        with isolated_user_config():
            self.assertEqual(
                config.section("empty_instance"),
                {"subnet_id": "subnet-test", "ami_id": "ami-test"},
            )

    def test_generic_instance_defaults_do_not_create_missing_section(self) -> None:
        config = AppConfig(raw={"defaults": {"instance": {"subnet_id": "subnet-test"}}})

        with self.assertRaisesRegex(ValueError, "Missing required config section"):
            config.section("empty_instance")


if __name__ == "__main__":
    unittest.main()
