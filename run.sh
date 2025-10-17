#!/usr/bin/env bash
set -e

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate

##pip install --upgrade pip
##pip install -r install/requirements.txt

export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

if [ -f ".env" ]; then
  set -a
  . ./.env
  set +a
fi

exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8010}" --reload
