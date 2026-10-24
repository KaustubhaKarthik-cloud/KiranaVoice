#!/usr/bin/env bash
# one-command setup + run (mock mode, 0 Gnani credits)
set -e; cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate && pip install -q -r requirements.txt && python run.py --mock "$@"
