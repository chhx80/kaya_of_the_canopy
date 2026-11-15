#!/usr/bin/env python3
"""Generates the Phase 5 "juice" art: particle sprites and animated tile frames.

Kept apart from tools/gen_art.py on purpose — everything here is an *overlay* on
the art that generator produces, and the two are worked on independently.

Output goes to assets/sprites/fx/:
    particles.png   7 rows x 4 frames of 8x8 particle cells, at 2x (tools/art/hd_back.py)
    tile_anim.png   4x2 grid of 16x16 tile frames  (water surface, lava)

The tile frames are *derived from the live tileset* rather than drawn from
scratch: gen_fx.py opens assets/tiles/tileset.png and re-times the pixels that
are already there. Repaint the tileset and re-run this and the animation follows
the new palette for free. If the tileset cannot be read, a plain built-in
fallback is used so this script never depends on another generator having run.

Re-run with:  tools/genfx.sh
"""
import math, os, sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from art import palette     # noqa: E402  the HD writer only (docs/plan-hd.md)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TILESET = os.path.join(ROOT, "assets", "tiles", "tileset.png")
FX = os.path.join(ROOT, "assets", "sprites", "fx")
os.makedirs(FX, exist_ok=True)

TS = 16                 # tile size, matches TileData4.TILE_SIZE
ATLAS_COLUMNS = 16      # tileset columns, matches data/tiles.json
FRAMES = 4              # frames per animation

WATER_TOP_ID = 7        # data/tiles.json ids — the two tiles we re-time
LAVA_ID = 24

# ---------------------------------------------------------------- palette
# Particles are deliberately near-monochrome: they read as light and debris, so
# they survive any repaint of the tiles underneath them. Hand-authored rather
# than imported from tools/art/palette.py for exactly that reason — but every
# value below was chosen to already equal one of the ramps' own steps (metal's
# brightest step, water's, foliage's...), so a repaint only drifts these if its
# author never looks at this file again. Phase E, docs/plan-art-motion.md's
# consistency sweep (tools/check_palette_purity.py) measured that against the
# generated PNG and found one real miss: 'w' had been typed as #f4f0e6, two
# values off metal's actual top step (#f2efe6) — fixed below, 38 px in
# particles.png.
PAL = {
    '.': (0, 0, 0, 0),
    'w': (0xf2, 0xef, 0xe6, 255),   # off-white (metal ramp, step 6)
    'W': (0xf2, 0xef, 0xe6, 170),   # off-white, soft
    'a': (0xb8, 0xb0, 0xa8, 255),   # light grey
    'A': (0xb8, 0xb0, 0xa8, 150),   # light grey, soft
    'd': (0x6a, 0x6a, 0x72, 200),   # grey
    'y': (0xf2, 0xd5, 0x65, 255),   # yellow
    'o': (0xe0, 0x8c, 0x3a, 255),   # orange
    'c': (0x41, 0xa6, 0xb5, 255),   # cyan
    'C': (0x41, 0xa6, 0xb5, 170),   # cyan, soft
    'g': (0x2a, 0x7a, 0x3f, 255),   # green
    'G': (0x58, 0xc1, 0x5a, 255),   # light green
    'm': (0x6b, 0x43, 0x26, 255),   # brown
    'k': (0x1a, 0x1c, 0x2c, 255),   # near-black
}


# ---------------------------------------------------------------- particles
# Seven rows of four frames: dust, spark, shimmer, scatter, turn scuff,
# takeoff kick, splash (data/fx.json names the rows). Drawn natively at 2x by
# tools/art/hd_back.py in this file's PAL (docs/plan-hd.md): 8x8 world cells,
# 16x16 texels each.
def build_particles():
    from art import hd_back
    img = hd_back.particles(PAL)
    img.save(os.path.join(FX, "particles.png"))
    print("particles.png (%dx%d)" % img.size)


# ------------------------------------------------------------- tile frames
def load_tile(tid):
    """The 16x16 cell for a tile id, or None if the tileset is unreadable."""
    if not os.path.exists(TILESET):
        return None
    try:
        # The shipped tileset is at ART_SCALE; these frames are re-timed at
        # one pixel per world unit and published at ART_SCALE like the rest.
        sheet = palette.open_1x(TILESET)
    except OSError:
        return None
    ox, oy = (tid % ATLAS_COLUMNS) * TS, (tid // ATLAS_COLUMNS) * TS
    if ox + TS > sheet.width or oy + TS > sheet.height:
        return None
    return sheet.crop((ox, oy, ox + TS, oy + TS))


def flat(rgba):
    img = Image.new("RGBA", (TS, TS), (0, 0, 0, 0))
    for y in range(TS):
        for x in range(TS):
            img.putpixel((x, y), rgba)
    return img


def scale(col, f):
    r, g, b, a = col
    return (min(255, int(r * f)), min(255, int(g * f)), min(255, int(b * f)), a)


def water_frame(src, f):
    """One frame of the water surface: every column rides a sine wave.

    The wave has exactly one period per tile, so neighbouring tiles line up and
    a row of them reads as a single moving surface.
    """
    out = Image.new("RGBA", (TS, TS), (0, 0, 0, 0))
    for x in range(TS):
        shift = int(round(math.sin(2.0 * math.pi * (x / float(TS) + f / float(FRAMES)))))
        for y in range(TS):
            sy = y - shift
            if sy < 0:
                continue            # crest rose: leave sky above it
            sy = min(TS - 1, sy)    # trough fell: repeat the water below
            out.putpixel((x, y), src.getpixel((x, sy)))
        # Pick out the crest so the movement is legible at 16px.
        for y in range(TS):
            if out.getpixel((x, y))[3]:
                out.putpixel((x, y), scale(out.getpixel((x, y)), 1.35))
                break
    return out


def water_sparkle_frame(src, f):
    """Phase C, docs/plan-art-motion.md: sparkle + shoreline foam on
    `water_top`, expressed as four MORE frames of the same tile rather than a
    new id — "if a new tile id would be needed, do NOT add one". Built on top
    of `water_frame()`'s own wave so the surface keeps moving underneath: a
    ragged foam fleck along the crest row, brighter and wider than the plain
    1.35x crest pick-out, plus two single-pixel glints that walk the tile a
    different, deterministic way each frame so the cycle still repeats.
    """
    out = water_frame(src, f).copy()
    for x in range(TS):                      # foam: a ragged bright crest
        c = out.getpixel((x, 0))
        if c[3] and (x * 7 + f * 5) % 11 < 4:
            out.putpixel((x, 0), scale(c, 1.55))
    for i in range(2):                        # sparkle: two glints, drifting
        sx = (f * 11 + i * 23 + 3) % TS
        sy = (f * 7 + i * 13 + 2) % TS
        c = out.getpixel((sx, sy))
        if c[3]:
            out.putpixel((sx, sy), scale(c, 1.8))
    return out


def lava_frame(src, f):
    """One frame of lava: the whole body creeps upward and pulses brighter.

    Wrapping the scroll keeps the tile seamless with itself vertically.
    """
    glow = 1.0 + 0.06 * f
    out = Image.new("RGBA", (TS, TS), (0, 0, 0, 0))
    for y in range(TS):
        for x in range(TS):
            out.putpixel((x, y), scale(src.getpixel((x, (y + f) % TS)), glow))
    # Two bubbles per frame, placed deterministically so the cycle repeats.
    for i in range(2):
        bx = (f * 5 + i * 9 + 3) % TS
        by = (f * 3 + i * 7 + 5) % TS
        if out.getpixel((bx, by))[3]:
            out.putpixel((bx, by), scale(out.getpixel((bx, by)), 1.6))
            if by + 1 < TS and out.getpixel((bx, by + 1))[3]:
                out.putpixel((bx, by + 1), scale(out.getpixel((bx, by + 1)), 1.25))
    return out


def build_tile_anim():
    water = load_tile(WATER_TOP_ID) or flat((0x3b, 0x6e, 0xa5, 255))
    lava = load_tile(LAVA_ID) or flat((0xc0, 0x4a, 0x3a, 255))
    # Row 0: the plain wave (frames 0-3). Row 1: lava (frames 4-7), unchanged.
    # Row 2: the sparkle+foam phase of the SAME water_top tile (frames 8-11) —
    # data/tile_anim.json's "7" entry cycles through both rows, so a shoreline
    # run of water_top gets its glint without a second tile id anywhere.
    img = Image.new("RGBA", (TS * FRAMES, TS * 3), (0, 0, 0, 0))
    for f in range(FRAMES):
        img.paste(water_frame(water, f), (f * TS, 0))
        img.paste(lava_frame(lava, f), (f * TS, TS))
        img.paste(water_sparkle_frame(water, f), (f * TS, TS * 2))
    img.save(os.path.join(FX, "tile_anim.png"))
    print("tile_anim.png (%dx%d)" % img.size)


if __name__ == "__main__":
    started = palette.run_started()
    build_particles()
    build_tile_anim()
    palette.publish_hd(started, (FX,))
    print("done")
