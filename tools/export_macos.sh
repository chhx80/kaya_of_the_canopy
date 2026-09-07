#!/usr/bin/env bash
# macOS build. Unsigned by default; set codesign/notarization in the preset for
# a distributable build.
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$PROJECT_ROOT"
mkdir -p build/macos
"$GODOT" --headless --path . --export-release "macOS" build/macos/KayaOfTheCanopy.zip
echo "built build/macos/KayaOfTheCanopy.zip"
