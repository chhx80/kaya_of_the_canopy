#!/usr/bin/env python3
"""Generates the Phase 5 "juice" art: particle sprites and animated tile frames.

Kept apart from tools/gen_art.py on purpose — everything here is an *overlay* on
the art that generator produces, and the two are worked on independently.

Output goes to assets/sprites/fx/:
    particles.png   4x4 grid of 8x8 particle frames (dust, spark, shimmer, scatter)
    tile_anim.png   4x2 grid of 16x16 tile frames  (water surface, lava)

The tile frames are *derived from the live tileset* rather than drawn from
scratch: gen_fx.py opens assets/tiles/tileset.png and re-times the pixels that
are already there. Repaint the tileset and re-run this and the animation follows
the new palette for free. If the tileset cannot be read, a plain built-in
fallback is used so this script never depends on another generator having run.

Re-run with:  tools/genfx.sh
"""
import math, os
from PIL import Image

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
# they survive any repaint of the tiles underneath them.
PAL = {
    '.': (0, 0, 0, 0),
    'w': (0xf4, 0xf0, 0xe6, 255),   # off-white
    'W': (0xf4, 0xf0, 0xe6, 170),   # off-white, soft
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

ROWS = [DUST, SPARK, SHIMMER, SCATTER]


def build_particles():
    img = Image.new("RGBA", (CELL * FRAMES, CELL * len(ROWS)), (0, 0, 0, 0))
    for ry, row in enumerate(ROWS):
        for fx, frame in enumerate(row):
            img.paste(cell(frame), (fx * CELL, ry * CELL))
    img.save(os.path.join(FX, "particles.png"))
    print("particles.png (%dx%d)" % img.size)


# ------------------------------------------------------------- tile frames
def load_tile(tid):
    """The 16x16 cell for a tile id, or None if the tileset is unreadable."""
    if not os.path.exists(TILESET):
        return None
    try:
        sheet = Image.open(TILESET).convert("RGBA")
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
    img = Image.new("RGBA", (TS * FRAMES, TS * 2), (0, 0, 0, 0))
    for f in range(FRAMES):
        img.paste(water_frame(water, f), (f * TS, 0))
        img.paste(lava_frame(lava, f), (f * TS, TS))
    img.save(os.path.join(FX, "tile_anim.png"))
    print("tile_anim.png (%dx%d)" % img.size)


if __name__ == "__main__":
    build_particles()
    build_tile_anim()
    print("done")
