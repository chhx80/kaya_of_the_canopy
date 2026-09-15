#!/usr/bin/env bash
# Structural check: scripts compile, scenes resolve, levels and data parse.
set -uo pipefail
source "$(dirname "$0")/env.sh"
cd "$PROJECT_ROOT"
"$GODOT" --headless --path . --script res://tools/validate_scenes.gd "$@"
GODOT_RC=$?

# Structural validity is not the same as being playable. This walks each level
# from its spawn using the real jump envelope from data/forms/*.json -- including
# form changes at transform pads -- and fails if anything you must touch is
# unreachable. Three of five levels were uncompletable when it was first run.
"$PYVENV" tools/reachability.py
REACH_RC=$?

[ "$GODOT_RC" -ne 0 ] && exit "$GODOT_RC"
exit "$REACH_RC"
