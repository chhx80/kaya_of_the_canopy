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

# --- Xcode SDK check -------------------------------------------------------
# Godot 4.7.2's iOS *device* library is built against the iOS 26.1 SDK and
# references symbols that do not exist in older ones (_CADynamicRange*,
# _MTLTensorDomain). Linking against an older SDK fails with a wall of
# "Undefined symbol" errors at the very end of an Xcode build.
#
# The *simulator* slice does not reference those symbols, so a simulator build
# succeeds on an older Xcode and tells you nothing. Check explicitly.
REQUIRED_SDK="26.1"
HAVE_SDK="$(xcodebuild -showsdks 2>/dev/null | sed -n 's/.*-sdk iphoneos\([0-9.]*\).*/\1/p' | sort -V | tail -1)"
if [ -z "$HAVE_SDK" ]; then
  echo "error: no iOS SDK found. Install Xcode from the App Store." >&2
  exit 1
fi
if [ "$(printf '%s\n%s\n' "$REQUIRED_SDK" "$HAVE_SDK" | sort -V | head -1)" != "$REQUIRED_SDK" ]; then
  echo "error: your iOS SDK is $HAVE_SDK, but Godot 4.7.2's device template needs $REQUIRED_SDK or newer." >&2
  echo "       Building for a device will fail at link time with:" >&2
  echo "         Undefined symbol: _CADynamicRangeAutomatic  (and friends)" >&2
  echo "         Undefined symbol: _MTLTensorDomain" >&2
  echo "       Update Xcode, then re-run. See docs/shipping.md." >&2
  echo "       (A simulator build would still succeed — that slice does not use those symbols.)" >&2
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

# Godot 4.7.2 ships an x86_64-only simulator library while advertising arm64,
# so the Simulator cannot link on Apple Silicon. Say so before someone tries.
SIM_LIB="build/ios/KayaOfTheCanopy.xcframework/ios-arm64_x86_64-simulator/libgodot.a"
if [ -f "$SIM_LIB" ] && ! lipo -archs "$SIM_LIB" 2>/dev/null | grep -q arm64; then
  echo
  echo "note: use a physical device, not the Simulator."
  echo "      Godot's simulator library is x86_64-only ($(lipo -archs "$SIM_LIB" 2>/dev/null))"
  echo "      although its Info.plist claims arm64, so a Simulator build fails with"
  echo "      \"Undefined symbols for architecture arm64: _main\". See docs/shipping.md."
fi
