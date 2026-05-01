from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone
from typing import Any

from cadri_cli.aws import default_ec2_client, ec2_client, iam_client
from cadri_cli.config import load_config, require_values
from cadri_cli.iam_instance_profile import iam_instance_profile_arg


def build_setup_user_data(commands: list[str]) -> str:
    body = "\n".join(commands)
    return f"""#!/bin/bash
set -euxo pipefail
exec > >(tee -a /var/log/cadri-image-setup.log) 2>&1
{body}
shutdown -h now
"""


def optional_run_args(config: dict[str, Any], iam: Any | None = None) -> dict[str, Any]:
    args: dict[str, Any] = {}
    if config.get("subnet_id"):
        args["SubnetId"] = config["subnet_id"]
    if config.get("security_group_ids"):
        args["SecurityGroupIds"] = config["security_group_ids"]
    if config.get("iam_instance_profile"):
        args["IamInstanceProfile"] = iam_instance_profile_arg(
            config["iam_instance_profile"],
            iam,
        )
    if config.get("key_name"):
        args["KeyName"] = config["key_name"]
    return args


def wait_for_stopped(ec2: Any, instance_id: str, timeout_minutes: int) -> None:
    waiter = ec2.get_waiter("instance_stopped")
    waiter.wait(
        InstanceIds=[instance_id],
        WaiterConfig={"Delay": 15, "MaxAttempts": max(1, timeout_minutes * 4)},
    )


def tag_value(resource: dict[str, Any], key: str) -> str:
    for tag in resource.get("Tags", []):
        if tag.get("Key") == key:
            return tag.get("Value", "")
    return ""


def image_snapshot_ids(image: dict[str, Any]) -> list[str]:
    snapshot_ids = []
    for mapping in image.get("BlockDeviceMappings", []):
        snapshot_id = mapping.get("Ebs", {}).get("SnapshotId")
        if snapshot_id:
            snapshot_ids.append(snapshot_id)
    return snapshot_ids


def list_images(region: str | None = None) -> list[dict[str, str]]:
    ec2 = default_ec2_client(region)
    response = ec2.describe_images(Owners=["self"])
    images = response.get("Images", [])
    images.sort(key=lambda image: image.get("CreationDate", ""), reverse=True)
    return [
        {
            "name": image.get("Name") or tag_value(image, "Name") or "-",
            "id": image.get("ImageId", "-"),
            "state": image.get("State", "-"),
            "created": image.get("CreationDate", "-"),
            "snapshots": ",".join(image_snapshot_ids(image)) or "-",
        }
        for image in images
    ]


def format_images(images: list[dict[str, str]]) -> str:
    headers = {
        "name": "NAME",
        "id": "IMAGE_ID",
        "state": "STATE",
        "created": "CREATED",
        "snapshots": "SNAPSHOT_IDS",
    }
    rows = [headers, *images]
    widths = {
        key: max(len(row[key]) for row in rows)
        for key in ("name", "id", "state", "created", "snapshots")
    }
    lines = [
        f"{headers['name']:<{widths['name']}}  "
        f"{headers['id']:<{widths['id']}}  "
        f"{headers['state']:<{widths['state']}}  "
        f"{headers['created']:<{widths['created']}}  "
        f"{headers['snapshots']:<{widths['snapshots']}}"
    ]
    for image in images:
        lines.append(
            f"{image['name']:<{widths['name']}}  "
            f"{image['id']:<{widths['id']}}  "
            f"{image['state']:<{widths['state']}}  "
            f"{image['created']:<{widths['created']}}  "
            f"{image['snapshots']:<{widths['snapshots']}}"
        )
    return "\n".join(lines)


def describe_instance(ec2: Any, instance_id: str) -> dict[str, Any]:
    response = ec2.describe_instances(InstanceIds=[instance_id])
    reservations = response.get("Reservations", [])
    instances = [
        instance
        for reservation in reservations
        for instance in reservation.get("Instances", [])
    ]
    if not instances:
        raise ValueError(f"Instance not found: {instance_id}")
    return instances[0]


def create_image_from_instance(
    instance_id: str,
    name: str,
    region: str | None = None,
) -> str:
    ec2 = default_ec2_client(region)
    instance = describe_instance(ec2, instance_id)
    state = instance.get("State", {}).get("Name", "unknown")
    if state != "running":
        raise ValueError(f"Instance {instance_id} must be running; state={state}")

    response = ec2.create_image(
        InstanceId=instance_id,
        Name=name,
        Description=f"CADRI image created from {instance_id}",
        NoReboot=True,
        TagSpecifications=[
            {
                "ResourceType": "image",
                "Tags": [
                    {"Key": "Name", "Value": name},
                    {"Key": "Role", "Value": "cadri-generator"},
                ],
            }
        ],
    )
    image_id = response["ImageId"]
    ec2.get_waiter("image_available").wait(ImageIds=[image_id])
    return image_id


def create_image(config_path: str) -> str:
    app_config = load_config(config_path)
    image_config = app_config.section("image")
    require_values(
        "image",
        image_config,
        ["source_ami_id", "subnet_id", "security_group_ids"],
    )
    ec2 = ec2_client(app_config.aws)
    iam = iam_client(app_config.aws)

    name_prefix = image_config.get("name_prefix", "cadri-generator")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    ami_name = f"{name_prefix}-{timestamp}"

    response = ec2.run_instances(
        ImageId=image_config["source_ami_id"],
        InstanceType=image_config.get("instance_type", "t3.medium"),
        MinCount=1,
        MaxCount=1,
        UserData=build_setup_user_data(image_config.get("setup_commands", [])),
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "Name", "Value": f"{name_prefix}-builder"},
                    {"Key": "Role", "Value": "cadri-image-builder"},
                ],
            }
        ],
        **optional_run_args(image_config, iam),
    )
    instance_id = response["Instances"][0]["InstanceId"]

    try:
        wait_for_stopped(
            ec2,
            instance_id,
            int(image_config.get("setup_timeout_minutes", 60)),
        )
        image_response = ec2.create_image(
            InstanceId=instance_id,
            Name=ami_name,
            Description="CADRI generator image",
            NoReboot=True,
            TagSpecifications=[
                {
                    "ResourceType": "image",
                    "Tags": [
                        {"Key": "Name", "Value": ami_name},
                        {"Key": "Role", "Value": "cadri-generator"},
                    ],
                }
            ],
        )
        image_id = image_response["ImageId"]
        ec2.get_waiter("image_available").wait(ImageIds=[image_id])
        return image_id
    finally:
        ec2.terminate_instances(InstanceIds=[instance_id])
        time.sleep(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage CADRI AMIs.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    list_parser = subcommands.add_parser("list", help="List owned AMIs.")
    list_parser.add_argument("--region", default=None, help="AWS region override.")

    create_parser = subcommands.add_parser(
        "create",
        help="Create an AMI from a running EC2 instance.",
    )
    create_parser.add_argument(
        "instance_id",
        metavar="INSTANCE_ID",
        help="Running EC2 instance ID.",
    )
    create_parser.add_argument("name", metavar="NAME", help="Name for the new AMI.")
    create_parser.add_argument("--region", default=None, help="AWS region override.")

    args = parser.parse_args()

    if args.command == "list":
        print(format_images(list_images(args.region)))
    elif args.command == "create":
        print(create_image_from_instance(args.instance_id, args.name, args.region))


if __name__ == "__main__":
    main()
