from __future__ import annotations

from datetime import datetime, timezone
import unittest
from unittest.mock import patch

from cadri_cli.key_pair import format_key_pairs, list_key_pairs


class FakeEc2:
    def describe_key_pairs(self) -> dict:
        return {
            "KeyPairs": [
                {
                    "KeyName": "workstation",
                    "KeyPairId": "key-0123456789abcdef0",
                    "KeyType": "rsa",
                    "KeyFingerprint": "aa:bb:cc",
                    "CreateTime": datetime(2026, 5, 1, tzinfo=timezone.utc),
                },
                {
                    "KeyName": "builder",
                    "KeyPairId": "key-11111111111111111",
                    "KeyType": "ed25519",
                    "KeyFingerprint": "dd:ee:ff",
                },
            ]
        }


class KeyPairTest(unittest.TestCase):
    def test_list_key_pairs_formats_aws_key_pairs(self) -> None:
        with patch("cadri_cli.key_pair.default_ec2_client", return_value=FakeEc2()):
            key_pairs = list_key_pairs("us-west-2")

        self.assertEqual(
            key_pairs,
            [
                {
                    "name": "builder",
                    "id": "key-11111111111111111",
                    "type": "ed25519",
                    "fingerprint": "dd:ee:ff",
                    "created": "-",
                },
                {
                    "name": "workstation",
                    "id": "key-0123456789abcdef0",
                    "type": "rsa",
                    "fingerprint": "aa:bb:cc",
                    "created": "2026-05-01T00:00:00+00:00",
                },
            ],
        )

    def test_format_key_pairs_includes_expected_columns(self) -> None:
        output = format_key_pairs(
            [
                {
                    "name": "workstation",
                    "id": "key-0123456789abcdef0",
                    "type": "rsa",
                    "fingerprint": "aa:bb:cc",
                    "created": "2026-05-01T00:00:00+00:00",
                }
            ]
        )

        self.assertIn("KEY_PAIR_ID", output)
        self.assertIn("FINGERPRINT", output)
        self.assertIn("workstation", output)


if __name__ == "__main__":
    unittest.main()
