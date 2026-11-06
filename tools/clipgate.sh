#!/usr/bin/env bash
# The clip gate (Kaya Refit, phase 1): replay every proof tape through the
# prover's simulation, render each frame through Player's own render path, and
# fail if a single drawn pixel of Kaya lands on a solid tile.
#
#   tools/clipgate.sh                    every tape in proofs/
#   tools/clipgate.sh jungle_1 deeps_2   just these
#   tools/clipgate.sh --no-stoop         with only the stoop switched off --
#                                        a run that must FAIL
#   tools/clipgate.sh --no-pose          with every pose decision off (stoop,
#                                        swim, slung hat, nudges) -- must FAIL
#   tools/clipgate.sh --trace=N lvl      print what the decision saw on frame N
#   tools/clipgate.sh --all-forms        also gate the frog, fish and bird
#   tools/clipgate.sh --show=20          list more clips per level
#
# Exit 0 clean, 1 any clip (or a stale tape, or a tape that drew nothing).
# See tools/clipgate/clipgate.gd for exactly what "drawn" means.
set -uo pipefail
source "$(dirname "$0")/env.sh"
cd "$PROJECT_ROOT"

LOG="$(mktemp -t kaya_clipgate)"
trap 'rm -f "$LOG"' EXIT

"$GODOT" --headless --path . res://tools/clipgate/clipgate.tscn -- "$@" >"$LOG" 2>&1
CODE=$?

grep -viE 'Godot Engine v|OpenGL API|were leaked|resources still in use|^\s+at: |^$' "$LOG"
exit $CODE
