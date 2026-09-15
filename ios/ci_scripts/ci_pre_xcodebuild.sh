#!/usr/bin/env bash
# Reassembles the Godot engine XCFrameworks from the compressed copies in
# ios/frameworks/.
#
# Why compressed: libgodot.a is 180 MB for the device slice, past GitHub's
# 100 MB per-file limit. xz gets it to 25 MB.
#
# Why .tar.xz and not raw .xz: the standalone `xz` binary is NOT part of macOS —
# it comes from Homebrew, and it is absent on the Xcode Cloud image. The first
# version of this script used `xz -dc` and died with exit 127, "command not
# found". macOS `tar` is bsdtar with liblzma compiled in, so `tar -xJf` works
# with nothing but /usr/bin. Verified by extracting under `env -i PATH=/usr/bin:/bin`.
#
# Device slice only: an archive targets generic/platform=iOS and never needs the
# simulator.
set -euo pipefail
REPO_ROOT="${CI_PRIMARY_REPOSITORY_PATH:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$REPO_ROOT"

command -v tar >/dev/null 2>&1 || { echo "error: no tar on PATH" >&2; exit 1; }

unpack() {  # <framework> <tar.xz> <plist> <libname>
  local fw="ios/$1.xcframework"
  local src="ios/frameworks/$2" plist="ios/frameworks/$3"
  [ -f "$src" ] || { echo "error: missing $src" >&2; exit 1; }
  [ -f "$plist" ] || { echo "error: missing $plist" >&2; exit 1; }
  rm -rf "$fw"
  mkdir -p "$fw/ios-arm64"
  cp "$plist" "$fw/Info.plist"
  tar -xJf "$src" -C "$fw/ios-arm64"
  [ -f "$fw/ios-arm64/$4" ] || { echo "error: $4 not extracted from $src" >&2; exit 1; }
  echo "    $fw  ($(du -h "$fw/ios-arm64/$4" | cut -f1))"
}

echo "--- reassembling XCFrameworks with $(tar --version 2>&1 | head -1)"
unpack KayaOfTheCanopy libgodot.device.tar.xz    KayaOfTheCanopy.Info.plist libgodot.a
unpack MoltenVK        libMoltenVK.device.tar.xz MoltenVK.Info.plist        libMoltenVK.a
echo "--- ready"
