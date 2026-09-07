#!/usr/bin/env bash
# Re-imports assets so freshly generated PNGs get .import files.
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$PROJECT_ROOT"
"$GODOT" --headless --path . --import 2>&1 | grep -viE '^$|Godot Engine|OpenGL|Vulkan' || true
