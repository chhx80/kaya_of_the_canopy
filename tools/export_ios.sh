#!/usr/bin/env bash
# iOS: exports an Xcode project you then run on a device and archive in Xcode.
#
# Godot also *attempts* an xcodebuild archive at the end of the export. That
# step needs a signing certificate in your keychain, so it fails on a machine
# where Xcode has not been signed into a developer account yet. The Xcode
# project is fully written before that happens, which is all we actually need —
# so this script checks for the project rather than trusting Godot's exit code.
#
# Prerequisites: macOS with Xcode, and application/app_store_team_id set in
# export_presets.cfg (see docs/shipping.md).
set -uo pipefail
source "$(dirname "$0")/env.sh"
cd "$PROJECT_ROOT"

if ! xcode-select -p >/dev/null 2>&1; then
  echo "error: Xcode command line tools not found." >&2
  exit 1
fi
if ! grep -q 'app_store_team_id="[^"]\+"' export_presets.cfg; then
  echo "error: application/app_store_team_id is blank in export_presets.cfg." >&2
  echo "       Find it at developer.apple.com > Membership, then set it." >&2
  exit 1
fi

IDENTITIES="$(security find-identity -v -p codesigning 2>/dev/null | grep -c 'valid identities found' || true)"
if security find-identity -v -p codesigning 2>/dev/null | grep -q '0 valid identities'; then
  echo "note: no code signing identities in your keychain yet."
  echo "      The Xcode project will still be generated; signing happens in Xcode."
  echo "      Xcode > Settings > Accounts > (your Apple ID) > Manage Certificates > + > Apple Development"
  echo
fi

rm -rf build/ios
mkdir -p build/ios
"$GODOT" --headless --path . --export-release "iOS" build/ios/KayaOfTheCanopy.xcodeproj \
  >/tmp/kaya_ios_export.log 2>&1
GODOT_CODE=$?

PROJ="build/ios/KayaOfTheCanopy.xcodeproj/project.pbxproj"
if [ ! -f "$PROJ" ]; then
  echo "error: no Xcode project was produced. Godot said:" >&2
  grep -E '^(ERROR|error:)' /tmp/kaya_ios_export.log | head -10 >&2
  exit 1
fi

# Godot's own required-reason manifest is generated separately; ours documents
# the game's position (it collects nothing) and rides along in the bundle.
cp export/PrivacyInfo.xcprivacy build/ios/ 2>/dev/null || true

echo "built build/ios/KayaOfTheCanopy.xcodeproj"
if [ "$GODOT_CODE" -ne 0 ]; then
  echo
  echo "Godot's optional archive step did not complete (exit $GODOT_CODE)."
  echo "That is expected without a signing certificate — archive in Xcode instead:"
fi
echo
echo "  open build/ios/KayaOfTheCanopy.xcodeproj"
echo "  target > Signing & Capabilities > Automatically manage signing > pick your team"
echo "  Cmd-R to run on a connected iPhone, then Product > Archive to ship"
