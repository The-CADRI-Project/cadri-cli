from __future__ import annotations

import argparse

import argcomplete


def main() -> None:
    parser = argparse.ArgumentParser(prog="cadri", description="Manage CADRI AWS instances.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    image_parser = subcommands.add_parser("image", help="Manage CADRI AMIs.")
    image_subcommands = image_parser.add_subparsers(
        dest="image_command",
        required=True,
    )

    image_list_parser = image_subcommands.add_parser("list", help="List owned AMIs.")
    image_list_parser.add_argument("--region", default=None, help="AWS region override.")

    image_create_parser = image_subcommands.add_parser(
        "create",
        help="Create an AMI from a running EC2 instance.",
    )
    image_create_parser.add_argument(
        "instance_id",
        metavar="INSTANCE_ID",
        help="Running EC2 instance ID.",
    )
    image_create_parser.add_argument("name", metavar="NAME", help="Name for the new AMI.")
    image_create_parser.add_argument("--region", default=None, help="AWS region override.")

    instance_parser = subcommands.add_parser("instance", help="Manage EC2 instances.")
    instance_subcommands = instance_parser.add_subparsers(
        dest="instance_command",
        required=True,
    )

    instance_launch_parser = instance_subcommands.add_parser(
        "launch",
        help="Launch a plain EC2 instance for manual setup.",
    )
    instance_launch_parser.add_argument("--config", required=True, help="Path to YAML config.")

    instance_list_parser = instance_subcommands.add_parser(
        "list",
        help="List EC2 instances.",
    )
    instance_list_parser.add_argument("--region", default=None, help="AWS region override.")

    instance_ip_parser = instance_subcommands.add_parser(
        "ip",
        help="Print an EC2 instance public IP address.",
    )
    instance_ip_parser.add_argument("instance_id", help="EC2 instance ID.")
    instance_ip_parser.add_argument("--region", default=None, help="AWS region override.")

    instance_terminate_parser = instance_subcommands.add_parser(
        "terminate",
        help="Terminate an EC2 instance.",
    )
    instance_terminate_parser.add_argument("instance_id", help="EC2 instance ID.")
    instance_terminate_parser.add_argument("--region", default=None, help="AWS region override.")

    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    if args.command == "image":
        if args.image_command == "list":
            from cadri_cli.image import format_images, list_images

            print(format_images(list_images(args.region)))
        elif args.image_command == "create":
            from cadri_cli.image import create_image_from_instance

            print(create_image_from_instance(args.instance_id, args.name, args.region))
    elif args.command == "instance":
        if args.instance_command == "launch":
            from cadri_cli.empty_instance import launch_empty_instance

            print(launch_empty_instance(args.config))
        elif args.instance_command == "list":
            from cadri_cli.instance import format_instances, list_instances

            print(format_instances(list_instances(args.region)))
        elif args.instance_command == "ip":
            from cadri_cli.instance import public_ip

            print(public_ip(args.instance_id, args.region))
        elif args.instance_command == "terminate":
            from cadri_cli.terminate import terminate_instance

            print(terminate_instance(args.instance_id, region=args.region))

if __name__ == "__main__":
    main()
