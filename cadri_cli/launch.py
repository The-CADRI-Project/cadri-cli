from __future__ import annotations

import argparse
from typing import Any

from cadri_cli.aws import ec2_client, iam_client
from cadri_cli.config import load_config, require_values
from cadri_cli.iam_instance_profile import iam_instance_profile_arg
from cadri_cli.user_data import generator_user_data


def tags_from_config(tags: dict[str, str]) -> list[dict[str, str]]:
    return [{"Key": key, "Value": value} for key, value in tags.items()]


def optional_run_args(config: dict[str, Any], iam: Any | None = None) -> dict[str, Any]:
    args: dict[str, Any] = {}
    if config.get("iam_instance_profile"):
        args["IamInstanceProfile"] = iam_instance_profile_arg(
            config["iam_instance_profile"],
            iam,
        )
    if config.get("key_name"):
        args["KeyName"] = config["key_name"]
    if config.get("shutdown_behavior"):
        args["InstanceInitiatedShutdownBehavior"] = config["shutdown_behavior"]
    return args


def block_device_mapping(config: dict[str, Any]) -> list[dict[str, Any]]:
    volume_size = int(config.get("volume_size_gb", 100))
    volume_type = config.get("volume_type", "gp3")
    device_name = config.get("root_device_name", "/dev/sda1")
    ebs: dict[str, Any] = {
        "VolumeSize": volume_size,
        "VolumeType": volume_type,
        "DeleteOnTermination": bool(config.get("delete_on_termination", True)),
    }

    optional_ebs_fields = {
        "encrypted": "Encrypted",
        "iops": "Iops",
        "kms_key_id": "KmsKeyId",
        "snapshot_id": "SnapshotId",
        "throughput": "Throughput",
    }
    for config_key, aws_key in optional_ebs_fields.items():
        if config.get(config_key) is not None:
            ebs[aws_key] = config[config_key]

    return [
        {
            "DeviceName": device_name,
            "Ebs": ebs,
        }
    ]


def network_interfaces(config: dict[str, Any]) -> list[dict[str, Any]]:
    interface = {
        "SubnetId": config["subnet_id"],
        "DeviceIndex": 0,
    }
    if config.get("associate_public_ip_address") is not None:
        interface["AssociatePublicIpAddress"] = bool(
            config["associate_public_ip_address"]
        )
    if config.get("security_group_ids"):
        interface["Groups"] = config["security_group_ids"]
    return [interface]


def private_dns_name_options(config: dict[str, Any]) -> dict[str, Any] | None:
    options = config.get("private_dns_name_options")
    if isinstance(options, dict):
        return options
    return None


def launch_instance(config_path: str) -> str:
    app_config = load_config(config_path)
    launch_config = app_config.section("launch")
    generator_config = app_config.section("generator")

    require_values("launch", launch_config, ["ami_id", "subnet_id"])

    ec2 = ec2_client(app_config.aws)
    iam = iam_client(app_config.aws)

    run_args: dict[str, Any] = {
        "ImageId": launch_config["ami_id"],
        "InstanceType": launch_config.get("instance_type", "t3.medium"),
        "MinCount": 1,
        "MaxCount": 1,
        "UserData": generator_user_data(generator_config),
        "TagSpecifications": [
            {
                "ResourceType": "instance",
                "Tags": tags_from_config(launch_config.get("tags", {})),
            },
            {
                "ResourceType": "volume",
                "Tags": tags_from_config(launch_config.get("tags", {})),
            },
        ],
        "BlockDeviceMappings": block_device_mapping(launch_config),
        "NetworkInterfaces": network_interfaces(launch_config),
        **optional_run_args(launch_config, iam),
    }
    dns_options = private_dns_name_options(launch_config)
    if dns_options:
        run_args["PrivateDnsNameOptions"] = dns_options

    try:
        response = ec2.run_instances(**run_args)
    except Exception as e:
        raise RuntimeError(f"EC2 launch failed: {e}")

    instance_id = response["Instances"][0]["InstanceId"]
    return instance_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch a CADRI generator instance.")
    parser.add_argument("--config", required=True, help="Path to YAML config.")
    args = parser.parse_args()

    instance_id = launch_instance(args.config)
    print(instance_id)


if __name__ == "__main__":
    main()
