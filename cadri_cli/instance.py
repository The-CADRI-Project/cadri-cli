from __future__ import annotations

import argparse
from typing import Any

from cadri_cli.aws import default_ec2_client


def tag_value(instance: dict[str, Any], key: str) -> str:
    for tag in instance.get("Tags", []):
        if tag.get("Key") == key:
            return tag.get("Value", "")
    return ""


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


def public_ip(instance_id: str, region: str | None = None) -> str:
    instance = describe_instance(default_ec2_client(region), instance_id)
    ip_address = instance.get("PublicIpAddress")
    if not ip_address:
        state = instance.get("State", {}).get("Name", "unknown")
        raise ValueError(f"Instance {instance_id} has no public IP address; state={state}")
    return ip_address


def status_check_summary(status: dict[str, Any] | None) -> str:
    if not status:
        return "-"

    checks = [
        status.get("SystemStatus", {}).get("Status"),
        status.get("InstanceStatus", {}).get("Status"),
    ]
    checks = [check for check in checks if check]
    if not checks:
        return "-"
    if all(check == "ok" for check in checks):
        return f"{len(checks)}/{len(checks)} passed"
    if any(check == "initializing" for check in checks):
        return "initializing"
    if all(check == "not-applicable" for check in checks):
        return "not-applicable"

    passed = sum(1 for check in checks if check == "ok")
    return f"{passed}/{len(checks)} passed"


def describe_instance_statuses(
    ec2: Any,
    instance_ids: list[str],
) -> dict[str, dict[str, Any]]:
    if not instance_ids:
        return {}

    response = ec2.describe_instance_status(
        InstanceIds=instance_ids,
        IncludeAllInstances=True,
    )
    return {
        status["InstanceId"]: status
        for status in response.get("InstanceStatuses", [])
        if status.get("InstanceId")
    }


def list_instances(region: str | None = None) -> list[dict[str, str]]:
    ec2 = default_ec2_client(region)
    response = ec2.describe_instances(
        Filters=[
            {
                "Name": "instance-state-name",
                "Values": ["pending", "running", "stopping", "stopped"],
            }
        ]
    )
    instances = [
        instance
        for reservation in response.get("Reservations", [])
        for instance in reservation.get("Instances", [])
    ]
    instances.sort(key=lambda instance: instance.get("LaunchTime"), reverse=True)
    instance_statuses = describe_instance_statuses(
        ec2,
        [instance["InstanceId"] for instance in instances if instance.get("InstanceId")],
    )
    return [
        {
            "name": tag_value(instance, "Name") or "-",
            "id": instance.get("InstanceId", "-"),
            "status": instance.get("State", {}).get("Name", "-"),
            "status_check": status_check_summary(
                instance_statuses.get(instance.get("InstanceId", "")),
            ),
            "ip": instance.get("PublicIpAddress", "-"),
        }
        for instance in instances
    ]


def format_instances(instances: list[dict[str, str]]) -> str:
    headers = {
        "name": "NAME",
        "id": "INSTANCE_ID",
        "status": "STATUS",
        "status_check": "STATUS_CHECK",
        "ip": "PUBLIC_IP",
    }
    rows = [headers, *instances]
    widths = {
        key: max(len(row[key]) for row in rows)
        for key in ("name", "id", "status", "status_check", "ip")
    }
    lines = [
        f"{headers['name']:<{widths['name']}}  "
        f"{headers['id']:<{widths['id']}}  "
        f"{headers['status']:<{widths['status']}}  "
        f"{headers['status_check']:<{widths['status_check']}}  "
        f"{headers['ip']:<{widths['ip']}}"
    ]
    for instance in instances:
        lines.append(
            f"{instance['name']:<{widths['name']}}  "
            f"{instance['id']:<{widths['id']}}  "
            f"{instance['status']:<{widths['status']}}  "
            f"{instance['status_check']:<{widths['status_check']}}  "
            f"{instance['ip']:<{widths['ip']}}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect EC2 instances.")
    parser.add_argument("instance_id", nargs="?", help="EC2 instance ID.")
    parser.add_argument("--list", action="store_true", help="List EC2 instances.")
    parser.add_argument("--region", default=None, help="AWS region override.")
    args = parser.parse_args()

    if args.list:
        print(format_instances(list_instances(args.region)))
    elif args.instance_id:
        print(public_ip(args.instance_id, args.region))
    else:
        parser.error("instance_id is required unless --list is used")


if __name__ == "__main__":
    main()
