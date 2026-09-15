#!/usr/bin/env bash
# Reassembles the Godot engine XCFrameworks from the compressed copies in
# ios/frameworks/.
#
# Why they are compressed: libgodot.a is 180 MB for the device slice, past
# GitHub's 100 MB hard per-file limit. xz gets it to 25 MB, so it fits and the
# build no longer has to download 1.3 GB of Godot to reconstruct it.
#
# Device slice only — an archive builds for `generic/platform=iOS` and never
# needs the simulator, which would double the payload for nothing.
set -euo pipefail
REPO_ROOT="${CI_PRIMARY_REPOSITORY_PATH:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$REPO_ROOT"

unpack() {  # <framework-name> <xz-file> <plist>
  local fw="ios/$1.xcframework" xz="ios/frameworks/$2" plist="ios/frameworks/$3"
  [ -f "$xz" ] || { echo "error: missing $xz" >&2; exit 1; }
  rm -rf "$fw"
  mkdir -p "$fw/ios-arm64"
  cp "$plist" "$fw/Info.plist"
  xz -dc "$xz" > "$fw/ios-arm64/$4"
  echo "   $fw  ($(du -h "$fw/ios-arm64/$4" | cut -f1))"
}

echo "--- reassembling XCFrameworks"
unpack KayaOfTheCanopy libgodot.device.a.xz   KayaOfTheCanopy.Info.plist libgodot.a
unpack MoltenVK        libMoltenVK.device.a.xz MoltenVK.Info.plist       libMoltenVK.a

for FW in ios/KayaOfTheCanopy.xcframework ios/MoltenVK.xcframework; do
  [ -d "$FW" ] || { echo "error: $FW not assembled" >&2; exit 1; }
done
echo "--- ready"
