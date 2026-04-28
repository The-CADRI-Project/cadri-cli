from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

from cadri_cli.aws import ec2_client, iam_client
from cadri_cli.config import load_config, require_values
from cadri_cli.iam_instance_profile import iam_instance_profile_arg
from cadri_cli.launch import tags_from_config
from cadri_cli.user_data import empty_instance_user_data


def instance_name(config_path: str) -> str:
    config_name = Path(config_path).stem
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    return f"{config_name}-{timestamp}"


def tags_with_name(tags: dict[str, str], name: str) -> list[dict[str, str]]:
    merged_tags = {**tags, "Name": name}
    return tags_from_config(merged_tags)


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


def metadata_options(config: dict[str, Any]) -> dict[str, Any]:
    options = config.get("metadata_options")
    if isinstance(options, dict):
        return options
    return {
        "HttpEndpoint": "enabled",
        "HttpPutResponseHopLimit": 2,
        "HttpTokens": "required",
    }


def private_dns_name_options(config: dict[str, Any]) -> dict[str, Any] | None:
    options = config.get("private_dns_name_options")
    if isinstance(options, dict):
        return options
    return None


def launch_empty_instance(config_path: str) -> str:
    app_config = load_config(config_path)
    instance_config = app_config.section("empty_instance")
    require_values("empty_instance", instance_config, ["ami_id", "subnet_id"])

    ec2 = ec2_client(app_config.aws)
    iam = iam_client(app_config.aws)
    tags = tags_with_name(instance_config.get("tags", {}), instance_name(config_path))
    run_args: dict[str, Any] = {
        "ImageId": instance_config["ami_id"],
        "InstanceType": instance_config.get("instance_type", "t3.large"),
        "MinCount": 1,
        "MaxCount": 1,
        "TagSpecifications": [
            {
                "ResourceType": "instance",
                "Tags": tags,
            },
            {
                "ResourceType": "volume",
                "Tags": tags,
            },
        ],
        "BlockDeviceMappings": block_device_mapping(instance_config),
        "NetworkInterfaces": network_interfaces(instance_config),
        "MetadataOptions": metadata_options(instance_config),
    }
    dns_options = private_dns_name_options(instance_config)
    if dns_options:
        run_args["PrivateDnsNameOptions"] = dns_options
    user_data = empty_instance_user_data(instance_config)
    if user_data:
        run_args["UserData"] = user_data
    if instance_config.get("iam_instance_profile"):
        run_args["IamInstanceProfile"] = iam_instance_profile_arg(
            instance_config["iam_instance_profile"],
            iam,
        )
    if instance_config.get("key_name"):
        run_args["KeyName"] = instance_config["key_name"]

    response = ec2.run_instances(**run_args)
    return response["Instances"][0]["InstanceId"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch an empty EC2 instance.")
    parser.add_argument("--config", required=True, help="Path to YAML config.")
    args = parser.parse_args()

    print(launch_empty_instance(args.config))


if __name__ == "__main__":
    main()
