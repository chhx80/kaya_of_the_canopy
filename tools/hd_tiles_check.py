#!/usr/bin/env python3
"""Check the shipped 2x tileset against the H0 one it replaces.

    $PYVENV tools/hd_tiles_check.py <old tileset.png>

  * every cell of a NATIVE id (its gameplay cell, every variant and decoration
    cell variants.json gives it) must differ from the old, nearest-doubled
    cell -- a lazy double fails;
  * every other cell must be byte-identical to the old one -- a world that has
    not been redrawn must ship exactly as before.

Exit 1 on either failure. Get the old sheet with
`git show <base>:assets/tiles/tileset.png > /tmp/old.png`.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image  # noqa: E402

from art import hd_tilekit as hd, palette, tiles  # noqa: E402,F401


def main():
    old = Image.open(sys.argv[1]).convert("RGBA")
    new = Image.open(os.path.join(palette.TILES, "tileset.png")).convert("RGBA")
    with open(os.path.join(palette.TILES, "variants.json")) as f:
        v = json.load(f)
    n = hd.N
    native = {i for i in range(len(tiles.TILE_DEFS)) if hd.is_native(i)}
    for tid, rec in v["tiles"].items():
        if hd.is_native(int(tid)):
            for ids in rec["cases"].values():
                native.update(ids)
            native.update(d["index"] for d in rec["decor"])
    if old.size != new.size:
        print("FAIL atlas size %s -> %s" % (old.size, new.size))
        return 1
    lazy, moved = [], []
    cols = new.width // n
    for c in range(cols * (new.height // n)):
        box = ((c % cols) * n, (c // cols) * n, (c % cols) * n + n, (c // cols) * n + n)
        a, b = old.crop(box).tobytes(), new.crop(box).tobytes()
        if c in native:
            if a == b and any(b[3::4]):
                lazy.append(c)
        elif a != b:
            moved.append(c)
    print("%d cells: %d native, %d lazy doubles, %d non-native cells changed"
          % (cols * (new.height // n), len(native), len(lazy), len(moved)))
    if lazy:
        print("FAIL lazy:", lazy[:40])
    if moved:
        print("FAIL changed though not native:", moved[:40])
    return 1 if (lazy or moved) else 0


if __name__ == "__main__":
    sys.exit(main())
