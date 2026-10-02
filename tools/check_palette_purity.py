#!/usr/bin/env python3
"""Phase E, docs/plan-art-motion.md: consistency sweep, "ramp purity" half.

Walks every opaque pixel of the generated sheets that are supposed to be pure
ramp output — the tileset, every character sprite sheet (selout or not), the
four small icon sheets, and the two FX atlases — and checks it against
`assets/palette.json`'s ramps plus ink. Dithering never fails this: `dither()`
interleaves two REAL ramp colours pixel by pixel, so every individual pixel is
still a ramp step; "dithered pairs are legal by construction" falls out of
checking pixels rather than regions.

What is deliberately NOT scanned, and why (the same exclusions
`tests/test_art_palette.gd` already carries for the sheets it covers,
extended here to the newer generators):

  - `bg_*_{sky,far,near,fg}.png` (parallax backdrops) and `light_pool.png` /
    `vignette.png` — phase 3/C's own call: these blend and dither continuous
    falloffs rather than index discrete ramp steps, by design.
  - `font8.png`, `logo.png`, `title_bg.png`, `icon.png`, `splash.png`,
    `icon_*.png` (store icons) — presentation chrome, never drawn over
    gameplay, not part of the ramp contract any sprite or tile makes.

Usage:  tools/env.sh's PYVENV check_palette_purity.py [--fix]

Without --fix: report every off-palette colour found, per file, and exit
non-zero if any sheet this project's own generators are supposed to keep pure
(the tileset, the character sheets, the icon sheets) has one. FX sheets are
reported but never fail the run — see the note on `FX_SHEETS` below.

With --fix: nothing in this script writes pixels. "Fix" in the plan's docket
item means edit the generator's source values and re-run tools/genart.sh /
tools/genfx.sh — a checker that silently rewrites pixels could paper over the
exact drift it exists to catch. --fix just prints the one-line diagnosis for
each violation found, to point at what to edit.
"""
import json
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPRITES = os.path.join(ROOT, "assets", "sprites")
TILES = os.path.join(ROOT, "assets", "tiles")
FX = os.path.join(SPRITES, "fx")

# Sheets the gen_art.py pipeline builds purely out of ramp steps (dither(),
# auto_shade(), lit()) — any off-palette pixel here is a real defect.
STRICT_SHEETS = [
    os.path.join(TILES, "tileset.png"),
    os.path.join(SPRITES, "kaya_human.png"),
    os.path.join(SPRITES, "kaya_frog.png"),
    os.path.join(SPRITES, "kaya_fish.png"),
    os.path.join(SPRITES, "kaya_bird.png"),
    os.path.join(SPRITES, "enemy_walker.png"),
    os.path.join(SPRITES, "enemy_jumper.png"),
    os.path.join(SPRITES, "enemy_shooter.png"),
    os.path.join(SPRITES, "enemy_swimmer.png"),
    os.path.join(SPRITES, "enemy_charger.png"),
    os.path.join(SPRITES, "enemy_dropper.png"),
    os.path.join(SPRITES, "enemy_flyer.png"),
    os.path.join(SPRITES, "boss_grove.png"),
    os.path.join(SPRITES, "boss_stormcrest.png"),
    os.path.join(SPRITES, "boss_tide_maw.png"),
    os.path.join(SPRITES, "boss_brood_queen.png"),
    os.path.join(SPRITES, "boss_obsidian_heart.png"),
    os.path.join(SPRITES, "blade.png"),
    os.path.join(SPRITES, "pickups.png"),
    os.path.join(SPRITES, "props.png"),
    os.path.join(SPRITES, "projectiles.png"),
]

# gen_fx.py is a second, independent pipeline (tools/gen_fx.py's own
# docstring: "Particles are deliberately near-monochrome... so they survive
# any repaint of the tiles underneath them") with a hand-authored PAL dict,
# not palette.py's ramps, PLUS continuous brightness scaling (scale()) for
# the water sparkle / lava glow animation. Both are intentional: reported for
# visibility (a checker that only ever says "fine" on a file nobody looks at
# again is not a checker), never a failure.
FX_SHEETS = [
    os.path.join(FX, "particles.png"),
    os.path.join(FX, "tile_anim.png"),
]


def load_allowed():
    pal = json.load(open(os.path.join(ROOT, "assets", "palette.json")))
    allowed = set()
    for steps in pal["ramps"].values():
        for c in steps:
            allowed.add(tuple(c))
    allowed.add(tuple(pal["ink"]))
    return allowed


def scan(path, allowed):
    """-> {offending_rgb: pixel_count}, or None if the file does not exist."""
    if not os.path.exists(path):
        return None
    img = Image.open(path).convert("RGBA")
    bad = {}
    w, h = img.size
    px = img.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            rgb = (r, g, b)
            if rgb not in allowed:
                bad[rgb] = bad.get(rgb, 0) + 1
    return bad


def nearest(rgb, allowed):
    def d2(a, b):
        return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2
    best = min(allowed, key=lambda c: d2(c, rgb))
    return best, d2(best, rgb) ** 0.5


def report(sheets, allowed, strict):
    total_bad_files = 0
    rows = []
    for path in sheets:
        name = os.path.relpath(path, ROOT)
        bad = scan(path, allowed)
        if bad is None:
            rows.append((name, "MISSING", "", ""))
            continue
        if not bad:
            rows.append((name, "clean", "", ""))
            continue
        total_bad_files += 1
        n_px = sum(bad.values())
        worst = sorted(bad.items(), key=lambda kv: -kv[1])[:3]
        detail = ", ".join(
            "#%02x%02x%02x x%d (nearest ramp step %s, d=%.1f)"
            % (c[0], c[1], c[2], n, *nearest(c, allowed))
            for c, n in worst)
        rows.append((name, "%d off-palette px / %d colours" % (n_px, len(bad)),
                     detail, ""))
    width = max(len(r[0]) for r in rows) + 2
    for name, status, detail, _ in rows:
        print("  %-*s %s" % (width, name, status))
        if detail:
            print("      %s" % detail)
    return total_bad_files


def main():
    allowed = load_allowed()
    print("palette purity — %d allowed colours (ramps + ink)\n" % len(allowed))
    print("strict sheets (every pixel must be a ramp step):")
    n_strict_bad = report(STRICT_SHEETS, allowed, strict=True)
    print("\nfx sheets (reported, not enforced — see this script's docstring):")
    report(FX_SHEETS, allowed, strict=False)
    print()
    if n_strict_bad:
        print("FAIL: %d strict sheet(s) carry off-palette pixels" % n_strict_bad)
        return 1
    print("OK: every strict sheet is ramp-pure")
    return 0


if __name__ == "__main__":
    sys.exit(main())
