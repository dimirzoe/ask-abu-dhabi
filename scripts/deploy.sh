#!/usr/bin/env bash
set -euo pipefail

# Build and start the Ask Abu Dhabi stack with Docker Compose.
# Requires a populated .env file (see .env.example).

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f .env ]]; then
  echo "ERROR: .env not found. Copy .env.example to .env and add your keys." >&2
  exit 1
fi

echo "==> Building images"
docker compose build

echo "==> Starting services (detached)"
docker compose up -d

echo "==> Deployed:"
echo "    UI : http://localhost:8501"
echo "    API: http://localhost:8000"
