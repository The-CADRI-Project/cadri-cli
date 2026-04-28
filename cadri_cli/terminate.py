from __future__ import annotations

import argparse
from typing import Any

from cadri_cli.aws import default_ec2_client, ec2_client
from cadri_cli.config import load_config


def client_from_options(config_path: str | None, region: str | None) -> Any:
    if config_path:
        return ec2_client(load_config(config_path).aws)
    return default_ec2_client(region)


def terminate_instance(
    instance_id: str,
    config_path: str | None = None,
    region: str | None = None,
) -> str:
    ec2 = client_from_options(config_path, region)
    response = ec2.terminate_instances(InstanceIds=[instance_id])
    changes = response.get("TerminatingInstances", [])
    if not changes:
        raise ValueError(f"Instance not found or not terminated: {instance_id}")

    state_change = changes[0]
    previous = state_change.get("PreviousState", {}).get("Name", "unknown")
    current = state_change.get("CurrentState", {}).get("Name", "unknown")
    return f"{instance_id}: {previous} -> {current}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Terminate an EC2 instance.")
    parser.add_argument("instance_id", help="EC2 instance ID.")
    parser.add_argument("--config", default=None, help="Path to YAML config.")
    parser.add_argument("--region", default=None, help="AWS region override.")
    args = parser.parse_args()

    print(terminate_instance(args.instance_id, args.config, args.region))


if __name__ == "__main__":
    main()
