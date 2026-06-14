#!/usr/bin/env bash
set -euo pipefail

# Refresh the knowledge base by running the Firecrawl ETL pipeline.
# Exits non-zero (and preserves the existing KB) if fewer than the required
# number of sources validate.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

echo "==> Running ETL pipeline (etl.run)"
python -m etl.run
echo "==> Knowledge base refresh complete."
