#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$PROJECT_ROOT"
"$PYVENV" tools/gen_store_shots.py
