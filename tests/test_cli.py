from __future__ import annotations

import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cadri_cli.cli import main
from cadri_cli.config import configured_key_name, set_configured_key_name


class CliTest(unittest.TestCase):
    def test_configure_prompts_for_key_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            user_config = Path(temp_dir) / "config.yaml"
            stdout = io.StringIO()

            with (
                patch.dict(
                    os.environ,
                    {"CADRI_USER_CONFIG": str(user_config)},
                    clear=True,
                ),
                patch("sys.argv", ["cadri", "configure"]),
                patch("builtins.input", return_value="new-key"),
                patch("sys.stdout", stdout),
            ):
                main()

            self.assertEqual(configured_key_name_from_path(user_config), "new-key")
            self.assertIn(f"configured key_name in {user_config}", stdout.getvalue())

    def test_configure_reuses_current_key_name_on_empty_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            user_config = Path(temp_dir) / "config.yaml"
            set_configured_key_name("current-key", user_config)

            with (
                patch.dict(
                    os.environ,
                    {"CADRI_USER_CONFIG": str(user_config)},
                    clear=True,
                ),
                patch("sys.argv", ["cadri", "configure"]),
                patch("builtins.input", return_value=""),
                patch("sys.stdout", io.StringIO()),
            ):
                main()

            self.assertEqual(configured_key_name_from_path(user_config), "current-key")


def configured_key_name_from_path(path: Path) -> str | None:
    with patch.dict(os.environ, {"CADRI_USER_CONFIG": str(path)}, clear=True):
        return configured_key_name()


if __name__ == "__main__":
    unittest.main()
