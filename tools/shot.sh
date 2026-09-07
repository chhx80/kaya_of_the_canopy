#!/usr/bin/env bash
# Drives the real game and writes PNGs. Examples:
#   tools/shot.sh --scenario=title --out=shots/01_title.png --frames=40
#   tools/shot.sh --seq=tools/seq/level1.json
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$PROJECT_ROOT"
"$GODOT" --path . --rendering-driver opengl3 --resolution 400x240 -- "$@" 2>&1 \
  | grep -viE 'Godot Engine v|OpenGL API|^$' || true
