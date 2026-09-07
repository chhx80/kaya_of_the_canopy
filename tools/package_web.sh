#!/usr/bin/env bash
# Zips the web build for upload to itch.io / Netlify / any static host.
# index.html sits at the archive root, which is what itch.io requires.
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$PROJECT_ROOT"

tools/export_web.sh >/dev/null
OUT="build/kaya-web.zip"
rm -f "$OUT"
(cd build/web && zip -qr "../../$OUT" .)
echo "packaged $OUT ($(du -h "$OUT" | cut -f1))"
echo
echo "itch.io: new project > Kind: HTML > upload this zip > tick 'This file will be played in the browser'"
echo "         viewport 1280x768, tick 'Fullscreen button', set visibility to Restricted for a private playtest"
