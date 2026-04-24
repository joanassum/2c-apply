#!/bin/bash
set -e
cd "$(dirname "$0")/backend"

# find a suitable python3 (3.9+)
PYTHON=""
for cmd in python3.13 python3.12 python3.11 python3.10 python3.9 python3; do
  if command -v "$cmd" &>/dev/null; then
    PYTHON="$cmd"
    break
  fi
done

if [ -z "$PYTHON" ]; then
  echo "Error: Python 3.9+ not found. Please install Python first."
  exit 1
fi

if [ ! -f venv/bin/uvicorn ]; then
  echo "Setting up virtualenv with $PYTHON..."
  "$PYTHON" -m venv venv
  ./venv/bin/pip install -q --upgrade pip
  ./venv/bin/pip install -q -r requirements.txt
fi

if [ ! -f .env ]; then
  echo "Warning: backend/.env not found. Copying from .env.example..."
  cp .env.example .env
  echo "Edit backend/.env and set your DEEPSEEK_API_KEY, then re-run ./start.sh"
  exit 1
fi

./venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8087
