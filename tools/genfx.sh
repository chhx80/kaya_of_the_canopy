#!/usr/bin/env bash
# Regenerates the Phase 5 FX art (particles + animated tile frames).
# The tile frames are derived from assets/tiles/tileset.png, so run this AFTER
# tools/genart.sh whenever the tileset is repainted.
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$PROJECT_ROOT"
"$PYVENV" tools/gen_fx.py
tools/import.sh
