from __future__ import annotations

import shlex
from typing import Any


def s3_file_system_mount_commands(
    config: dict[str, Any], section_name: str = "generator"
) -> str:
    file_systems = config.get("s3_file_systems", [])
    if not file_systems:
        return ""
    if not isinstance(file_systems, list):
        raise ValueError(f"{section_name}.s3_file_systems must be a list")

    commands: list[str] = []
    for index, file_system in enumerate(file_systems, start=1):
        if not isinstance(file_system, dict):
            raise ValueError(
                f"{section_name}.s3_file_systems[{index}] must be a mapping"
            )

        file_system_id = file_system.get("id")
        mount_point = file_system.get("mount_point")
        if not file_system_id or not mount_point:
            raise ValueError(
                f"{section_name}.s3_file_systems[{index}] requires id and mount_point"
            )

        commands.extend(
            [
                f"mkdir -p {shlex.quote(str(mount_point))}",
                (
                    "curl -fsSL https://amazon-efs-utils.aws.com/efs-utils-installer.sh "
                    "| sh -s -- --install-launch-wizard "
                    f"--mount-s3files {shlex.quote(str(file_system_id))} "
                    f"{shlex.quote(str(mount_point))}"
                ),
            ]
        )

    return "\n".join(commands)


def empty_instance_user_data(empty_instance: dict[str, Any]) -> str | None:
    mount_commands = s3_file_system_mount_commands(empty_instance, "empty_instance")
    if not mount_commands:
        return None

    log_file = empty_instance.get("log_file", "/var/log/cadri-empty-instance.log")
    return f"""#!/bin/bash
set -euxo pipefail

LOG_FILE={shlex.quote(log_file)}
exec > >(tee -a "$LOG_FILE") 2>&1

{mount_commands}
"""


def generator_user_data(generator: dict[str, Any]) -> str:
    workdir = generator["working_directory"]
    command = generator["command"]
    results_dir = generator["results_directory"]
    log_file = generator.get("log_file", "/var/log/cadri-generator.log")
    bucket = generator.get("s3_bucket")
    prefix = generator.get("s3_prefix", "").strip("/")
    mount_commands = s3_file_system_mount_commands(generator, "generator")

    if bucket:
        upload_commands = f"""
  S3_URI="s3://{shlex.quote(bucket)}/{shlex.quote(prefix)}/$(hostname)-$(date +%Y%m%dT%H%M%SZ)"
  if [ -d "$RESULTS_DIR" ]; then
    aws s3 cp "$RESULTS_DIR" "$S3_URI/results" --recursive
  fi
  aws s3 cp "$LOG_FILE" "$S3_URI/cadri-generator.log"
  echo "$status" > /tmp/cadri-generator-exit-code
  aws s3 cp /tmp/cadri-generator-exit-code "$S3_URI/exit-code.txt"
"""
    else:
        upload_commands = """
  echo "generator.s3_bucket is not configured; leaving results on the instance"
"""

    return f"""#!/bin/bash
set -uo pipefail

LOG_FILE={shlex.quote(log_file)}
WORKDIR={shlex.quote(workdir)}
RESULTS_DIR={shlex.quote(results_dir)}

exec > >(tee -a "$LOG_FILE") 2>&1

finish() {{
  status=$?
  set +e
{upload_commands.rstrip()}
  shutdown -h now
}}
trap finish EXIT

set -euxo pipefail
{mount_commands}
cd "$WORKDIR"
bash -lc {shlex.quote(command)}
"""
