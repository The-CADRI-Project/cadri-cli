from __future__ import annotations

import unittest

from cadri_cli.instance import format_instances, status_check_summary


class InstanceStatusCheckTest(unittest.TestCase):
    def test_status_check_summary_passed(self) -> None:
        self.assertEqual(
            status_check_summary(
                {
                    "SystemStatus": {"Status": "ok"},
                    "InstanceStatus": {"Status": "ok"},
                }
            ),
            "2/2 passed",
        )

    def test_status_check_summary_initializing(self) -> None:
        self.assertEqual(
            status_check_summary(
                {
                    "SystemStatus": {"Status": "ok"},
                    "InstanceStatus": {"Status": "initializing"},
                }
            ),
            "initializing",
        )

    def test_format_instances_includes_status_check_column(self) -> None:
        output = format_instances(
            [
                {
                    "name": "cadri-test",
                    "id": "i-0123456789abcdef0",
                    "status": "running",
                    "status_check": "2/2 passed",
                    "ip": "203.0.113.10",
                }
            ]
        )

        self.assertIn("STATUS_CHECK", output)
        self.assertIn("2/2 passed", output)


if __name__ == "__main__":
    unittest.main()
