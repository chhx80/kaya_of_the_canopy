#!/usr/bin/env bash
# tools/grid.sh out.png cols scale shot1.png shot2.png ...
set -euo pipefail
source "$(dirname "$0")/env.sh"
"$PYVENV" - "$@" <<'PY'
import sys
from PIL import Image
out_path, cols, scale = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
paths = sys.argv[4:]
ims = [Image.open(p).convert("RGBA") for p in paths]
w, h = ims[0].width * scale, ims[0].height * scale
rows = (len(ims) + cols - 1) // cols
out = Image.new("RGBA", (cols * (w + 8) + 8, rows * (h + 8) + 8), (18, 20, 26, 255))
for i, im in enumerate(ims):
    out.alpha_composite(im.resize((w, h), Image.NEAREST),
                        (8 + (i % cols) * (w + 8), 8 + (i // cols) * (h + 8)))
out.save(out_path)
print(out_path)
PY
