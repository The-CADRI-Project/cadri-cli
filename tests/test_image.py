from __future__ import annotations

import unittest
from unittest.mock import patch

from cadri_cli.image import (
    create_image_from_instance,
    format_images,
    image_snapshot_ids,
)


class FakeWaiter:
    def __init__(self) -> None:
        self.image_ids: list[list[str]] = []

    def wait(self, ImageIds: list[str]) -> None:
        self.image_ids.append(ImageIds)


class FakeEc2:
    def __init__(self, state: str = "running") -> None:
        self.state = state
        self.created: dict | None = None
        self.waiter = FakeWaiter()

    def describe_instances(self, InstanceIds: list[str]) -> dict:
        return {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": InstanceIds[0],
                            "State": {"Name": self.state},
                        }
                    ]
                }
            ]
        }

    def create_image(self, **kwargs: object) -> dict:
        self.created = kwargs
        return {"ImageId": "ami-0123456789abcdef0"}

    def get_waiter(self, name: str) -> FakeWaiter:
        self.waiter.name = name
        return self.waiter


class ImageTest(unittest.TestCase):
    def test_image_snapshot_ids_extracts_ebs_snapshots(self) -> None:
        self.assertEqual(
            image_snapshot_ids(
                {
                    "BlockDeviceMappings": [
                        {"Ebs": {"SnapshotId": "snap-root"}},
                        {"VirtualName": "ephemeral0"},
                        {"Ebs": {"SnapshotId": "snap-data"}},
                    ]
                }
            ),
            ["snap-root", "snap-data"],
        )

    def test_format_images_includes_snapshot_ids(self) -> None:
        output = format_images(
            [
                {
                    "name": "cadri-test",
                    "id": "ami-0123456789abcdef0",
                    "state": "available",
                    "created": "2026-05-01T00:00:00.000Z",
                    "snapshots": "snap-root,snap-data",
                }
            ]
        )

        self.assertIn("SNAPSHOT_IDS", output)
        self.assertIn("snap-root,snap-data", output)

    def test_create_image_from_instance_uses_running_instance(self) -> None:
        ec2 = FakeEc2()

        with patch("cadri_cli.image.default_ec2_client", return_value=ec2):
            image_id = create_image_from_instance(
                "i-0123456789abcdef0",
                "cadri-test-image",
                "us-west-2",
            )

        self.assertEqual(image_id, "ami-0123456789abcdef0")
        self.assertEqual(
            ec2.created,
            {
                "InstanceId": "i-0123456789abcdef0",
                "Name": "cadri-test-image",
                "Description": "CADRI image created from i-0123456789abcdef0",
                "NoReboot": True,
                "TagSpecifications": [
                    {
                        "ResourceType": "image",
                        "Tags": [
                            {"Key": "Name", "Value": "cadri-test-image"},
                            {"Key": "Role", "Value": "cadri-generator"},
                        ],
                    }
                ],
            },
        )
        self.assertEqual(ec2.waiter.image_ids, [["ami-0123456789abcdef0"]])

    def test_create_image_from_instance_rejects_stopped_instance(self) -> None:
        ec2 = FakeEc2(state="stopped")

        with patch("cadri_cli.image.default_ec2_client", return_value=ec2):
            with self.assertRaisesRegex(ValueError, "must be running"):
                create_image_from_instance("i-0123456789abcdef0", "cadri-test-image")


if __name__ == "__main__":
    unittest.main()
