#!/usr/bin/env bash
# Nearest-neighbour upscale of a 400x240 capture for human review.
set -euo pipefail
source "$(dirname "$0")/env.sh"
"$PYVENV" - "$@" <<'PY'
import sys
from PIL import Image
src = sys.argv[1]
dst = sys.argv[2] if len(sys.argv) > 2 else src.replace(".png", "_x3.png")
scale = int(sys.argv[3]) if len(sys.argv) > 3 else 3
im = Image.open(src)
im.resize((im.width * scale, im.height * scale), Image.NEAREST).save(dst)
print(dst)
PY
