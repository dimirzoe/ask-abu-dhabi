#!/usr/bin/env bash
set -euo pipefail

# Run the Ask Abu Dhabi services.
#   ./scripts/run.sh ui    -> Streamlit UI   (default, port 8501)
#   ./scripts/run.sh api   -> FastAPI server (port 8000)

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

TARGET="${1:-ui}"

case "$TARGET" in
  ui)
    echo "==> Starting Streamlit UI on http://localhost:8501"
    exec streamlit run app.py
    ;;
  api)
    echo "==> Starting FastAPI on http://localhost:8000"
    exec uvicorn api:app --host 0.0.0.0 --port 8000 --reload
    ;;
  *)
    echo "Usage: $0 [ui|api]" >&2
    exit 1
    ;;
esac
