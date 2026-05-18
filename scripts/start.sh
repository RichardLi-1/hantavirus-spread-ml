#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -x .venv/bin/python ]]; then
  echo "Run ./scripts/setup.sh first"
  exit 1
fi

if [[ ! -d web/dist ]]; then
  (cd web && npm install && npm run build)
fi

export PYTHONPATH="${PWD}"
exec .venv/bin/uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
