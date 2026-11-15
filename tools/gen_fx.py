#!/usr/bin/env python3
"""Generates the Phase 5 "juice" art: particle sprites and animated tile frames.

Kept apart from tools/gen_art.py on purpose — everything here is an *overlay* on
the art that generator produces, and the two are worked on independently.

Output goes to assets/sprites/fx/:
    particles.png   4x4 grid of 8x8 particle frames (dust, spark, shimmer, scatter)
    tile_anim.png   4x3 grid of 16x16 tile frames (water surface, lava, water
                    sparkle), drawn at ART_SCALE texels per world unit

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
CELL = 8                # particle cell size
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


def cell(rows):
    """8 ASCII rows -> an 8x8 RGBA image."""
    img = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
    for y, row in enumerate(rows[:CELL]):
        for x, ch in enumerate(row[:CELL]):
            img.putpixel((x, y), PAL[ch])
    return img


# ---------------------------------------------------------------- particles
# Row 0 — landing dust: a puff that spreads and thins.
DUST = [
    ["........",
     "........",
     "...aa...",
     "..awwa..",
     "..aaaa..",
     "........",
     "........",
     "........"],
    ["........",
     "..a..a..",
     ".awwwa..",
     ".awwwwa.",
     "..aaaa..",
     "...aa...",
     "........",
     "........"],
    [".A....A.",
     "..A..A..",
     ".AaWWa..",
     "A.aWWa.A",
     "..AaaA..",
     ".A....A.",
     "........",
     "........"],
    ["A......A",
     "...A.A..",
     "..A..A..",
     ".A.AA..A",
     "A...A...",
     "..A...A.",
     "........",
     "........"],
]

# Row 1 — blade impact spark: a hot cross that collapses to an ember.
SPARK = [
    ["...y....",
     "...y....",
     "..ywy...",
     "yyywwyyy",
     "..ywy...",
     "...y....",
     "...y....",
     "........"],
    ["y..y..y.",
     ".y.y.y..",
     "..ywy...",
     "yyywyyy.",
     "..ywy...",
     ".y.y.y..",
     "y..y..y.",
     "........"],
    ["o.....o.",
     "........",
     "..yo....",
     ".oywo...",
     "..oyo...",
     "........",
     "o.....o.",
     "........"],
    ["........",
     "..o.....",
     "........",
     "...oy...",
     "....o...",
     ".....o..",
     "........",
     "........"],
]

# Row 2 — gem shimmer: a four-point twinkle that opens and closes.
SHIMMER = [
    ["........",
     "........",
     "....c...",
     "...cwc..",
     "....c...",
     "........",
     "........",
     "........"],
    ["........",
     "...c....",
     "..cwc...",
     ".cwwwc..",
     "..cwc...",
     "...c....",
     "........",
     "........"],
    ["...C....",
     "...c....",
     "C.cwc..C",
     ".cwwwc..",
     "C.cwc..C",
     "...c....",
     "...C....",
     "........"],
    ["...C....",
     "........",
     "C..C...C",
     "..C.C...",
     "C..C...C",
     "........",
     "...C....",
     "........"],
]

# Row 3 — enemy death scatter: shell chips and leaf litter.
SCATTER = [
    ["........",
     "..gg....",
     ".gGGg.k.",
     ".gGGg.kk",
     "..gg....",
     "....mm..",
     "....mm..",
     "........"],
    ["..g.....",
     ".gGg..k.",
     ".gGg.kk.",
     "..g.....",
     "...mm...",
     "...mm.g.",
     "......g.",
     "........"],
    [".g....k.",
     ".gG..k..",
     "..g.....",
     "....m...",
     "...mm..g",
     "....m..g",
     "..k.....",
     "........"],
    ["......k.",
     ".g......",
     "....m...",
     "........",
     "...m...g",
     "........",
     "..k.....",
     "........"],
]

# Row 4 — turn scuff: a low, flat heel-streak that fades fast. Phase A,
# docs/plan-art-motion.md — spawned once when RenderFacingFSM enters State.TURN
# on the ground, kicked opposite the new facing.
TURN_SCUFF = [
    ["........",
     "........",
     "........",
     "........",
     "........",
     ".addda..",
     "adddada.",
     "........"],
    ["........",
     "........",
     "........",
     "........",
     "........",
     "a.ddd.a.",
     ".adada..",
     "........"],
    ["........",
     "........",
     "........",
     "........",
     "........",
     "..a.a...",
     ".a...a..",
     "........"],
    ["........",
     "........",
     "........",
     "........",
     "........",
     "........",
     "...a....",
     "........"],
]

# Row 5 — takeoff kick: a brighter, wider version of the landing dust, spawned
# once on the tick a jump leaves the ground (vel.y < 0), not on an ordinary
# walk off a ledge.
TAKEOFF_KICK = [
    ["........",
     "........",
     "..add...",
     ".adAda..",
     "adAAAda.",
     ".adada..",
     "..add...",
     "........"],
    ["........",
     ".a....a.",
     "a.adda.a",
     ".adAAda.",
     "a.adda.a",
     ".a....a.",
     "........",
     "........"],
    ["a......a",
     ".a....a.",
     "..a..a..",
     "...aa...",
     "..a..a..",
     ".a....a.",
     "a......a",
     "........"],
    [".a....a.",
     "..a..a..",
     "...aa...",
     "........",
     "........",
     "........",
     "........",
     "........"],
]

# Row 6 — surface-break splash: Phase B, docs/plan-art-motion.md. Spawned
# once by form_fish.gd when the fish breaks the surface (the jump-out hop) --
# a ring that pops open and falls back as droplets, cyan rather than the
# off-white every other burst uses, so it reads as water and not dust.
SPLASH = [
    ["........",
     "........",
     "..c..c..",
     ".c.CC.c.",
     "..CwwC..",
     ".c.CC.c.",
     "..c..c..",
     "........"],
    ["........",
     ".c....c.",
     "c.C..C.c",
     "..Cwwc..",
     "..cwwC..",
     "c.C..C.c",
     ".c....c.",
     "........"],
    ["c......c",
     "........",
     ".C....C.",
     "....c...",
     "..C.....",
     ".C....C.",
     "........",
     "c......c"],
    ["........",
     "c......c",
     "........",
     ".C......",
     "......C.",
     "........",
     "c......c",
     "........"],
]

ROWS = [DUST, SPARK, SHIMMER, SCATTER, TURN_SCUFF, TAKEOFF_KICK, SPLASH]


def build_particles():
    img = Image.new("RGBA", (CELL * FRAMES, CELL * len(ROWS)), (0, 0, 0, 0))
    for ry, row in enumerate(ROWS):
        for fx, frame in enumerate(row):
            img.paste(cell(frame), (fx * CELL, ry * CELL))
    img.save(os.path.join(FX, "particles.png"))
    print("particles.png (%dx%d)" % img.size)


# ------------------------------------------------------------- tile frames
# docs/plan-hd.md, H1: the tile frames are native at ART_SCALE (tile_anim is in
# tools/art/hd_native/hdtiles.txt). They are re-timed from the shipped 2x
# tileset cells, so the redrawn water and lava animate with their own detail;
# every distance below is in world units and multiplied by K at the texel.
K = palette.ART_SCALE   # texels per world unit
KT = TS * K             # a tile frame, in texels


def load_tile(tid):
    """The KTxKT cell for a tile id, or None if the tileset is unreadable."""
    if not os.path.exists(TILESET):
        return None
    try:
        sheet = Image.open(TILESET).convert("RGBA")
    except OSError:
        return None
    if sheet.width == ATLAS_COLUMNS * TS:
        sheet = palette.upscale(sheet, K)    # a 1x atlas (never shipped since H1)
    ox, oy = (tid % ATLAS_COLUMNS) * KT, (tid // ATLAS_COLUMNS) * KT
    if ox + KT > sheet.width or oy + KT > sheet.height:
        return None
    return sheet.crop((ox, oy, ox + KT, oy + KT))


def flat(rgba):
    img = Image.new("RGBA", (KT, KT), (0, 0, 0, 0))
    for y in range(KT):
        for x in range(KT):
            img.putpixel((x, y), rgba)
    return img


def scale(col, f):
    r, g, b, a = col
    return (min(255, int(r * f)), min(255, int(g * f)), min(255, int(b * f)), a)


def water_frame(src, f):
    """One frame of the water surface: every texel column rides a sine wave.

    The wave has exactly one period per tile, so neighbouring tiles line up and
    a row of them reads as a single moving surface. Its amplitude is one world
    unit, which at 2x is a swell of five texel heights instead of three steps.
    """
    out = Image.new("RGBA", (KT, KT), (0, 0, 0, 0))
    for x in range(KT):
        shift = int(round(K * math.sin(2.0 * math.pi * (x / float(KT) + f / float(FRAMES)))))
        for y in range(KT):
            sy = y - shift
            if sy < 0:
                continue            # crest rose: leave sky above it
            sy = min(KT - 1, sy)    # trough fell: repeat the water below
            out.putpixel((x, y), src.getpixel((x, sy)))
        # Pick out the crest so the movement is legible: the top texel bright,
        # the one under it half as much -- a crest with a thickness.
        k = 0
        for y in range(KT):
            if out.getpixel((x, y))[3]:
                out.putpixel((x, y), scale(out.getpixel((x, y)), 1.35 if k == 0 else 1.15))
                k += 1
                if k == 2:
                    break
    return out


def water_sparkle_frame(src, f):
    """Phase C, docs/plan-art-motion.md: sparkle + shoreline foam on
    `water_top`, expressed as four MORE frames of the same tile rather than a
    new id — "if a new tile id would be needed, do NOT add one". Built on top
    of `water_frame()`'s own wave so the surface keeps moving underneath: a
    ragged foam fleck along the crest, brighter and wider than the plain crest
    pick-out, plus two glints that walk the tile a different, deterministic
    way each frame so the cycle still repeats. At 2x a glint is a small star
    (a bright core and four dimmer arms), not a lit square.
    """
    out = water_frame(src, f).copy()
    for x in range(KT):                      # foam: a ragged bright crest
        top = next((y for y in range(KT) if out.getpixel((x, y))[3]), None)
        if top is not None and (x * 7 + f * 5 * K) % (11 * K) < 4 * K - (x % 3 == 0):
            out.putpixel((x, top), scale(out.getpixel((x, top)), 1.55))
    for i in range(2):                        # sparkle: two glints, drifting
        sx = ((f * 11 + i * 23 + 3) % TS) * K + K // 2
        sy = ((f * 7 + i * 13 + 2) % TS) * K + K // 2
        for dx, dy, g in ((0, 0, 1.8), (-1, 0, 1.3), (1, 0, 1.3), (0, -1, 1.3), (0, 1, 1.3)):
            x, y = sx + dx, sy + dy
            if 0 <= x < KT and 0 <= y < KT and out.getpixel((x, y))[3]:
                out.putpixel((x, y), scale(out.getpixel((x, y)), g))
    return out


def lava_frame(src, f):
    """One frame of lava: the whole body creeps upward one world unit a frame
    and pulses brighter. Wrapping the scroll keeps the tile seamless with
    itself vertically. Bubbles are round at 2x: a hot core and a rim.
    """
    glow = 1.0 + 0.06 * f
    out = Image.new("RGBA", (KT, KT), (0, 0, 0, 0))
    for y in range(KT):
        for x in range(KT):
            out.putpixel((x, y), scale(src.getpixel((x, (y + f * K) % KT)), glow))
    # Two bubbles per frame, placed deterministically so the cycle repeats.
    for i in range(2):
        bx = ((f * 5 + i * 9 + 3) % TS) * K
        by = ((f * 3 + i * 7 + 5) % TS) * K
        for dx, dy, g in ((0, 0, 1.6), (1, 0, 1.45), (0, 1, 1.3), (1, 1, 1.25),
                          (-1, 0, 1.15), (2, 1, 1.1), (0, 2, 1.12), (1, 2, 1.12)):
            x, y = bx + dx, by + dy
            if 0 <= x < KT and 0 <= y < KT and out.getpixel((x, y))[3]:
                out.putpixel((x, y), scale(out.getpixel((x, y)), g))
    return out


def build_tile_anim():
    water = load_tile(WATER_TOP_ID) or flat((0x3b, 0x6e, 0xa5, 255))
    lava = load_tile(LAVA_ID) or flat((0xc0, 0x4a, 0x3a, 255))
    # Row 0: the plain wave (frames 0-3). Row 1: lava (frames 4-7), unchanged.
    # Row 2: the sparkle+foam phase of the SAME water_top tile (frames 8-11) —
    # data/tile_anim.json's "7" entry cycles through both rows, so a shoreline
    # run of water_top gets its glint without a second tile id anywhere.
    img = Image.new("RGBA", (KT * FRAMES, KT * 3), (0, 0, 0, 0))
    for f in range(FRAMES):
        img.paste(water_frame(water, f), (f * KT, 0))
        img.paste(lava_frame(lava, f), (f * KT, KT))
        img.paste(water_sparkle_frame(water, f), (f * KT, KT * 2))
    img.save(os.path.join(FX, "tile_anim.png"))
    print("tile_anim.png (%dx%d, x%d native)" % (img.size + (K,)))


if __name__ == "__main__":
    started = palette.run_started()
    build_particles()
    build_tile_anim()
    palette.publish_hd(started, (FX,))
    print("done")
