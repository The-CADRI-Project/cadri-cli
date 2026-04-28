from __future__ import annotations

import argparse
from pathlib import Path

from cadri_cli.aws import s3_client
from cadri_cli.config import load_config, require_values


def collect_results(config_path: str, destination: str) -> int:
    app_config = load_config(config_path)
    generator_config = app_config.section("generator")
    require_values("generator", generator_config, ["s3_bucket", "s3_prefix"])
    bucket = generator_config["s3_bucket"]
    prefix = generator_config["s3_prefix"].strip("/")
    target = Path(destination)
    target.mkdir(parents=True, exist_ok=True)

    s3 = s3_client(app_config.aws)
    paginator = s3.get_paginator("list_objects_v2")
    count = 0

    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for item in page.get("Contents", []):
            key = item["Key"]
            if key.endswith("/"):
                continue
            relative = Path(key).relative_to(prefix)
            local_path = target / relative
            local_path.parent.mkdir(parents=True, exist_ok=True)
            s3.download_file(bucket, key, str(local_path))
            count += 1

    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect CADRI generator results from S3.")
    parser.add_argument("--config", required=True, help="Path to YAML config.")
    parser.add_argument("--destination", default="results", help="Local output directory.")
    args = parser.parse_args()

    count = collect_results(args.config, args.destination)
    print(f"downloaded {count} files")


if __name__ == "__main__":
    main()
