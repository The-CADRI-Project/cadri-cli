from __future__ import annotations

from datetime import datetime
from typing import Any

from cadri_cli.aws import default_ec2_client


def format_time(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value) if value else "-"


def list_key_pairs(region: str | None = None) -> list[dict[str, str]]:
    ec2 = default_ec2_client(region)
    response = ec2.describe_key_pairs()
    key_pairs = response.get("KeyPairs", [])
    key_pairs.sort(key=lambda key_pair: key_pair.get("KeyName", ""))
    return [
        {
            "name": key_pair.get("KeyName", "-"),
            "id": key_pair.get("KeyPairId", "-"),
            "type": key_pair.get("KeyType", "-"),
            "fingerprint": key_pair.get("KeyFingerprint", "-"),
            "created": format_time(key_pair.get("CreateTime")),
        }
        for key_pair in key_pairs
    ]


def format_key_pairs(key_pairs: list[dict[str, str]]) -> str:
    headers = {
        "name": "NAME",
        "id": "KEY_PAIR_ID",
        "type": "TYPE",
        "fingerprint": "FINGERPRINT",
        "created": "CREATED",
    }
    rows = [headers, *key_pairs]
    widths = {
        key: max(len(row[key]) for row in rows)
        for key in ("name", "id", "type", "fingerprint", "created")
    }
    lines = [
        f"{headers['name']:<{widths['name']}}  "
        f"{headers['id']:<{widths['id']}}  "
        f"{headers['type']:<{widths['type']}}  "
        f"{headers['fingerprint']:<{widths['fingerprint']}}  "
        f"{headers['created']:<{widths['created']}}"
    ]
    for key_pair in key_pairs:
        lines.append(
            f"{key_pair['name']:<{widths['name']}}  "
            f"{key_pair['id']:<{widths['id']}}  "
            f"{key_pair['type']:<{widths['type']}}  "
            f"{key_pair['fingerprint']:<{widths['fingerprint']}}  "
            f"{key_pair['created']:<{widths['created']}}"
        )
    return "\n".join(lines)
