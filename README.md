# CADRI CLI

`cadri-cli` manages CADRI AWS instances and AMIs.

## Setup

```bash
./setup.sh
```

This installs `cadri-cli` for the current user in editable mode, so source
changes in this checkout are reflected without reinstalling.

Run the CLI directly:

```bash
cadri --help
```

For tab completion in zsh, register completion for the `cadri` executable:

```bash
autoload -U bashcompinit && bashcompinit
eval "$(register-python-argcomplete --shell zsh cadri)"
```

After that, use `cadri <TAB>`, `cadri instance <TAB>`, and so on. Completion is
registered for the `cadri` executable name, not for `uv run cadri`.

AWS credentials should come from your normal AWS CLI environment, such as
`AWS_PROFILE`, `AWS_REGION`, or instance/role credentials.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines, including
the required commit message format.

## Launch a General Instance

Edit `config/general.yaml` with the AWS values for your account:

- `aws.region`
- `empty_instance.ami_id`
- `empty_instance.subnet_id`
- `empty_instance.security_group_ids`
- `empty_instance.key_name`

Then launch:

```bash
cadri instance launch --config config/general.yaml
```

The instance and root volume are tagged with a generated `Name` in the form
`{config}-{datetime}`, for example `general-202604271444`.

List instance names, IDs, statuses, and public IPs:

```bash
cadri instance list
```

Print one instance's public IP:

```bash
cadri instance ip i-0123456789abcdef0
```

Terminate the instance:

```bash
cadri instance terminate i-0123456789abcdef0
```

## Configure DoppelTest

Edit `config/doppeltest.yaml` with the AWS values for your account:

- `aws.region`
- `image.source_ami_id`
- `image.subnet_id`
- `image.security_group_ids`
- `empty_instance.ami_id`
- `empty_instance.subnet_id`
- `empty_instance.security_group_ids`
- `empty_instance.s3_file_systems`
- `generator.s3_bucket`
- `generator.s3_file_systems`

After the image is created, set `launch.ami_id` to the AMI ID printed by
`cadri image create`.

## Manage Images

List owned AMIs and their backing snapshot IDs:

```bash
cadri image list
```

Create an AMI from a running instance:

```bash
cadri image create i-0123456789abcdef0 cadri-generator-manual
```

## Launch a Manual Builder

```bash
cadri instance launch --config config/doppeltest.yaml
```

This launches a plain EC2 instance using `empty_instance`. If
`empty_instance.s3_file_systems` is set, each S3 file system is mounted at boot.
Use it for the first manual DoppelTest setup pass before encoding the working
commands into `image.setup_commands`.
