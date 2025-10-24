#!/usr/bin/env zsh
# Simple helper to activate the project's virtualenv (if present)
# and run a command inside it. Use like:
#   ./run_lotus.sh "python3 lotus/nucleus.py"

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$ROOT_DIR/venv"

if [ -d "$VENV_DIR" ]; then
  # shellcheck disable=SC1090
  source "$VENV_DIR/bin/activate"
else
  echo "Warning: no venv found at $VENV_DIR"
  echo "If you want an isolated environment, create one: python3 -m venv venv && source venv/bin/activate && pip install -r lotus/requirements.txt"
fi

if [ "$#" -eq 0 ]; then
  echo "Running nucleus by default..."
  exec python3 lotus/nucleus.py
else
  exec "$@"
fi
