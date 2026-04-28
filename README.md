# CADRI CLI

`cadri-cli` keeps AWS instance work separated into three stages:

1. Prepare an AMI with system dependencies and the test generator installed.
2. Launch EC2 instances from that AMI and run the generator at boot.
3. Collect generated logs/results from S3.

## Setup

```bash
uv sync
```

Run the CLI through uv:

```bash
uv run cadri --help
```

For tab completion in zsh, activate the uv-managed environment and register
completion for the `cadri` executable:

```bash
. .venv/bin/activate
autoload -U bashcompinit && bashcompinit
eval "$(register-python-argcomplete --shell zsh cadri)"
```

After that, use `cadri <TAB>`, `cadri instance <TAB>`, and so on. Completion is
registered for the `cadri` executable name, not for `uv run cadri`.

AWS credentials should come from your normal AWS CLI environment, such as
`AWS_PROFILE`, `AWS_REGION`, or instance/role credentials.

## Launch a General Instance

Edit `config/general.yaml` with the AWS values for your account:

- `aws.region`
- `empty_instance.ami_id`
- `empty_instance.subnet_id`
- `empty_instance.security_group_ids`
- `empty_instance.key_name`

Then launch:

```bash
uv run cadri instance launch --config config/general.yaml
```

The instance and root volume are tagged with a generated `Name` in the form
`{config}-{datetime}`, for example `general-202604271444`.

List instance names, IDs, statuses, and public IPs:

```bash
uv run cadri instance list
```

Print one instance's public IP:

```bash
uv run cadri instance ip i-0123456789abcdef0
```

Terminate the instance:

```bash
uv run cadri instance terminate i-0123456789abcdef0
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
`cadri image`.

## Prepare an Image

```bash
uv run cadri image --config config/doppeltest.yaml
```

This launches a temporary builder instance from `image.source_ami_id`, runs the
commands in `image.setup_commands`, creates an AMI, and terminates the builder.

## Launch a Manual Builder

```bash
uv run cadri instance launch --config config/doppeltest.yaml
```

This launches a plain EC2 instance using `empty_instance`. If
`empty_instance.s3_file_systems` is set, each S3 file system is mounted at boot.
Use it for the first manual DoppelTest setup pass before encoding the working
commands into `image.setup_commands`.

## Launch a Generator Instance

```bash
uv run cadri launch --config config/doppeltest.yaml
```

This starts an instance from `launch.ami_id` and sends cloud-init user data that
runs `generator.command`. If `generator.s3_file_systems` is set, each S3 file
system is mounted before the command runs. Results are uploaded to the
configured S3 prefix.

## Collect Results

```bash
uv run cadri collect --config config/doppeltest.yaml --destination results/doppeltest
```

This downloads files from the configured S3 result prefix.
