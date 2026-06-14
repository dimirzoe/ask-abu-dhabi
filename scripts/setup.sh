#!/usr/bin/env bash
set -euo pipefail

# Bootstrap a local development environment for Ask Abu Dhabi.
# Creates a virtualenv, installs dependencies, and seeds the .env file.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON="${PYTHON:-python3}"

echo "==> Creating virtual environment (.venv)"
"$PYTHON" -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Upgrading pip"
pip install --upgrade pip

echo "==> Installing dependencies"
pip install -r requirements.txt

if [[ ! -f .env ]]; then
  echo "==> Creating .env from .env.example"
  cp .env.example .env
  echo "    Edit .env and add your API keys."
fi

echo "==> Setup complete. Activate with: source .venv/bin/activate"
