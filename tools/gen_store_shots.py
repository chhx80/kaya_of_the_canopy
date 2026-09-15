#!/usr/bin/env python3
"""Composes App Store screenshots at Apple's exact required pixel sizes.

Apple requires 6.9" iPhone and 13" iPad screenshots for a universal app, at
precise dimensions. The game renders 400x240 integer-scaled and pillarboxed, so
each screenshot is the source capture scaled by the largest whole number that
fits, centred on the same near-black the game letterboxes with. That is exactly
what the device shows, so the store page does not promise a framing the player
will not get.

Run with tools/genstoreshots.sh.
"""
import os, sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "shots")
OUT = os.path.join(ROOT, "export", "store")

# name -> (store size, capture subdirectory). Landscape; the game is
# landscape-only. Captures are taken at each device's ASPECT so the screenshot
# shows the real layout — full-bleed game with the touch controls out in the
# margin — rather than a pillarboxed 400x240 that no device actually renders.
TARGETS = {
    "iphone-6.9": ((2868, 1320), "phone"),   # 19.5:9 -> 522x240 logical
    "ipad-13":    ((2752, 2064), "tablet"),  # 4:3    -> 400x300 logical
}

# Order matters: this is the order they appear on the store page.
# Captured by tools/seq/store_shots.json with the touch overlay forced on, so
# the store page shows the controls an iPhone player actually gets.
PICKS = [
    ("store_01_title.png",       "title"),
    ("store_02_platforming.png", "platforming"),
    ("store_03_boss.png",        "boss"),
    ("store_04_fish.png",        "fish-form"),
    ("store_05_hub.png",         "hub"),
]

BG = (13, 11, 15, 255)   # the palette's near-black, same as the letterbox


def compose(src_path, size):
    """The capture already has the device's aspect, so this only scales it up.
    Nearest-neighbour keeps the pixels hard; any sub-percent aspect difference
    between the capture and Apple's exact pixel size is invisible."""
    src = Image.open(src_path).convert("RGBA")
    scale = size[1] / src.height
    return src.resize(size, Image.NEAREST), scale


def main():
    for device, (size, sub) in TARGETS.items():
        d = os.path.join(OUT, device)
        os.makedirs(d, exist_ok=True)
        for i, (fname, label) in enumerate(PICKS, start=1):
            cap = os.path.join(SRC, sub, fname)
            if not os.path.exists(cap):
                raise SystemExit("missing %s — run tools/genstoreshots.sh, which "
                                 "captures per device aspect" % cap)
            img, scale = compose(cap, size)
            out = os.path.join(d, "%02d-%s.png" % (i, label))
            img.convert("RGB").save(out, optimize=True)
        print("%-12s %4dx%-4d  %d shots from %s captures (%.2fx)"
              % (device, size[0], size[1], len(PICKS), sub, scale))


if __name__ == "__main__":
    main()
