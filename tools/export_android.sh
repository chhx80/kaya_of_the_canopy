#!/usr/bin/env bash
# Android APK.
#
# Prerequisites (not installed on this machine — see docs/shipping.md):
#   * JDK 17
#   * Android SDK with build-tools 34 and platform-tools
#   * A debug/release keystore configured in Godot's editor settings, or via
#     the env vars below.
#
# Set these before running:
#   export GODOT_ANDROID_KEYSTORE=/path/to/release.keystore
#   export GODOT_ANDROID_KEYSTORE_USER=alias
#   export GODOT_ANDROID_KEYSTORE_PASS=...
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$PROJECT_ROOT"

if ! command -v javac >/dev/null 2>&1; then
  echo "error: no JDK on PATH. Install JDK 17 (brew install --cask temurin17)." >&2
  exit 1
fi
if [ -z "${ANDROID_HOME:-}" ] && [ ! -d "$HOME/Library/Android/sdk" ]; then
  echo "error: Android SDK not found. Install it and export ANDROID_HOME." >&2
  exit 1
fi

mkdir -p build/android
MODE="${1:-release}"
if [ "$MODE" = "debug" ]; then
  "$GODOT" --headless --path . --export-debug "Android" build/android/KayaOfTheCanopy-debug.apk
else
  "$GODOT" --headless --path . --export-release "Android" build/android/KayaOfTheCanopy.apk
fi
echo "built build/android/"
