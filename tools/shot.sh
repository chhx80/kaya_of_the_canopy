#!/usr/bin/env bash
# Drives the real game and writes PNGs. Examples:
#   tools/shot.sh --scenario=title --out=shots/01_title.png --frames=40
#   tools/shot.sh --seq=tools/seq/level1.json
# --res=WxH sets the WINDOW size, which decides the device aspect and therefore
# how wide the root viewport becomes. Default is the game's own 5:3, i.e. no
# margins; pass a phone or tablet aspect to see the real device layout.
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$PROJECT_ROOT"
RES="1200x720"
ARGS=()
for a in "$@"; do
  case "$a" in
    --res=*) RES="${a#--res=}" ;;
    *) ARGS+=("$a") ;;
  esac
done
"$GODOT" --path . --rendering-driver opengl3 --resolution "$RES" -- "${ARGS[@]}" 2>&1 \
  | grep -viE 'Godot Engine v|OpenGL API|^$' || true
