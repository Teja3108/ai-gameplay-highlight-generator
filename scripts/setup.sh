#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

npm install
uv sync --project apps/api --extra dev
uv run --project apps/api pre-commit install

echo "Setup complete."
