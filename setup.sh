#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v uv >/dev/null 2>&1; then
  echo "error: uv is required to install cadri-cli" >&2
  echo "Install uv, then rerun ./setup.sh" >&2
  exit 1
fi

uv tool install --force --editable --python 3.11 "$ROOT_DIR"

cat <<EOF

cadri-cli was installed in editable mode.

Run:
  cadri --help

If cadri is not found, add this to your shell profile:
  export PATH="\$HOME/.local/bin:\$PATH"
EOF
