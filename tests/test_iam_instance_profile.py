from __future__ import annotations

import unittest

from botocore.exceptions import ClientError

from cadri_cli.iam_instance_profile import iam_instance_profile_arg


class FakeIam:
    def __init__(self, response: dict | None = None, error_code: str | None = None):
        self.response = response or {}
        self.error_code = error_code
        self.role_names: list[str] = []

    def list_instance_profiles_for_role(self, RoleName: str) -> dict:
        self.role_names.append(RoleName)
        if self.error_code:
            raise ClientError(
                {"Error": {"Code": self.error_code, "Message": "not found"}},
                "ListInstanceProfilesForRole",
            )
        return self.response


class IamInstanceProfileArgTest(unittest.TestCase):
    def test_arn_is_passed_as_arn(self) -> None:
        arn = "arn:aws:iam::123456789012:instance-profile/cadri-profile"

        self.assertEqual(iam_instance_profile_arg(arn), {"Arn": arn})

    def test_role_name_resolves_to_attached_instance_profile_arn(self) -> None:
        iam = FakeIam(
            {
                "InstanceProfiles": [
                    {
                        "InstanceProfileName": "cadri-profile",
                        "Arn": "arn:aws:iam::123456789012:instance-profile/cadri-profile",
                    }
                ]
            }
        )

        self.assertEqual(
            iam_instance_profile_arg("cadri-role", iam),
            {"Arn": "arn:aws:iam::123456789012:instance-profile/cadri-profile"},
        )
        self.assertEqual(iam.role_names, ["cadri-role"])

    def test_missing_role_falls_back_to_profile_name(self) -> None:
        iam = FakeIam(error_code="NoSuchEntity")

        self.assertEqual(
            iam_instance_profile_arg("cadri-profile", iam),
            {"Name": "cadri-profile"},
        )

    def test_access_denied_falls_back_to_profile_name(self) -> None:
        iam = FakeIam(error_code="AccessDenied")

        self.assertEqual(
            iam_instance_profile_arg("cadri-profile", iam),
            {"Name": "cadri-profile"},
        )


if __name__ == "__main__":
    unittest.main()
