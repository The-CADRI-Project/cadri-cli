from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone
from typing import Any

from cadri_cli.aws import ec2_client, iam_client
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
    parser = argparse.ArgumentParser(description="Prepare a CADRI generator AMI.")
    parser.add_argument("--config", required=True, help="Path to YAML config.")
    args = parser.parse_args()

    image_id = create_image(args.config)
    print(image_id)


if __name__ == "__main__":
    main()
