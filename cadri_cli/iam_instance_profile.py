from __future__ import annotations

from typing import Any

from botocore.exceptions import ClientError


def _client_error_code(error: ClientError) -> str | None:
    return error.response.get("Error", {}).get("Code")


def iam_instance_profile_arg(value: str, iam: Any | None = None) -> dict[str, str]:
    """Build the EC2 IamInstanceProfile argument from a config value.

    EC2 accepts an instance profile name or ARN. Users often have the IAM role
    name instead, so when an IAM client is available we resolve role names to
    their attached instance profile.
    """
    if value.startswith("arn:"):
        return {"Arn": value}

    if iam is not None:
        try:
            response = iam.list_instance_profiles_for_role(RoleName=value)
        except ClientError as error:
            code = _client_error_code(error)
            fallback_codes = {
                "AccessDenied",
                "AccessDeniedException",
                "NoSuchEntity",
                "NoSuchEntityException",
                "UnauthorizedOperation",
            }
            if code not in fallback_codes:
                raise
        else:
            profiles = response.get("InstanceProfiles", [])
            if profiles:
                profile = sorted(
                    profiles,
                    key=lambda item: item.get("InstanceProfileName", ""),
                )[0]
                if profile.get("Arn"):
                    return {"Arn": profile["Arn"]}
                if profile.get("InstanceProfileName"):
                    return {"Name": profile["InstanceProfileName"]}

    return {"Name": value}
