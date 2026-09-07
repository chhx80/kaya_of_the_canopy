#!/usr/bin/env bash
# Structural check: scripts compile, scenes resolve, levels and data parse.
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$PROJECT_ROOT"
"$GODOT" --headless --path . --script res://tools/validate_scenes.gd "$@"
