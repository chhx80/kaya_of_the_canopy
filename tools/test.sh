#!/usr/bin/env bash
# Runs the headless unit suite. Exit code is the gate.
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$PROJECT_ROOT"
"$GODOT" --headless --path . --script res://tests/run_tests.gd "$@"
