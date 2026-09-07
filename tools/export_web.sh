#!/usr/bin/env bash
# Web build — the fastest way to put the game in front of a playtester.
# Output: build/web/  (serve it, don't open index.html from file://)
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$PROJECT_ROOT"
mkdir -p build/web
"$GODOT" --headless --path . --export-release "Web" build/web/index.html
echo "built build/web — serve with:  python3 -m http.server -d build/web 8080"
