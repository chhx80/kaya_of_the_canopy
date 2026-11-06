#!/usr/bin/env python3
"""Kaya Refit phase 3, tiles: the before/after sheet and the hat measurement.

    tools/p3_tiles_sheets.py kaya     shots/p3_tiles_kaya_sheet.png + the table
    tools/p3_tiles_sheets.py legend   shots/p3_tiles_legibility_<world>.png

`kaya` reads the in-game captures that tools/seq/p3_tiles_kaya_{before,after}
.json write: the same scenario and the same frame count, once against the
tile art at HEAD and once against this branch's, so the only thing that differs
between a pair is the tiles. It finds Kaya's hat by its exact `straw` colours
(entities are drawn untinted), and measures the scenery in a ring 3-5 px
outside it: how far the hat stands above what surrounds it, in luma and in
saturation. That is the number the THERMAL HEIGHTS brief named.

`legend` is the legibility sheet: every gameplay role of a world side by side
on that world's own background wall, at 1x and 3x, composited from the real
atlas, the real variant resolution and the real ambient tints — see
`_compose()` for what it does and does not reproduce of the engine.
"""
import colorsys
import json
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from art import palette, tiles  # noqa: E402

SHOTS = os.path.join(ROOT, "shots")
WORLDS = ["jungle", "ruins", "heights", "deeps", "nest"]
BG = (18, 20, 26, 255)
TEXT = (232, 200, 120, 255)


def luma(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def sat(c):
    return colorsys.rgb_to_hsv(*[v / 255.0 for v in c[:3]])[1]


# ---------------------------------------------------------------- kaya
def hat_ring(img):
    """(hat pixels, ring pixels) — the ring is scenery 3-5 px from the hat."""
    px = img.load()
    straw = {tuple(c) for c in palette.RAMPS["straw"]}
    w, h = img.size
    hat = [(x, y) for y in range(h) for x in range(w) if px[x, y][:3] in straw]
    if not hat:
        return [], []
    xs = [p[0] for p in hat]
    ys = [p[1] for p in hat]
    cx = sorted(xs)[len(xs) // 2]
    cy = sorted(ys)[len(ys) // 2]
    # only the hat nearest the median: ignore anything straw-coloured elsewhere
    hat = [p for p in hat if abs(p[0] - cx) < 16 and abs(p[1] - cy) < 10]
    hs = set(hat)
    ring = set()
    for (x, y) in hat:
        for dy in range(-5, 6):
            for dx in range(-5, 6):
                d = max(abs(dx), abs(dy))
                if 3 <= d <= 5 and 0 <= x + dx < w and 0 <= y + dy < h:
                    ring.add((x + dx, y + dy))
    # Kaya herself (hair, face, ink) is not scenery: drop every pixel that is
    # one of her own ramps' colours.
    own = {tuple(c) for r in ("hair", "skin", "straw", "cloth") for c in palette.RAMPS[r]}
    own.add(palette.INK)
    ring = [p for p in ring if p not in hs and px[p][:3] not in own]
    return [px[p] for p in hat], [px[p] for p in ring]


def measure(path):
    img = Image.open(path).convert("RGB")
    hat, ring = hat_ring(img)
    if not hat or not ring:
        return None
    hl = sum(luma(c) for c in hat) / len(hat)
    rl = sum(luma(c) for c in ring) / len(ring)
    hs = sum(sat(c) for c in hat) / len(hat)
    rs = sum(sat(c) for c in ring) / len(ring)
    return dict(hat_l=hl, ring_l=rl, dl=hl - rl, hat_s=hs, ring_s=rs,
                ds=hs - rs)


def crop_kaya(path, scale=4, w=72, h=60):
    img = Image.open(path).convert("RGBA")
    hat, _ = hat_ring(img.convert("RGB"))
    px = img.convert("RGB").load()
    straw = {tuple(c) for c in palette.RAMPS["straw"]}
    pts = [(x, y) for y in range(img.height) for x in range(img.width)
           if px[x, y] in straw]
    if pts:
        xs = sorted(p[0] for p in pts)
        ys = sorted(p[1] for p in pts)
        cx, cy = xs[len(xs) // 2], ys[len(ys) // 2] + 18
    else:
        cx, cy = img.width // 2, img.height // 2
    box = (cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2)
    return img.crop(box).resize((w * scale, h * scale), Image.NEAREST)


def kaya_sheet():
    rows = []
    table = []
    for world in WORLDS:
        for pose in ("idle", "run"):
            b = os.path.join(SHOTS, "p3_tiles_kaya_before_%s_%s.png" % (world, pose))
            a = os.path.join(SHOTS, "p3_tiles_kaya_after_%s_%s.png" % (world, pose))
            if not (os.path.exists(a) and os.path.exists(b)):
                continue
            mb, ma = measure(b), measure(a)
            table.append((world, pose, mb, ma))
            if pose == "idle":
                rows.append((world, b, a, mb, ma))
    cw, ch = 72 * 4, 60 * 4
    fw, fh = 400, 240
    W = 8 + (cw + 8) * 2 + (fw + 8) * 2
    H = 28 + len(rows) * (max(ch, fh) + 26)
    out = Image.new("RGBA", (W, H), BG)
    d = ImageDraw.Draw(out)
    d.text((8, 8), "Kaya over each tileset, BEFORE | AFTER the phase 3 tile pass "
           "(4x crops, then the full in-game frame at 1x). Same scenario, same "
           "frame: only the tiles differ.", fill=TEXT)
    y = 28
    for world, b, a, mb, ma in rows:
        x = 8
        for p, tag, m in ((b, "before", mb), (a, "after", ma)):
            out.alpha_composite(crop_kaya(p), (x, y + 14))
            label = "%s %s" % (world, tag)
            if m:
                label += "   hat-surround %+.0f luma, %+.2f sat" % (m["dl"], m["ds"])
            d.text((x, y), label, fill=TEXT)
            x += cw + 8
        for p in (b, a):
            out.alpha_composite(Image.open(p).convert("RGBA"), (x, y + 14))
            x += fw + 8
        y += max(ch, fh) + 26
    path = os.path.join(SHOTS, "p3_tiles_kaya_sheet.png")
    out.save(path)
    print(path)
    print("\nhat minus surround: luma and saturation\n%-8s %-5s %24s %24s"
          % ("world", "pose", "before (dL dS)", "after (dL dS)"))
    for world, pose, mb, ma in table:
        def f(m):
            if not m:
                return "%24s" % "no hat found"
            return "%24s" % ("%+6.1f %+5.2f" % (m["dl"], m["ds"]))
        print("%-8s %-5s %s %s" % (world, pose, f(mb), f(ma)))


# -------------------------------------------------------------- legend
if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "kaya"
    if what == "kaya":
        kaya_sheet()
    elif what == "legend":
        import p3_tiles_legend
        p3_tiles_legend.main()
