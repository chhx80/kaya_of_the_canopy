#!/usr/bin/env bash
# Playtest build: the same game, but with tools/ and tests/ included so the
# capture harness and integration suite can run against a *packaged* build.
# Never ship this preset — it carries the dev harness.
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$PROJECT_ROOT"
mkdir -p build/playtest
"$GODOT" --headless --path . --export-release "macOS Playtest" build/playtest/KayaPlaytest.zip
rm -rf build/playtest/app && mkdir -p build/playtest/app
unzip -qo build/playtest/KayaPlaytest.zip -d build/playtest/app
xattr -dr com.apple.quarantine build/playtest/app 2>/dev/null || true
echo "built build/playtest/app"
