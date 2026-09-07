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

# name -> (width, height). Landscape, because the game is landscape-only.
TARGETS = {
    "iphone-6.9": (2868, 1320),   # iPhone 16 Pro Max — required
    "ipad-13":    (2752, 2064),   # 13" iPad — required while we ship universal
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
    src = Image.open(src_path).convert("RGBA")
    tw, th = size
    scale = min(tw // src.width, th // src.height)
    if scale < 1:
        raise SystemExit("target %dx%d is smaller than the source" % size)
    game = src.resize((src.width * scale, src.height * scale), Image.NEAREST)
    canvas = Image.new("RGBA", size, BG)
    canvas.alpha_composite(game, ((tw - game.width) // 2, (th - game.height) // 2))
    return canvas, scale


def main():
    missing = [f for f, _ in PICKS if not os.path.exists(os.path.join(SRC, f))]
    if missing:
        raise SystemExit("missing source captures: %s" % ", ".join(missing))
    for device, size in TARGETS.items():
        d = os.path.join(OUT, device)
        os.makedirs(d, exist_ok=True)
        for i, (fname, label) in enumerate(PICKS, start=1):
            img, scale = compose(os.path.join(SRC, fname), size)
            out = os.path.join(d, "%02d-%s.png" % (i, label))
            img.convert("RGB").save(out, optimize=True)
        print("%-12s %4dx%-4d  %d shots at %dx integer scale"
              % (device, size[0], size[1], len(PICKS), scale))


if __name__ == "__main__":
    main()
