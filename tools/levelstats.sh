#!/usr/bin/env bash
# Per-level metrics from the level JSON and its proof tape: tiles, screens,
# route seconds, hops, checkpoints and the longest stretch between them,
# enemies (and per route-minute), hazard tiles near the route, forms, pickups.
# How the 5x length target and the difficulty curve are held
# (docs/plan-longer-levels.md). Usage and exit codes:
# tools/levelstats/levelstats_runner.gd.
#
#   tools/levelstats.sh [level-id ...] [--level-file=res://...] [--json] [--strict]
set -uo pipefail
source "$(dirname "$0")/env.sh"
cd "$PROJECT_ROOT"

LOG="$(mktemp -t kaya_levelstats)"
trap 'rm -f "$LOG"' EXIT
"$GODOT" --headless --path . res://tools/levelstats/levelstats.tscn -- "$@" >"$LOG" 2>&1
CODE=$?
grep -viE 'Godot Engine v|OpenGL API|were leaked|resources still in use|^\s+at: |^$' "$LOG"
exit $CODE
