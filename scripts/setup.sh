#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Prefer project venv; create with pyenv 3.11.9 if missing
PYENV_PY="${HOME}/.pyenv/versions/3.11.9/bin/python3"
if [[ ! -x .venv/bin/python ]]; then
  if [[ -x "$PYENV_PY" ]]; then
    "$PYENV_PY" -m venv .venv
  elif command -v python3 >/dev/null 2>&1; then
    python3 -m venv .venv
  else
    echo "No python3 found. Install Python 3.11+ or enable pyenv."
    exit 1
  fi
fi

.venv/bin/pip install -U pip
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/build_offline_panel.py

echo ""
echo "Setup done. Start the app:"
echo "  ./scripts/start.sh"
