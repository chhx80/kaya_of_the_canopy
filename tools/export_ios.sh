#!/usr/bin/env bash
# iOS: exports an Xcode project you then build/archive in Xcode.
#
# Prerequisites: macOS with Xcode, and an Apple Developer team id filled into
# `application/app_store_team_id` in export_presets.cfg (left blank here on
# purpose — it is account-specific).
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$PROJECT_ROOT"

if ! xcode-select -p >/dev/null 2>&1; then
  echo "error: Xcode command line tools not found." >&2
  exit 1
fi
if ! grep -q 'app_store_team_id="[^"]\+"' export_presets.cfg; then
  echo "error: application/app_store_team_id is blank in export_presets.cfg." >&2
  echo "       It is account-specific, so it is deliberately not committed." >&2
  echo "       Find it at developer.apple.com > Membership, then set it and re-run." >&2
  exit 1
fi

rm -rf build/ios
mkdir -p build/ios
"$GODOT" --headless --path . --export-release "iOS" build/ios/KayaOfTheCanopy.xcodeproj
# Godot writes its own required-reason manifest; ours documents the game's
# position (it collects nothing) and rides along in the bundle.
cp export/PrivacyInfo.xcprivacy build/ios/ 2>/dev/null || true
echo "built build/ios — open the .xcodeproj, set your team, then Product > Archive"
