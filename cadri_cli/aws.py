from __future__ import annotations

from typing import Any

import boto3

from cadri_cli.config import AwsConfig


def session(config: AwsConfig) -> boto3.Session:
    if config.profile:
        return boto3.Session(profile_name=config.profile, region_name=config.region)
    return boto3.Session(region_name=config.region)


def ec2_client(config: AwsConfig) -> Any:
    return session(config).client("ec2")


def iam_client(config: AwsConfig) -> Any:
    return session(config).client("iam")


def default_ec2_client(region: str | None = None) -> Any:
    return boto3.Session(region_name=region).client("ec2")


def s3_client(config: AwsConfig) -> Any:
    return session(config).client("s3")
