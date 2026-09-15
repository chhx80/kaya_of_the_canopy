#!/usr/bin/env bash
# Xcode Cloud post-clone hook.
#
# The Godot engine static libraries are 180 MB and 167 MB — past GitHub's 100 MB
# hard limit — so they are NOT in the repo. Neither is anything else Godot
# generates. This regenerates the whole iOS export on the build machine, which
# also guarantees the .pck matches the committed game data rather than whatever
# was last exported by hand.
set -euo pipefail

GODOT_VERSION="4.7.2-stable"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "--- installing Godot $GODOT_VERSION"
curl -fL -sS -o /tmp/godot.zip \
  "https://github.com/godotengine/godot/releases/download/${GODOT_VERSION}/Godot_v${GODOT_VERSION}_macos.universal.zip"
unzip -qo /tmp/godot.zip -d /tmp/godot
GODOT="/tmp/godot/Godot.app/Contents/MacOS/Godot"
chmod +x "$GODOT"

echo "--- installing export templates"
curl -fL -sS -o /tmp/templates.tpz \
  "https://github.com/godotengine/godot/releases/download/${GODOT_VERSION}/Godot_v${GODOT_VERSION}_export_templates.tpz"
unzip -qo /tmp/templates.tpz -d /tmp/tpl
TPL_DIR="$HOME/Library/Application Support/Godot/export_templates/${GODOT_VERSION/-stable/.stable}"
mkdir -p "$TPL_DIR"
cp -f /tmp/tpl/templates/* "$TPL_DIR"/

echo "--- importing project"
"$GODOT" --headless --path . --import >/dev/null 2>&1 || true

echo "--- exporting iOS project over ios/"
# Godot also attempts an archive at the end; it has no signing identity here and
# Xcode Cloud does the signing itself, so its exit code is not the gate — the
# presence of the project is.
"$GODOT" --headless --path . --export-release "iOS" ios/KayaOfTheCanopy.xcodeproj \
  >/tmp/ios_export.log 2>&1 || true

if [ ! -f ios/KayaOfTheCanopy.xcodeproj/project.pbxproj ]; then
  echo "error: no Xcode project produced" >&2
  grep -E '^(ERROR|error:)' /tmp/ios_export.log | head -20 >&2
  exit 1
fi

# Never let a packaging log reach an artefact; it carries live Apple auth headers.
find ios -name '*.log' -delete
cp -f export/PrivacyInfo.xcprivacy ios/ 2>/dev/null || true

echo "--- ready: $(find ios -type f | wc -l | tr -d ' ') files"
