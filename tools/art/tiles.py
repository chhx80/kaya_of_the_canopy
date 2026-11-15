"""The 16x16 tileset.

Tile ids are load-bearing: `data/tiles.json`, `data/level_legend.json` and every
`levels/*.json` index into this atlas by position, so tiles may be repainted but
never reordered, inserted or removed. `T()` calls below are therefore in id
order and there must be exactly as many of them as `data/tiles.json` declares.

Authoring rule, from the prototype's second finding: **structure first, shading
second.** Shading a flat fill makes it softer, not better. A tile reads as
material when it contains discrete things — pebbles, mortar courses, planks,
nails, ribs of bark — each with its own highlight and its own shadow. Every
builder below authors the things, then lights them from the upper left.
"""
import json
import math
import os
import random

from PIL import Image

from . import tiles_p3
from .palette import (RAMPS, TILES, auto_shade, blob, crack, put, put_ink,
                       speckle)

TS = 16
#: Kaya Refit phase 3: a fill resolves its grain to whole ramp steps instead of
#: through the Bayer matrix. Fractional grain on a flat slab came out as a
#: checkerboard, and beside the 40 px Kaya — whose shading is clean steps — a
#: screen of checkerboard read as noise rather than material. The grain's random
#: stream is unchanged, so every structure drawn over a fill lands where it did.
CLEAN_FILL = True


def tile(alpha=0):
    return Image.new("RGBA", (TS, TS), (0, 0, 0, alpha))


def fill(img, ramp, base, rnd=None, grain=0.32, bevel=None):
    """A flat slab of one material, with optional grain and a bevel function.

    `bevel` is called as bevel(x, y) and returns a level offset, which is how
    each tile decides whether it is a free-standing block (lit top, occluded
    underside) or part of a mass that has to tile without banding.
    """
    for y in range(TS):
        for x in range(TS):
            lvl = base
            if bevel is not None:
                lvl += bevel(x, y)
            if rnd is not None and grain:
                lvl += rnd.uniform(-grain, grain)
            put(img, x, y, ramp, round(lvl) if CLEAN_FILL else lvl)
    return img


def block_bevel(x, y):
    """Free-standing block: sunlit cap, occluded underside, lit left cheek."""
    lvl = 0.0
    if y == 0:
        lvl += 2.2
    elif y == 1:
        lvl += 1.2
    elif y == 2:
        lvl += 0.45
    if y == 15:
        lvl -= 2.0
    elif y == 14:
        lvl -= 1.0
    if x == 0:
        lvl += 0.5
    elif x == 15:
        lvl -= 0.7
    return lvl


def wrap_blob(img, ramp, cx, cy, rx, ry, base, **kw):
    """A blob that survives being tiled: drawn again across each edge."""
    for dx in (-TS, 0, TS):
        for dy in (-TS, 0, TS):
            blob(img, ramp, cx + dx, cy + dy, rx, ry, base, **kw)


def grass_cap(img, rnd, top=0, height=3, ramp="grass", light=True):
    """The lit sod that sits on top of an earth tile: a ragged band of grass
    with blades hanging down into the soil below it."""
    depth = []
    for x in range(TS):
        h = height + (1 if rnd.random() < 0.45 else 0)
        for y in range(top, top + h):
            put(img, x, y, ramp, 5.4 - (y - top) * 1.5)
        if rnd.random() < 0.5:
            put(img, x, top + h, ramp, 2.6)
            h += 1
        depth.append(top + h)
    if light:
        # sun striking the exposed soil directly under the sod
        for x in range(TS):
            for k in range(3):
                y = depth[x] + k
                if y < TS:
                    put(img, x, y, "dirt", 4.4 - k * 0.9 + rnd.uniform(-0.2, 0.2))
    return depth


# ---------------------------------------------------------------- terrain
def t_dirt(seed):
    """Packed earth. No block bevel — dirt tiles in a solid mass and a per-tile
    bevel would band it into visible bricks. Pebbles do the work instead."""
    rnd = random.Random(seed)
    img = fill(tile(255), "dirt", 3.0, rnd, grain=0.30)
    for _ in range(6):                                   # clods of earth
        wrap_blob(img, "dirt", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(1.4, 2.8), rnd.uniform(1.1, 2.1), 2.3)
    for _ in range(2):                                   # buried pebbles
        wrap_blob(img, "stone", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(0.9, 1.6), rnd.uniform(0.8, 1.3), 3.1)
    for _ in range(2):                                   # root fibres
        crack(img, "dirt", rnd.randrange(TS), rnd.randrange(2, 13), 6, 3.0, rnd)
    speckle(img, "dirt", rnd, 14, 3.0, (-1.1, 1.0))
    return img


def t_grass_top(seed):
    rnd = random.Random(seed)
    img = t_dirt(seed + 100)
    grass_cap(img, rnd)
    return img


def t_grass_edge(seed, side):
    """Left/right face of a grass platform: the sod wraps over the corner and
    hangs a little way down the cliff, and the rock face itself is lit (left)
    or occluded (right) to agree with the light direction."""
    rnd = random.Random(seed)
    img = t_dirt(seed + 100)
    grass_cap(img, rnd)
    for y in range(TS):
        for k in range(2):
            x = k if side == "left" else TS - 1 - k
            shade = (1.5 - k * 0.7) if side == "left" else (-1.4 + k * 0.5)
            put(img, x, y, "dirt", 3.0 + shade + rnd.uniform(-0.25, 0.25))
    # moss creeping down the exposed edge
    run = 5 + rnd.randrange(4)
    for y in range(run):
        w = 2 if y < run - 2 else 1
        for k in range(w):
            x = k if side == "left" else TS - 1 - k
            lvl = (4.6 if side == "left" else 3.4) - y * 0.45
            put(img, x, y, "grass", lvl)
    return img


def t_stone(seed, mossy=False):
    """Cut masonry. Two courses of half-offset blocks with mortar joints on the
    tile edges, so a wall of these tiles reads as continuous coursing rather
    than as a grid of identical squares."""
    rnd = random.Random(seed)
    img = tile(255)
    for y in range(TS):
        course = 0 if y < 8 else 1
        jy = 0 if course == 0 else 8            # horizontal mortar row
        jx = 0 if course == 0 else 8            # vertical mortar column
        for x in range(TS):
            if y == jy or x == jx:
                lvl = 1.1 + rnd.uniform(-0.25, 0.25)        # mortar
            else:
                ly, lx = y - jy, (x - jx) % TS
                lvl = 3.1
                if ly == 1:
                    lvl += 1.7                              # sunlit top of block
                elif ly == 2:
                    lvl += 0.6
                elif ly == 7:
                    lvl -= 1.5                              # its own drop shadow
                if lx == 1:
                    lvl += 0.9
                elif lx == 15:
                    lvl -= 1.1
                lvl += rnd.uniform(-0.3, 0.3)
            put(img, x, y, "stone", lvl)
    for _ in range(3):                                      # weathering pits
        blob(img, "stone", rnd.randrange(2, 14), rnd.randrange(2, 14),
             rnd.uniform(0.8, 1.5), rnd.uniform(0.7, 1.2), 1.9)
    crack(img, "stone", rnd.randrange(1, 7), rnd.randrange(2, 6), 6, 3.1, rnd)
    if mossy:
        for x in range(TS):
            h = 1 + (2 if rnd.random() < 0.55 else 0)
            for y in range(h):
                put(img, x, y, "foliage", 4.6 - y * 1.1)
            if rnd.random() < 0.35:
                put(img, x, h, "foliage", 2.4)
        for _ in range(3):                                  # tufts hanging lower
            x = rnd.randrange(TS)
            for y in range(3, 3 + rnd.randrange(1, 4)):
                put(img, x, y, "foliage", 3.2 - (y - 3) * 0.6)
    return img


def t_bg_rock(seed):
    """Background stone. Same material, held down at the dark, low-contrast end
    of the ramp — the atmospheric-perspective trick phase 3 leans on."""
    rnd = random.Random(seed)
    img = fill(tile(255), "stone", 1.25, rnd, grain=0.3)
    for _ in range(5):
        wrap_blob(img, "stone", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(2.0, 4.0), rnd.uniform(1.6, 3.0), 1.0,
                  lit=0.9, dark=0.7)
    for _ in range(2):
        crack(img, "stone", rnd.randrange(TS), rnd.randrange(TS), 7, 1.4, rnd)
    speckle(img, "stone", rnd, 10, 1.3, (-0.6, 0.7))
    return img


def t_bg_dark(seed):
    """The void behind everything. Almost flat on purpose: it exists to make
    the lit tiles in front of it read."""
    rnd = random.Random(seed)
    img = fill(tile(255), "stone", 0.25, rnd, grain=0.22)
    speckle(img, "stone", rnd, 12, 0.5, (-0.3, 0.9))
    return img


def t_bg_leaves(seed):
    """A mat of overlapping leaves, dark enough to sit behind the player.

    Deliberately low contrast. This is a background fill and there is only one
    of it, so any strong structure in it becomes a visible repeat across a whole
    screen — the variant sets in phase 2 are what buy the headroom to make a
    fill tile bolder than this."""
    rnd = random.Random(seed)
    img = fill(tile(255), "foliage", 1.0, rnd, grain=0.26)
    for _ in range(13):
        cx, cy = rnd.randrange(TS), rnd.randrange(TS)
        rx, ry = rnd.uniform(2.0, 3.6), rnd.uniform(1.3, 2.4)
        wrap_blob(img, "foliage", cx, cy, rx, ry, 1.5, lit=0.9, dark=0.7)
        for i in range(-int(rx), int(rx) + 1):             # midrib
            put(img, (cx + i) % TS, (cy - int(i * 0.3)) % TS, "foliage", 2.5)
    speckle(img, "foliage", rnd, 16, 1.2, (-0.6, 0.9))
    return img


def t_trunk(seed):
    """Bark. Vertical ribs with a lit left shoulder and a dark groove on the
    right of each — tiles vertically without a seam because nothing in it is
    keyed to the top or bottom row."""
    rnd = random.Random(seed)
    img = fill(tile(255), "wood", 2.0, rnd, grain=0.28)
    edges = [0, 3, 6, 10, 13, 16]
    for i in range(len(edges) - 1):
        x0, x1 = edges[i], edges[i + 1]
        for x in range(x0, x1):
            for y in range(TS):
                lvl = 2.0
                if x == x0:
                    lvl -= 1.6                    # groove between ribs
                elif x == x0 + 1:
                    lvl += 1.4                    # lit shoulder
                elif x == x1 - 1:
                    lvl -= 1.0                    # rolling into shadow
                lvl += rnd.uniform(-0.3, 0.3)
                if rnd.random() < 0.10:           # flaking bark
                    lvl -= 1.2
                put(img, x, y, "wood", lvl)
    for _ in range(4):                            # horizontal splits
        y = rnd.randrange(TS)
        x = rnd.randrange(TS)
        for k in range(rnd.randrange(2, 5)):
            put(img, (x + k) % TS, y, "wood", 0.8)
    return img


# ---------------------------------------------------------------- water
def t_water(seed, surface=False):
    rnd = random.Random(seed)
    img = tile(255)
    for y in range(TS):
        for x in range(TS):
            lvl = 4.4 if surface else 4.0
            if surface:
                lvl = 5.2 - min(y, 6) * 0.28
            put(img, x, y, "water", lvl + rnd.uniform(-0.3, 0.3))
    for _ in range(4):                            # slow caustic wisps
        y = rnd.randrange(TS)
        x = rnd.randrange(TS)
        for k in range(rnd.randrange(3, 7)):
            put(img, (x + k) % TS, (y + (k // 4)) % TS, "water", 5.6)
    for _ in range(3):                            # cold pockets of depth
        wrap_blob(img, "water", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(2.0, 3.4), rnd.uniform(1.2, 2.2), 3.0,
                  lit=0.8, dark=0.6)
    if surface:
        # Foam crest. The swell has period 16 so the tile repeats seamlessly,
        # and the foam only breaks on the rising face — a solid white rule
        # across the top row reads as a painted line, not as water.
        for x in range(TS):
            swell = math.sin(x * math.pi / 8.0)
            put(img, x, 0, "water", 6.0)
            if swell > 0.1:
                put(img, x, 0, "metal", 6.0)
                if swell > 0.75:
                    put(img, x, 1, "metal", 5.2)
            elif swell < -0.6:
                put(img, x, 0, "water", 4.6)      # trough between crests
            put(img, x, 1 if swell <= 0.75 else 2, "water", 6.0)
        for x in (2, 7, 11, 14):                  # sparkle on the swell
            put(img, x, 3 + (x % 2), "water", 6.0)
    return img


# ---------------------------------------------------------------- hazards
def t_spikes(seed):
    """Three iron spikes on a bolted plate. Each cone is lit on its left flank
    and falls away to the right, which is what stops them reading as triangles."""
    rnd = random.Random(seed)
    img = tile(0)
    for x in range(TS):                                  # base plate
        put(img, x, 13, "metal", 4.4 + rnd.uniform(-0.3, 0.3))
        put(img, x, 14, "metal", 2.6 + rnd.uniform(-0.3, 0.3))
        put_ink(img, x, 15)
    for bx in (1, 6, 11):                                # plate bolts
        blob(img, "metal", bx + 0.5, 13.5, 1.2, 1.0, 4.2)
    for cx in (2.5, 7.5, 12.5):
        for y in range(4, 14):
            half = (y - 4) / 9.0 * 2.7
            lo, hi = int(math.floor(cx - half)), int(math.ceil(cx + half))
            for x in range(lo, hi + 1):
                if not 0 <= x < TS:
                    continue
                t = (x - cx) / max(half, 0.6)
                if abs(t) > 1.05:
                    continue
                lvl = 4.6 - t * 2.4 + (0.5 if y < 6 else 0.0)
                put(img, x, y, "metal", lvl)
            put_ink(img, hi, y)                          # hard right edge
    return img


def t_lava(seed):
    """Molten rock: a bright skin over a body that is mostly cooled crust, with
    the crack network between the plates glowing through."""
    rnd = random.Random(seed)
    img = tile(255)
    for y in range(TS):
        for x in range(TS):
            lvl = 3.4
            if y == 0:
                lvl = 6.2
            elif y == 1:
                lvl = 5.4
            elif y == 2:
                lvl = 4.5
            put(img, x, y, "ember", lvl + rnd.uniform(-0.25, 0.25))
    for _ in range(6):                                   # cooled crust plates
        cx, cy = rnd.randrange(TS), rnd.randrange(4, TS)
        wrap_blob(img, "ember", cx, cy, rnd.uniform(2.0, 3.4),
                  rnd.uniform(1.4, 2.4), 1.2, lit=0.6, dark=0.5)
    for _ in range(4):                                   # glow in the seams
        x, y = rnd.randrange(TS), rnd.randrange(3, TS)
        for k in range(rnd.randrange(2, 5)):
            put(img, (x + k) % TS, (y + k % 2) % TS, "ember", 5.6)
    for (bx, by) in ((4, 9), (11, 12), (8, 6)):          # bubbles
        blob(img, "ember", bx, by, 1.6, 1.3, 4.4)
    return img


# ---------------------------------------------------------------- carpentry
def t_platform(seed):
    """One-way wooden platform: four rows of plank with a lit top edge, grain,
    two nails and a hard shadow line under it."""
    rnd = random.Random(seed)
    img = tile(0)
    for x in range(TS):
        put(img, x, 0, "wood", 5.2 + rnd.uniform(-0.2, 0.2))
        put(img, x, 1, "wood", 4.3 + rnd.uniform(-0.3, 0.3))
        put(img, x, 2, "wood", 3.2 + rnd.uniform(-0.3, 0.3))
        put_ink(img, x, 3)
    for sx in (5, 11):                                   # plank seams
        for y in range(1, 3):
            put(img, sx, y, "wood", 2.0)
    for nx in (2, 8, 14):                                # nail heads
        put(img, nx, 1, "metal", 5.4)
    return img


def t_crate(seed):
    """Crate: frame, planks, corner braces, nails. The prototype's proof that
    a tile needs authored things in it before shading can help."""
    rnd = random.Random(seed)
    img = tile(255)
    for y in range(TS):
        for x in range(TS):
            if x in (0, 15) or y in (0, 15):
                lvl = 5.0 if (y == 0 or x == 0) else 1.4         # frame
            elif x in (1, 14) or y in (1, 14):
                lvl = 4.2 if (y == 1 or x == 1) else 2.2
            elif y in (5, 10):
                lvl = 1.6                                        # plank seam
            elif y in (6, 11):
                lvl = 4.6                                        # lip below it
            else:
                lvl = 3.2 + rnd.uniform(-0.35, 0.35)
            put(img, x, y, "wood", lvl)
    for i in range(2, 14):                                       # diagonal brace
        put(img, i, i, "wood", 1.7)
        put(img, i, min(15, i + 1), "wood", 4.6)
        put(img, 15 - i, i, "wood", 1.7)
        put(img, 15 - i, min(15, i + 1), "wood", 4.4)
    for (nx, ny) in ((2, 2), (13, 2), (2, 13), (13, 13)):        # nails
        put(img, nx, ny, "metal", 5.4)
        put(img, nx, ny + 1, "metal", 1.8)
    return img


def t_bridge(seed):
    """Rope bridge: a sagging run of planks slung between two rope anchors."""
    rnd = random.Random(seed)
    img = tile(0)
    for x in range(TS):
        t = (x - 7.5) / 8.0
        top = 2 + int(round(2.6 * (1.0 - t * t)))
        put(img, x, top, "wood", 5.4)                    # sunlit plank top
        put(img, x, top + 1, "wood", 3.2 + rnd.uniform(-0.3, 0.3))
        put_ink(img, x, top + 2)
        if x % 3 == 0:                                   # gaps between planks
            put(img, x, top + 1, "wood", 1.4)
    for x in (0, 1, 14, 15):                             # rope anchors
        put(img, x, 1, "wood", 2.0)
        put(img, x, 2, "wood", 4.2)
    return img


def t_metal(seed):
    """Riveted plate: lit top and left, occluded bottom and right, a tread
    hatch across the face and a dome on every rivet."""
    rnd = random.Random(seed)
    img = tile(255)
    for y in range(TS):
        for x in range(TS):
            lvl = 3.2
            if y == 0:
                lvl = 5.6
            elif y == 1:
                lvl = 4.4
            elif y == 15:
                lvl = 0.8
            elif y == 14:
                lvl = 1.8
            if x == 0:
                lvl = min(lvl + 1.3, 5.8)
            elif x == 15:
                lvl -= 1.2
            if 2 <= y <= 13 and y % 4 == 0:
                lvl -= 0.9                               # tread hatch
            put(img, x, y, "metal", lvl + rnd.uniform(-0.18, 0.18))
    for (rx, ry) in ((2, 3), (13, 3), (2, 12), (13, 12)):
        blob(img, "metal", rx, ry, 1.6, 1.6, 3.4)
    return img


# ---------------------------------------------------------------- switches
def t_switch(ramp, on, seed, glyph):
    """Switch block. `on` is the solid state (a machined block); off is the
    ghost the renderer swaps in when the pair flips, so it stays mostly
    transparent and reads as "not there"."""
    rnd = random.Random(seed)
    if not on:
        img = tile(0)
        for x in range(TS):                              # dashed outline
            if (x // 2) % 2 == 0:
                put(img, x, 0, ramp, 4.6)
                put(img, x, 14, ramp, 3.4)
        for y in range(1, 15):
            if (y // 2) % 2 == 0:
                put(img, 0, y, ramp, 4.6)
                put(img, 15, y, ramp, 3.4)
        for i, (gx, gy) in enumerate(glyph):             # ghost of the rune
            if i % 2 == 0:
                put(img, gx, gy, ramp, 4.0)
        return img
    img = tile(255)
    for y in range(TS):
        for x in range(TS):
            if y == 15:
                lvl = 0.2
            elif x in (0, 15) or y == 0:
                lvl = 5.6 if (y == 0 or x == 0) else 1.4
            elif x in (1, 14) or y in (1, 13):
                lvl = 4.6 if (y == 1 or x == 1) else 2.0
            else:
                lvl = 2.6 + rnd.uniform(-0.25, 0.25)     # recessed panel
            put(img, x, y, ramp, lvl)
    for (gx, gy) in glyph:                               # raised rune
        put(img, gx, gy, ramp, 6.0)
        put(img, gx, gy + 1, ramp, 1.6)
    return img


def _diamond():
    out = []
    for dy in range(-3, 4):
        dx = 3 - abs(dy)
        out += [(7 + dx, 7 + dy), (7 - dx, 7 + dy)]
    return sorted(set(out))


def _square():
    out = []
    for i in range(-3, 4):
        out += [(7 + i, 4), (7 + i, 10), (4, 7 + i), (10, 7 + i)]
    return sorted(set(out))


# ---------------------------------------------------------------- vine
VINE_ROWS = [
    "......GG.G......",
    ".....GllGG......",
    "....GlGG.GG.....",
    "..GGGlG...GGG...",
    "GGGllG.....lGGGG",
    "..GGGG.....GGG..",
    "......GG.GG.....",
    "......GllG......",
    "......GllG......",
    ".....GGllGG.....",
    "..GGGGlGGGGGG...",
    "GGGllG...GlGGGG.",
    "..GGG.....GGG...",
    "......GG.GG.....",
    "......GllG......",
    "......GGGG......",
]
VINE_MAP = {'G': ("foliage", 2.6), 'l': ("grass", 3.6)}


# ---------------------------------------------------------------- overworld
# The hub is drawn top-down, so these four get ambient light rather than the
# side-lit bevel the platforming tiles use.
def t_hub_grass(seed):
    rnd = random.Random(seed)
    img = fill(tile(255), "grass", 2.4, rnd, grain=0.35)
    for _ in range(6):
        wrap_blob(img, "grass", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(1.8, 3.2), rnd.uniform(1.4, 2.4), 2.0,
                  lit=0.9, dark=0.8)
    for _ in range(10):                                  # tufts
        x, y = rnd.randrange(TS), rnd.randrange(TS)
        for k in range(rnd.randrange(1, 3)):
            put(img, x, (y - k) % TS, "grass", 4.0 + k * 0.4)
    # No flowers. One flower authored into the fill tile becomes a perfectly
    # regular grid of flowers across the whole overworld, which reads far worse
    # than plain grass. Scatter belongs on the variant set in phase 2.
    speckle(img, "foliage", rnd, 10, 3.0, (-0.6, 0.6))
    return img


def t_hub_path(seed):
    rnd = random.Random(seed)
    img = fill(tile(255), "dirt", 4.7, rnd, grain=0.3)
    for _ in range(7):                                   # pebbles in the sand
        wrap_blob(img, "stone", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(0.9, 1.7), rnd.uniform(0.8, 1.4), 3.2)
    for _ in range(4):                                   # tracked-in earth
        wrap_blob(img, "dirt", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(1.8, 3.0), rnd.uniform(1.2, 2.0), 3.8,
                  lit=0.8, dark=0.7)
    speckle(img, "dirt", rnd, 18, 4.7, (-1.0, 1.1))
    return img


def t_hub_water(seed):
    rnd = random.Random(seed)
    img = fill(tile(255), "water", 4.6, rnd, grain=0.3)
    for _ in range(5):                                   # ripple rings
        cx, cy = rnd.randrange(TS), rnd.randrange(TS)
        r = rnd.randrange(2, 5)
        for a in range(0, 360, 18):
            x = cx + int(round(r * math.cos(math.radians(a))))
            y = cy + int(round(r * 0.6 * math.sin(math.radians(a))))
            put(img, x % TS, y % TS, "water", 6.0 if a < 180 else 3.2)
    speckle(img, "water", rnd, 10, 4.6, (-1.0, 1.2))
    return img


def t_hub_tree(seed):
    """Overworld tree: a canopy of leaf clusters over a short trunk."""
    rnd = random.Random(seed)
    img = tile(0)
    for _ in range(14):                                  # mass of the crown
        cx = rnd.randrange(2, 14)
        cy = rnd.randrange(1, 9)
        blob(img, "foliage", cx, cy, rnd.uniform(2.4, 4.0),
             rnd.uniform(2.0, 3.2), 3.4)
    for _ in range(9):                                   # sunlit upper leaves
        blob(img, "grass", rnd.randrange(2, 13), rnd.randrange(0, 6),
             rnd.uniform(1.4, 2.6), rnd.uniform(1.1, 2.0), 3.0)
    # The trunk is placed by the seed, not centred: a stand of these tiles kept
    # a visible column rhythm while every trunk sat in the same four pixels.
    tx = rnd.randrange(4, 9)
    tw = rnd.randrange(3, 5)
    top = 8 + rnd.randrange(0, 3)
    if rnd.random() > 0.72:
        # A third of the variants are canopy only. The hub borders its map with
        # a solid run of these, and a trunk in every single tile is the rhythm
        # that gives the run away as tiles.
        for x in range(3, 13):
            put(img, x, 15, "foliage", 2.6 + rnd.uniform(-0.5, 0.5))
        return img
    for y in range(top, TS):
        for x in range(tx, tx + tw):
            lvl = 3.4
            if x == tx:
                lvl += 1.4
            elif x == tx + tw - 1:
                lvl -= 1.4
            put(img, x, y, "wood", lvl + rnd.uniform(-0.2, 0.2))
    for x in range(max(0, tx - 2), min(TS, tx + tw + 2)):  # roots in the grass
        put(img, x, 15, "grass", 3.0 + rnd.uniform(-0.6, 0.6))
    return img


# ============================================================== worlds 2-5
# Four new tilesets, one per world of docs/plan-20-levels.md. Each is built the
# way the jungle set above is — author the discrete things first, then light
# them from the upper left — and each is held to one extra rule the jungle set
# never had to state:
#
#   **a world must not swallow the player.**
#
# Measured over the solid pixels of the four form sheets, Kaya reads as:
#
#     human   ink outline, cloth 93-120, skin 159-191
#     frog    NO outline, 26-150, and 62% of it sits at 118-150   <- the hard one
#     fish    NO outline, 52-209, and 52% of it sits at 156-209
#     bird    ink outline, 82-238
#
# The frog is why this is written down rather than left to taste. It carries no
# ink outline at all, so it reads purely as a green silhouette against whatever
# is behind it, and the shipped jungle parallax is green at the same luma —
# a real defect in the current art, measured by tools/gen_art.py --readability.
#
# So every world below fixes the luma band its *bulk* material may occupy, and
# anything that lands inside a form's band is confined to crests, veins and
# specks a pixel or two wide. A fill never enters a form's band. The bands:
#
#     ruins     stone/water 40-92        algae held under 55
#     heights   dirt 58-100              bleached crest is a 2px line, not a face
#     deeps     dirt/wood 21-60          the fungal glow is violet, a hue no
#                                        form uses, and never a fill
#     nest      stone/purple 22-40       ember lives in 1px cracks


# ---------------------------------------------------------- 2. SUNKEN RUINS
# Waterlogged stone, algae, submerged columns. Cold greens and blue-greys: the
# `stone` ramp is already blue-grey, so the world is built by holding it two
# steps darker than the jungle masonry and letting `water` into every joint.
def t_ruin_stone(seed, algae=False):
    """Ashlar that has spent a century under water.

    The coursing is t_stone()'s — two half-offset courses, so a wall reads as
    masonry and not as a grid of squares — but every joint holds standing water
    instead of dry mortar, the faces are pitted where the current worked at
    them, and algae has taken the shaded side of each block."""
    rnd = random.Random(seed)
    img = tile(255)
    for y in range(TS):
        jy = 0 if y < 8 else 8                      # horizontal mortar row
        jx = 0 if y < 8 else 8                      # vertical mortar column
        for x in range(TS):
            if y == jy or x == jx:
                put(img, x, y, "water", 1.7 + rnd.uniform(-0.35, 0.35))
                continue
            ly, lx = y - jy, (x - jx) % TS
            lvl = 2.5
            if ly == 1:
                lvl += 1.4                          # top of the block, lit
            elif ly == 2:
                lvl += 0.5
            elif ly == 7:
                lvl -= 1.3                          # its own drop shadow
            if lx == 1:
                lvl += 0.8
            elif lx == 15:
                lvl -= 1.0
            put(img, x, y, "stone", lvl + rnd.uniform(-0.3, 0.3))
    for _ in range(4):                              # pitting
        blob(img, "stone", rnd.randrange(2, 14), rnd.randrange(2, 14),
             rnd.uniform(0.9, 1.7), rnd.uniform(0.8, 1.4), 1.4)
    for _ in range(2):                              # algae, dark and in shade
        wrap_blob(img, "foliage", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(1.6, 3.0), rnd.uniform(1.0, 2.0), 1.6,
                  lit=0.7, dark=0.6)
    crack(img, "stone", rnd.randrange(1, 8), rnd.randrange(2, 7), 6, 2.5, rnd)
    if algae:
        # The ledge-top read. A grass cap is bright; this one must not be, or
        # the frog standing on it disappears — so the mat is `foliage` 1.4-3.6
        # (luma 27-53) and the only bright thing in it is a broken line of wet
        # highlight one pixel deep.
        depth = []
        for x in range(TS):
            h = 2 + (1 if rnd.random() < 0.5 else 0)
            for y in range(h):
                put(img, x, y, "foliage", 3.6 - y * 1.1)
            if rnd.random() < 0.55:
                put(img, x, h, "foliage", 1.4)
                h += 1
            depth.append(h)
        for x in range(TS):
            if rnd.random() < 0.28:
                put(img, x, 0, "water", 5.8)        # sun on the wet crest
        for _ in range(3):                          # strands down the face
            x = rnd.randrange(TS)
            for y in range(depth[x], min(TS, depth[x] + rnd.randrange(2, 6))):
                put(img, x, y, "foliage", 2.4 - (y - depth[x]) * 0.35)
    return img


def t_ruin_wall(seed):
    """Background masonry. Same building, held at the dark end of the ramp so
    the blocks in front of it read as the ones you can stand on."""
    rnd = random.Random(seed)
    img = fill(tile(255), "stone", 0.85, rnd, grain=0.26)
    for y in (3, 11):                               # ghost of the coursing
        for x in range(TS):
            put(img, x, y, "stone", 0.5 + rnd.uniform(-0.2, 0.2))
            put(img, x, y + 1, "stone", 1.7 + rnd.uniform(-0.2, 0.2))
    for x in (5, 13):
        for y in range(TS):
            put(img, x, y, "stone", 0.6 + rnd.uniform(-0.2, 0.2))
    for _ in range(2):
        wrap_blob(img, "foliage", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(3.4, 6.0), rnd.uniform(2.0, 3.6), 0.7,
                  lit=0.5, dark=0.4)
    speckle(img, "stone", rnd, 12, 0.9, (-0.5, 0.6))
    return img


def t_ruin_silt(seed):
    """Cold silt: the mud a flooded room collects. Earth, but drained of every
    warm step and seeded with the shell grit that settles out of still water."""
    rnd = random.Random(seed)
    # Built on `stone` with `dirt` coming through it rather than the other way
    # round. The first pass was a dirt tile with grit in it and read as ordinary
    # jungle earth, which is the one thing a drowned room must not look like.
    img = fill(tile(255), "stone", 1.9, rnd, grain=0.26)
    for _ in range(6):                              # mud coming through
        wrap_blob(img, "dirt", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(1.8, 3.2), rnd.uniform(1.2, 2.2), 1.5,
                  lit=0.9, dark=0.7)
    for _ in range(5):                              # shell grit
        wrap_blob(img, "stone", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(0.8, 1.5), rnd.uniform(0.7, 1.2), 3.4)
    for _ in range(3):                              # water standing in a hollow
        wrap_blob(img, "water", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(1.8, 3.0), rnd.uniform(1.0, 1.8), 2.4,
                  lit=0.8, dark=0.5)
    for _ in range(2):                              # a worm cast of algae
        wrap_blob(img, "foliage", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(1.0, 2.0), rnd.uniform(0.8, 1.4), 1.6,
                  lit=0.7, dark=0.5)
    speckle(img, "stone", rnd, 16, 2.0, (-0.7, 0.8))
    return img


def t_ruin_deep(seed):
    """The flooded void behind everything. Almost flat, and blue rather than
    black: a drowned room still has light in it, it just has no detail."""
    rnd = random.Random(seed)
    img = fill(tile(255), "water", 1.0, rnd, grain=0.22)
    for _ in range(2):
        wrap_blob(img, "water", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(3.0, 5.0), rnd.uniform(2.0, 3.4), 0.6,
                  lit=0.5, dark=0.4)
    speckle(img, "water", rnd, 10, 1.1, (-0.3, 0.8))
    return img


def t_ruin_column(seed):
    """A fluted column shaft, drawn as background so a level can stand one up
    behind the play field. Tiles vertically: nothing is keyed to a row."""
    rnd = random.Random(seed)
    img = fill(tile(255), "water", 0.7, rnd, grain=0.2)     # the room behind it
    # Three broad flutes, not eight fine ones: at 16 px a fine flute is noise.
    # The shaft is bounded by its own shadow on the right and by the lit air on
    # the left, which is the only thing that makes it read as round and in front
    # of the wall rather than as part of it.
    # Nine pixels wide, not twelve, with drowned room either side of it. A
    # shaft that fills its tile has no silhouette, and the first pass of this
    # one read as a window frame rather than as a column standing in a room.
    x0, wdt = 4, 9
    for x in range(x0, x0 + wdt):
        t = (x - x0) / float(wdt - 1)
        f = ((x - x0) % 5) / 4.0                    # position within one flute
        for y in range(TS):
            lvl = 2.2
            lvl += 1.0 - 2.2 * t                    # the barrel of the shaft
            lvl += 0.7 if f < 0.3 else (-1.1 if f > 0.95 else -0.15)
            put(img, x, y, "stone", lvl + rnd.uniform(-0.18, 0.18))
    for y in range(TS):
        put_ink(img, x0 + wdt, y)                   # the shadow it casts right
        put(img, x0 - 1, y, "stone", 3.0)           # the light on its left
    for _ in range(3):                              # algae creeping up it
        cy = rnd.randrange(TS)
        wrap_blob(img, "foliage", rnd.randrange(x0, x0 + wdt), cy,
                  rnd.uniform(1.0, 2.0), rnd.uniform(1.0, 2.0), 1.4,
                  lit=0.7, dark=0.5)
    y = rnd.randrange(TS)                           # one chipped drum joint
    for x in range(x0, x0 + wdt):
        put(img, x, y, "stone", 0.7)
        if y + 1 < TS:
            put(img, x, y + 1, "stone", 3.2)
    return img


def t_ruin_slab(seed):
    """One-way slab: a cracked flag of masonry on two corbels, with the hard
    ink line under it that tells you nothing is holding it up from below."""
    rnd = random.Random(seed)
    img = tile(0)
    for x in range(TS):
        put(img, x, 0, "stone", 4.6 + rnd.uniform(-0.25, 0.25))
        put(img, x, 1, "stone", 3.4 + rnd.uniform(-0.3, 0.3))
        put(img, x, 2, "stone", 2.2 + rnd.uniform(-0.3, 0.3))
        put_ink(img, x, 3)
    for sx in (4, 11):                              # joints between flags
        for y in range(0, 3):
            put(img, sx, y, "stone", 1.3)
    for x in range(TS):                             # algae hanging off the lip
        if rnd.random() < 0.3:
            put(img, x, 2, "foliage", 2.6)
    for cx in (2, 12):                              # corbels
        for k in range(3):
            put(img, cx + k, 4, "stone", 2.8 - k * 0.4)
    return img


def t_ruin_urchin(seed):
    """The hazard. Three urchins wedged in the silt — a dark body with pale
    spines, because a hazard has to read as one at 400x240 and the only thing
    small enough to be bright without flattening the world is a spine."""
    rnd = random.Random(seed)
    img = tile(0)
    for x in range(TS):                             # the silt they sit in
        put(img, x, 13, "dirt", 2.2 + rnd.uniform(-0.3, 0.3))
        put(img, x, 14, "dirt", 1.2 + rnd.uniform(-0.3, 0.3))
        put_ink(img, x, 15)
    # The spines go down first and the body over the top of them, so the shape
    # reads as a creature with spines rather than as a pile of white specks —
    # which is what the first pass came out as at 400x240.
    for (cx, cy, r) in ((3.0, 10.0, 3.2), (8.5, 11.0, 2.6), (13.0, 9.5, 3.6)):
        # Five spines, two pixels at the root and one at the tip. The first pass
        # drew twelve one-pixel spines and the result read as a tuft of grass:
        # a spine has to be thick enough to have a lit side and a dark one.
        for ang in (205, 240, 270, 300, 335):
            a = math.radians(ang + rnd.randrange(-8, 9))
            ln = r + 2.5 + rnd.uniform(0, 1.0)
            k = 1.0
            while k < ln:
                px = int(round(cx + math.cos(a) * k))
                py = int(round(cy + math.sin(a) * k))
                near_tip = k > ln - 1.6
                put(img, px, py, "metal", 5.6 if near_tip else 3.0)
                if not near_tip:
                    put_ink(img, px + 1, py)
                k += 1.0
        blob(img, "purple", cx, cy, r, r * 0.85, 1.6, lit=1.8, dark=1.0)
        blob(img, "foliage", cx - r * 0.25, cy + r * 0.3,
             r * 0.6, r * 0.5, 2.2)
        for k in range(-1, 2):                      # the test, ribbed
            put(img, int(cx + k), int(cy - r * 0.45), "stone", 3.4)
        put(img, int(cx - r * 0.4), int(cy - r * 0.3), "water", 6.0)
    return img


def t_ruin_grate(seed):
    """An iron grate. Solid, rusted through in places, algae in every square."""
    rnd = random.Random(seed)
    img = tile(255)
    for y in range(TS):
        for x in range(TS):
            put(img, x, y, "water", 0.8 + rnd.uniform(-0.2, 0.2))
    for i in (0, 5, 10, 15):
        for y in range(TS):
            put(img, i, y, "metal", 3.6 + rnd.uniform(-0.3, 0.3))
            if i + 1 < TS:
                put(img, i + 1, y, "metal", 1.6)
        for x in range(TS):
            put(img, x, i, "metal", 4.4 + rnd.uniform(-0.3, 0.3))
            if i + 1 < TS:
                put(img, x, i + 1, "metal", 1.8)
    for _ in range(5):                              # rust blooms
        wrap_blob(img, "ember", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(1.0, 2.0), rnd.uniform(0.9, 1.6), 2.2,
                  lit=0.8, dark=0.6)
    for _ in range(4):                              # algae in the squares
        wrap_blob(img, "foliage", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(1.2, 2.2), rnd.uniform(1.0, 1.8), 1.6,
                  lit=0.6, dark=0.5)
    return img


def t_kelp(seed):
    """The climbable. Kelp, not vine: a brown stipe with green blades off it,
    so it cannot be mistaken for the frog standing in front of it."""
    rnd = random.Random(seed)
    img = tile(0)
    x = 7
    for y in range(TS):
        x = max(3, min(12, x + rnd.choice((-1, 0, 0, 1))))
        put(img, x, y, "wood", 3.6)                 # stipe, lit shoulder
        put(img, x + 1, y, "wood", 2.2)
        put(img, x + 2, y, "wood", 0.9)
        if y % 3 == 1:                              # blades
            side = -1 if (y // 3) % 2 == 0 else 2
            span = 4 + rnd.randrange(3)
            for k in range(span):
                px = x + side * (1 + k) + (1 if side > 0 else 0)
                for t in range(2 if k < span - 2 else 1):
                    put(img, px, y + k // 2 + t, "foliage",
                        3.6 - k * 0.25 - t * 1.4)
        if y % 6 == 3:                              # gas bladder
            put(img, x - 1, y, "gold", 3.0)
    return img


def t_ruin_algae(seed):
    """Background algae mat: the leaf-litter of a drowned room. Deliberately
    the flattest tile in the world — it is a fill, and a fill that reads is a
    fill that repeats."""
    rnd = random.Random(seed)
    img = fill(tile(255), "foliage", 0.8, rnd, grain=0.22)
    for _ in range(11):
        cx, cy = rnd.randrange(TS), rnd.randrange(TS)
        wrap_blob(img, "foliage", cx, cy, rnd.uniform(2.0, 3.4),
                  rnd.uniform(1.2, 2.2), 1.2, lit=0.7, dark=0.55)
    for _ in range(3):                              # cold light through it
        wrap_blob(img, "water", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(1.6, 2.8), rnd.uniform(1.0, 1.8), 1.6,
                  lit=0.6, dark=0.5)
    speckle(img, "foliage", rnd, 14, 1.0, (-0.5, 0.8))
    return img


def t_ruin_cracked(seed):
    """Breakable masonry. It has to *look* breakable from across the screen, so
    the read is a block that has already failed: a fracture through the middle,
    both halves shifted, and the corners knocked off."""
    rnd = random.Random(seed)
    img = t_ruin_stone(seed + 700)
    for x in range(TS):                             # the shifted courses
        put(img, x, 7, "stone", 0.6)
        put(img, x, 8, "stone", 4.4)
    yy = 2
    for x in range(TS):                             # the fracture itself
        yy = max(1, min(13, yy + rnd.choice((-1, 0, 0, 1, 1))))
        put_ink(img, x, yy)
        put(img, x, yy + 1, "stone", 4.6)
        put(img, x, yy - 1, "stone", 1.2)
    for (cx, cy) in ((0, 0), (14, 0), (0, 14), (14, 14)):   # knocked corners
        for dx in range(2):
            for dy in range(2):
                if rnd.random() < 0.7:
                    put(img, cx + dx, cy + dy, "stone", 0.8)
    for _ in range(3):
        crack(img, "stone", rnd.randrange(2, 13), rnd.randrange(9, 13), 4, 2.4,
              rnd, drift=(-1, 0, 1))
    return img


# ------------------------------------------------------- 3. THERMAL HEIGHTS
# High rock, cloud decks, sun-bleached stone. Warm oranges into pale sky — but
# the warmth is put in the *backdrop*, and the tiles stay in dirt 2-4 (luma
# 58-100). The fish is a 156-209 orange and the bird an ember red, and a warm
# bright ledge would take both of them.
def t_heights_rock(seed, sun=False):
    """Weathered highland rock: horizontal strata with a lit lip on each, the
    way a wind-cut cliff actually breaks."""
    rnd = random.Random(seed)
    img = fill(tile(255), "dirt", 2.4, rnd, grain=0.30)
    # The first pass of this tile read as *planking*: level strata on a brown
    # ramp is a wall of boards. Two things fix it and both are about rock being
    # irregular — the bedding wanders and breaks, and half the surface is grey
    # mineral rather than brown, which is what "sun-bleached" means here.
    y = rnd.randrange(3)
    while y < TS:
        yy = y
        x = 0
        while x < TS:
            run = 2 + rnd.randrange(5)
            if rnd.random() < 0.22:                          # the bed pinches out
                x += run
                continue
            for k in range(run):
                px = x + k
                if px >= TS:
                    break
                put(img, px, yy, "dirt", 1.1 + rnd.uniform(-0.3, 0.3))
                if yy + 1 < TS:
                    put(img, px, yy + 1, "dirt", 3.9 + rnd.uniform(-0.3, 0.3))
            x += run
            yy = max(0, min(TS - 2, yy + rnd.choice((-1, 0, 0, 1))))
        y += 3 + rnd.randrange(3)
    for _ in range(7):                              # grey mineral, the bleach
        wrap_blob(img, "stone", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(1.8, 3.4), rnd.uniform(1.2, 2.2),
                  rnd.uniform(2.2, 3.2), lit=1.1, dark=0.9)
    for _ in range(5):                              # nodules in the rock
        wrap_blob(img, "dirt", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(1.2, 2.2), rnd.uniform(0.9, 1.5), 2.2)
    crack(img, "dirt", rnd.randrange(TS), rnd.randrange(2, 12), 7, 2.4, rnd)
    speckle(img, "stone", rnd, 14, 2.6, (-0.9, 0.9))
    if sun:
        # The sun-bleached crust. Two pixels of it, no more: `metal` 5-6 is
        # luma 180-239, which is the fish's own highlight, so it may be a line
        # and never a face.
        for x in range(TS):
            put(img, x, 0, "metal", 5.2 + rnd.uniform(-0.4, 0.4))
            put(img, x, 1, "stone", 4.8 + rnd.uniform(-0.4, 0.4))
            h = 2 + (1 if rnd.random() < 0.5 else 0)
            for y in range(2, 2 + h):
                put(img, x, y, "stone", 3.8 - (y - 2) * 0.9)
        for _ in range(4):                          # the crust flaking away
            x = rnd.randrange(TS)
            for k in range(rnd.randrange(1, 3)):
                put(img, x + k, 0, "dirt", 2.0)
    return img


def t_heights_wall(seed):
    """Background cliff. Warm, but two steps down and with the strata softened
    — it is the air between you and it that you are meant to read."""
    rnd = random.Random(seed)
    img = fill(tile(255), "dirt", 0.55, rnd, grain=0.24)
    for _ in range(5):
        wrap_blob(img, "stone", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(2.2, 4.2), rnd.uniform(1.6, 3.0), 0.9,
                  lit=0.6, dark=0.45)
    y = rnd.randrange(4)
    while y < TS:
        for x in range(TS):
            if rnd.random() < 0.6:
                put(img, x, y, "dirt", 0.1)
                put(img, x, y + 1, "stone", 1.3)
        y += 5 + rnd.randrange(3)
    speckle(img, "stone", rnd, 12, 0.9, (-0.4, 0.6))
    return img


def t_heights_scree(seed):
    """Loose slope: nothing but broken stone, each piece with its own lit face
    and its own shadow. No bevel — scree tiles in a mass."""
    rnd = random.Random(seed)
    img = fill(tile(255), "dirt", 1.8, rnd, grain=0.24)
    for _ in range(14):
        wrap_blob(img, "stone", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(1.0, 2.2), rnd.uniform(0.8, 1.6),
                  rnd.uniform(1.8, 3.0))
    for _ in range(6):
        wrap_blob(img, "dirt", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(0.9, 1.7), rnd.uniform(0.7, 1.3), 3.2)
    speckle(img, "stone", rnd, 16, 2.2, (-0.9, 0.9))
    return img


def t_heights_air(seed):
    """The pale fill for a room the parallax cannot reach — a gallery cut into
    the cliff, with nothing behind it but sky. Bright, and therefore flat:
    every step of structure in here is a step stolen from the tiles in front.

    Kaya Refit phase 3 re-valued it (it sat at the value of her straw hat);
    the painting lives in tools/art/tiles_p3.py."""
    return tiles_p3.t_heights_air_refit(seed)


def t_heights_stack(seed):
    """A basalt stack standing behind the play field: columnar jointing, which
    is the one rock formation that is unmistakable in sixteen pixels."""
    rnd = random.Random(seed)
    # The cleft between two stacks is a *shadow*, not a strip of sky. The first
    # pass painted it `metal` 4.0 — luma 140, which is the frog's own band —
    # and a 2 px bright stripe every 16 px is exactly the kind of repeating
    # highlight a green sprite disappears into.
    img = fill(tile(255), "stone", 1.1, rnd, grain=0.16)
    edges = [1, 5, 8, 12, 15]
    for i in range(len(edges) - 1):
        x0, x1 = edges[i], edges[i + 1]
        for x in range(x0, x1):
            for y in range(TS):
                lvl = 1.7
                if x == x0:
                    lvl -= 1.0                      # joint between columns
                elif x == x0 + 1:
                    lvl += 1.4                      # lit shoulder
                elif x == x1 - 1:
                    lvl -= 0.7
                put(img, x, y, "stone", lvl + rnd.uniform(-0.25, 0.25))
    for _ in range(3):                              # horizontal cooling breaks
        y = rnd.randrange(TS)
        for x in range(1, 15):
            put(img, x, y, "stone", 0.6)
            if y + 1 < TS:
                put(img, x, y + 1, "stone", 2.6)
    for _ in range(3):                              # warm dust on the windward side
        wrap_blob(img, "dirt", rnd.randrange(1, 15), rnd.randrange(TS),
                  rnd.uniform(1.2, 2.2), rnd.uniform(1.6, 3.0), 2.0,
                  lit=0.7, dark=0.6)
    return img


def t_heights_plank(seed):
    """One-way walkway: sun-dried timber lashed to two pegs. Grey rather than
    golden — this is wood that has been in the sun for thirty years."""
    rnd = random.Random(seed)
    img = tile(0)
    for x in range(TS):
        put(img, x, 0, "metal", 4.6 + rnd.uniform(-0.25, 0.25))
        put(img, x, 1, "wood", 3.4 + rnd.uniform(-0.3, 0.3))
        put(img, x, 2, "wood", 2.0 + rnd.uniform(-0.3, 0.3))
        put_ink(img, x, 3)
    for sx in (5, 11):
        for y in range(1, 3):
            put(img, sx, y, "wood", 1.0)
    for x in range(TS):                             # split grain
        if rnd.random() < 0.2:
            put(img, x, 1, "wood", 4.4)
    for px in (2, 13):                              # lashings
        for y in range(0, 3):
            put(img, px, y, "dirt", 2.2)
    return img


def t_heights_vent(seed):
    """The hazard: a fumarole. A cracked plate with heat coming off it, and the
    heat is the only ember in the world's tiles — which is what makes it read
    as the thing that hurts."""
    rnd = random.Random(seed)
    img = tile(0)
    for x in range(TS):
        put(img, x, 12, "dirt", 3.4 + rnd.uniform(-0.3, 0.3))
        put(img, x, 13, "dirt", 2.0 + rnd.uniform(-0.3, 0.3))
        put(img, x, 14, "dirt", 1.2 + rnd.uniform(-0.3, 0.3))
        put_ink(img, x, 15)
    for cx in (3, 8, 13):                           # the throats
        for y in range(11, 14):
            for dx in (-1, 0, 1):
                put(img, cx + dx, y, "ember", 5.4 - abs(dx) * 1.2)
        for k in range(rnd.randrange(5, 9)):        # the plume
            y = 11 - k
            if y < 0:
                break
            wdt = 1 + k // 3
            for dx in range(-wdt, wdt + 1):
                if rnd.random() < 0.55:
                    put(img, cx + dx, y, "ember", 5.8 - k * 0.5)
    return img


def t_heights_chain(seed):
    """The climbable: an anchored chain. Metal, so it cannot be confused with
    anything growing, and links rather than a line so it reads at 16px."""
    rnd = random.Random(seed)
    img = tile(0)
    for y in range(TS):
        k = y % 4
        if k in (0, 2):                             # the flat of a link
            for dx in (-2, -1, 0, 1, 2):
                put(img, 8 + dx, y, "metal", 4.6 - abs(dx) * 0.8)
        else:                                       # its sides
            put(img, 6, y, "metal", 4.2)
            put(img, 10, y, "metal", 2.0)
        put(img, 7, y, "metal", 5.2 if k in (0, 2) else 3.4)
        put(img, 9, y, "metal", 1.8)
    for y in range(TS):                             # the wall it hangs from
        if rnd.random() < 0.18:
            put(img, 8 + rnd.choice((-4, 4)), y, "dirt", 2.2)
    return img


def t_heights_basalt(seed):
    """The hard, dark block of the world: cooled columnar basalt, cut square.
    It is the *floor* of the luma band, which is what gives a level somewhere
    to put a wall that is unmistakably not the sky."""
    rnd = random.Random(seed)
    img = fill(tile(255), "stone", 1.3, rnd, grain=0.22, bevel=block_bevel)
    for x0 in (1, 6, 11):
        for y in range(TS):
            put(img, x0, y, "stone", 0.3)
            put(img, x0 + 1, y, "stone", 2.6 + rnd.uniform(-0.2, 0.2))
    for _ in range(4):                              # iron staining in the joints
        wrap_blob(img, "dirt", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(0.9, 1.6), rnd.uniform(0.8, 1.3), 2.0,
                  lit=0.7, dark=0.6)
    return img


def t_heights_cloud(seed):
    """The cloud deck, as a *tile*: what a level lays down when the floor gives
    out and there is nothing below but weather. Pale, and almost structureless
    for the same reason t_heights_air() is. Re-valued with it in phase 3."""
    return tiles_p3.t_heights_cloud_refit(seed)


def t_heights_shell(seed):
    """Breakable: sun-cracked crust over a void. The crack pattern is the tell,
    and it is drawn dark on a light face so it survives the haze."""
    rnd = random.Random(seed)
    img = t_heights_rock(seed + 700)
    cx, cy = 7 + rnd.randrange(-2, 3), 7 + rnd.randrange(-2, 3)
    for ang in range(0, 360, 45):
        a = math.radians(ang + rnd.randrange(-12, 13))
        x, y = float(cx), float(cy)
        for _ in range(8):
            x += math.cos(a)
            y += math.sin(a)
            put_ink(img, int(round(x)), int(round(y)))
            put(img, int(round(x)), int(round(y)) + 1, "dirt", 4.6)
    blob(img, "dirt", cx, cy, 2.2, 2.0, 1.0)
    for (ox, oy) in ((0, 0), (14, 0), (0, 14), (14, 14)):
        for dx in range(2):
            for dy in range(2):
                if rnd.random() < 0.6:
                    put(img, ox + dx, oy + dy, "dirt", 1.0)
    return img


# --------------------------------------------------------- 4. TERMITE DEEPS
# Chitin, packed earth, fungal glow. Dark browns with a luminous accent, and
# the accent is **violet**: a boss arena that is dark needs the player's
# silhouette to survive, and green would take the frog, amber would take the
# fish and red would take the bird. `purple` is the one ramp no form uses.
def t_deep_earth(seed, crust=False):
    """Packed spoil. Termites build out of what they chew, so this is earth
    with the grain of having been *placed* — layered, and studded with the
    grit that would not pack down."""
    rnd = random.Random(seed)
    img = fill(tile(255), "dirt", 2.3, rnd, grain=0.28)
    for _ in range(7):
        wrap_blob(img, "dirt", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(1.6, 3.0), rnd.uniform(1.0, 2.0), 1.8)
    for _ in range(5):                              # grey grit, off the brown
        wrap_blob(img, "stone", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(1.2, 2.4), rnd.uniform(0.9, 1.6), 2.4,
                  lit=1.0, dark=0.8)
    for _ in range(6):                              # chewed grit
        wrap_blob(img, "wood", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(0.9, 1.7), rnd.uniform(0.8, 1.3), 2.6,
                  lit=1.1, dark=0.8)
    for _ in range(2):
        crack(img, "dirt", rnd.randrange(TS), rnd.randrange(2, 13), 6, 2.0, rnd)
    speckle(img, "stone", rnd, 16, 2.4, (-0.9, 0.9))
    return img


def t_deep_crust(seed):
    """The ledge you stand on: packed spoil capped with a chitin crust, the
    plates overlapping the way a carapace does. The crust is `wood` 2-4 with a
    single amber lip, which keeps the whole tile under luma 90 and leaves the
    frog and the fish room to read against it."""
    rnd = random.Random(seed)
    img = t_deep_earth(seed + 100)
    x = 0
    while x < TS:
        wdt = 3 + rnd.randrange(3)
        h = 2 + (1 if rnd.random() < 0.5 else 0)
        for k in range(wdt):
            px = x + k
            if px >= TS:
                break
            for y in range(h):
                put(img, px, y, "wood", 4.0 - y * 1.1)
            put(img, px, h, "wood", 0.6)            # the plate's own shadow
        if x + wdt <= TS:
            put(img, min(TS - 1, x + wdt - 1), 0, "gold", 3.6)   # amber lip
        x += wdt
    for _ in range(3):                              # crumbs off the edge
        px = rnd.randrange(TS)
        for k in range(rnd.randrange(1, 3)):
            put(img, px, 3 + k, "wood", 1.6)
    return img


def t_deep_comb(seed):
    """Background comb. The termites' own masonry: a lattice of cells, held
    dark, with the odd cell still lit from inside by whatever lives there."""
    rnd = random.Random(seed)
    img = fill(tile(255), "dirt", 0.22, rnd, grain=0.16)
    y_off, x_off = rnd.randrange(5), rnd.randrange(6)
    for cy in range(-5 + y_off, TS, 5):
        off = x_off + (0 if (cy // 5) % 2 == 0 else 3)
        for cx in range(-6, TS + 6, 6):
            x, y = cx + off, cy
            # A rounded cell, four across, with its own lit upper-left rim and
            # its own occluded floor — not a box, or a row of them merges into
            # a rib and the whole wall reads as planking.
            for (dx, dy) in ((1, 0), (2, 0), (0, 1), (3, 1),
                             (0, 2), (3, 2), (1, 3), (2, 3)):
                put(img, (x + dx) % TS, y + dy, "wood", 1.0)
            for (dx, dy) in ((1, 1), (2, 1), (1, 2), (2, 2)):
                put(img, (x + dx) % TS, y + dy, "dirt", 0.0)    # the cell
            for (dx, dy) in ((1, 0), (2, 0), (0, 1)):           # lit rim
                put(img, (x + dx) % TS, y + dy, "wood", 2.8)
            for (dx, dy) in ((3, 2), (1, 3), (2, 3)):           # its shadow
                put(img, (x + dx) % TS, y + dy, "dirt", 0.4)
            if rnd.random() < 0.14:                             # one lit cell
                put(img, (x + 1) % TS, y + 1, "purple", 3.4)
                put(img, (x + 2) % TS, y + 2, "purple", 2.4)
    speckle(img, "dirt", rnd, 10, 0.4, (-0.3, 0.6))
    return img


def t_deep_chitin(seed):
    """A plate of hard chitin, cut as a block. Ribbed, with the ribs lit along
    their upper shoulder and an amber bloom where the plate is thin."""
    rnd = random.Random(seed)
    img = fill(tile(255), "wood", 1.6, rnd, grain=0.22, bevel=block_bevel)
    for y0 in (1, 6, 11):
        for x in range(TS):
            put(img, x, y0, "wood", 3.4 + rnd.uniform(-0.25, 0.25))
            put(img, x, y0 + 1, "wood", 2.4)
            put(img, x, y0 + 3, "wood", 0.7)
    for _ in range(3):                              # amber where it is thin
        wrap_blob(img, "gold", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(1.0, 1.8), rnd.uniform(0.7, 1.2), 2.2,
                  lit=0.8, dark=0.6)
    for _ in range(2):
        crack(img, "wood", rnd.randrange(TS), rnd.randrange(2, 12), 5, 1.6, rnd)
    return img


def t_deep_void(seed):
    """The tunnel void. The darkest fill in the game, and it has to be: the
    Brood Queen's arena is unlit, and the only thing that makes a silhouette
    readable there is having nothing behind it."""
    rnd = random.Random(seed)
    img = fill(tile(255), "dirt", 0.18, rnd, grain=0.16)
    speckle(img, "dirt", rnd, 10, 0.4, (-0.2, 0.7))
    if rnd.random() < 0.5:                          # one spore drifting in it
        put(img, rnd.randrange(TS), rnd.randrange(TS), "purple", 2.4)
    return img


def t_deep_root(seed):
    """A great root coming down through the nest, drawn as background. The one
    vertical in the world that is not chitin."""
    rnd = random.Random(seed)
    img = fill(tile(255), "dirt", 0.5, rnd, grain=0.18)
    # The root wanders and swells instead of running straight down: a constant
    # width on a wood ramp is a fence post, and that is what the first pass of
    # this tile came out as.
    cx = 8.0 + rnd.uniform(-1.5, 1.5)
    for y in range(TS):
        cx += math.sin(y / 5.0 + seed) * 0.45
        half = 4.0 + 1.3 * math.sin(y / 3.5 + seed * 0.7)
        lo, hi = int(round(cx - half)), int(round(cx + half))
        for x in range(lo, hi + 1):
            t = (x - lo) / float(max(1, hi - lo))
            lvl = 2.0 + (1.4 if t < 0.2 else (-1.2 if t > 0.82 else 0.0))
            put(img, x, y, "wood", lvl + rnd.uniform(-0.25, 0.25))
        put_ink(img, hi + 1, y)
        if y % 4 == 1:                              # bark fissures, short
            for k in range(rnd.randrange(2, 5)):
                put(img, lo + 2 + k, y, "wood", 0.6)
    x0, wdt = int(cx) - 4, 9
    for _ in range(2):                              # rootlets off the side
        y = rnd.randrange(TS)
        side = rnd.choice((-1, 1))
        px = x0 if side < 0 else x0 + wdt - 1
        for k in range(rnd.randrange(2, 4)):
            put(img, px + side * (k + 1), y + k // 2, "wood", 1.4)
    return img


def t_deep_shelf(seed):
    """One-way shelf: a single overlapping chitin plate, cantilevered, with the
    hard line under it that says nothing holds it from below."""
    rnd = random.Random(seed)
    img = tile(0)
    for x in range(TS):
        put(img, x, 0, "wood", 4.0 + rnd.uniform(-0.25, 0.25))
        put(img, x, 1, "wood", 2.8 + rnd.uniform(-0.3, 0.3))
        put(img, x, 2, "wood", 1.6 + rnd.uniform(-0.3, 0.3))
        put_ink(img, x, 3)
    for sx in (3, 9, 14):                           # where plates overlap
        for y in range(0, 3):
            put(img, sx, y, "wood", 0.8)
        put(img, sx + 1, 0, "gold", 3.4)
    return img


def t_deep_spore(seed):
    """The hazard: a spore vent. Violet, like everything luminous down here, so
    the one warm thing on screen is never the thing that hurts you — the amber
    lips on the chitin are, and confusing the two would be a defect."""
    rnd = random.Random(seed)
    img = tile(0)
    for x in range(TS):
        put(img, x, 12, "wood", 2.6 + rnd.uniform(-0.3, 0.3))
        put(img, x, 13, "wood", 1.6 + rnd.uniform(-0.3, 0.3))
        put(img, x, 14, "dirt", 1.0 + rnd.uniform(-0.3, 0.3))
        put_ink(img, x, 15)
    for cx in (3, 8, 13):
        blob(img, "wood", cx, 12.0, 2.4, 1.6, 2.4)
        for y in range(10, 13):                     # the mouth
            for dx in (-1, 0, 1):
                put(img, cx + dx, y, "purple", 4.4 - abs(dx) * 1.0)
        for k in range(rnd.randrange(4, 8)):        # spores coming out of it
            y = 9 - k
            if y < 0:
                break
            for dx in range(-(1 + k // 3), 2 + k // 3):
                if rnd.random() < 0.4:
                    put(img, cx + dx, y, "purple", 5.0 - k * 0.45)
    return img


def t_deep_ladder(seed):
    """The climbable: a hanging root. Wood, lit on one shoulder, with rootlets
    every few pixels so the eye can tell it is a thing and not a seam."""
    rnd = random.Random(seed)
    img = tile(0)
    x = 6
    for y in range(TS):
        x = max(4, min(9, x + rnd.choice((-1, 0, 0, 1))))
        put(img, x, y, "wood", 4.2)                 # lit shoulder
        put(img, x + 1, y, "wood", 3.0)
        put(img, x + 2, y, "wood", 1.8)
        put(img, x + 3, y, "wood", 0.8)
        put_ink(img, x + 4, y)
        if y % 3 == 1:                              # rootlets, both sides
            side = -1 if (y // 3) % 2 == 0 else 5
            for k in range(2 + rnd.randrange(2)):
                px = x + side + (k if side > 0 else -k)
                put(img, px, y + k // 2, "wood", 3.4 - k * 0.4)
                put(img, px, y + 1 + k // 2, "wood", 1.0)
            put(img, x + 1, y, "gold", 3.8)         # the grip, in amber
            put(img, x + 2, y + 1, "gold", 2.4)
    return img


def t_deep_fungus(seed):
    """Background fungus: the luminous accent, as a mat rather than a lamp.

    It is bright *for this world* and still under luma 130, and it is violet,
    which is the point: the Brood Queen's arena is unlit, and a glow the same
    hue as any form would put the player inside the wallpaper."""
    rnd = random.Random(seed)
    img = fill(tile(255), "dirt", 0.5, rnd, grain=0.18)
    for _ in range(7):                              # the caps
        cx, cy = rnd.randrange(TS), rnd.randrange(TS)
        rx, ry = rnd.uniform(1.6, 2.8), rnd.uniform(1.0, 1.8)
        wrap_blob(img, "purple", cx, cy, rx, ry, 2.2, lit=1.0, dark=0.8)
        for dx in (-TS, 0, TS):                     # the lit crown of each
            put(img, (cx + dx) % TS, (cy - int(ry)) % TS, "purple", 4.6)
    for _ in range(9):                              # mycelium threads
        x, y = rnd.randrange(TS), rnd.randrange(TS)
        for k in range(rnd.randrange(3, 7)):
            put(img, (x + k) % TS, (y + (k // 3)) % TS, "purple", 3.0)
    speckle(img, "purple", rnd, 10, 2.0, (-0.8, 0.9))
    return img


def t_deep_glowwall(seed):
    """Breakable, and the world's verb: the luminous wall the Brood Queen fight
    is about. Breaking it lights the arena and removes the cover you were
    standing behind, so it has to read as *both* — a wall, and a lamp.

    The fracture lines are drawn violet-bright rather than ink-dark, because
    this is the one breakable that is meant to be found in the dark."""
    rnd = random.Random(seed)
    img = fill(tile(255), "dirt", 1.0, rnd, grain=0.22, bevel=block_bevel)
    for _ in range(5):
        wrap_blob(img, "wood", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(1.4, 2.6), rnd.uniform(1.0, 1.8), 1.6)
    cx, cy = 7 + rnd.randrange(-1, 2), 7 + rnd.randrange(-1, 2)
    for ang in range(0, 360, 60):                   # the fracture, lit
        a = math.radians(ang + rnd.randrange(-14, 15))
        x, y = float(cx), float(cy)
        for k in range(7):
            x += math.cos(a)
            y += math.sin(a)
            put(img, int(round(x)), int(round(y)), "purple", 5.2 - k * 0.3)
            put(img, int(round(x)), int(round(y)) + 1, "purple", 1.6)
    blob(img, "purple", cx, cy, 2.0, 1.8, 4.4)
    for (ox, oy) in ((0, 0), (14, 0), (0, 14), (14, 14)):
        for dx in range(2):
            for dy in range(2):
                if rnd.random() < 0.55:
                    put(img, ox + dx, oy + dy, "dirt", 0.6)
    return img


def t_deep_packed(seed):
    """The secondary solid: earth rammed into a block, mortarless, the way the
    mound's structural walls are built. Squarer and darker than the spoil, so a
    level has a way to say 'this is architecture, not dirt'."""
    rnd = random.Random(seed)
    img = fill(tile(255), "dirt", 1.1, rnd, grain=0.2, bevel=block_bevel)
    for y0 in (0, 8):
        for x in range(TS):
            put(img, x, y0, "dirt", 2.6 + rnd.uniform(-0.2, 0.2))
            put(img, x, y0 + 7, "dirt", 0.3)
    for x0 in (0, 8):
        for y in range(TS):
            put(img, (x0 + 7) % TS, y, "dirt", 0.3)
    for _ in range(5):
        wrap_blob(img, "dirt", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(1.0, 1.8), rnd.uniform(0.8, 1.4), 1.8)
    for _ in range(2):
        wrap_blob(img, "wood", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(0.8, 1.4), rnd.uniform(0.6, 1.1), 2.0)
    return img


# ----------------------------------------------------- 5. THE OBSIDIAN NEST
# Volcanic glass, heat cracks, black and ember. The bulk is `stone` 0-1 and
# `purple` 0-1 (luma 22-40) — near black with a violet cast, which is what
# separates glass from the Deeps' brown. Ember never fills: it is a one-pixel
# crack network, because ember 4-6 is 107-200 and that is the bird and the fish.
def t_nest_glass(seed, hot=False):
    """Obsidian: conchoidal fracture, which in sixteen pixels means broad flat
    facets meeting at hard edges, each facet catching a different amount of
    light. The glare is the material — a black rock with no highlight reads as
    a hole."""
    rnd = random.Random(seed)
    img = fill(tile(255), "stone", 0.5, rnd, grain=0.16)
    facets = []
    for _ in range(5):
        facets.append((rnd.randrange(TS), rnd.randrange(TS),
                       rnd.uniform(3.0, 6.0), rnd.uniform(2.2, 4.5),
                       rnd.uniform(-0.55, 0.85)))
    for (cx, cy, rx, ry, dv) in facets:
        for dx in (-TS, 0, TS):
            for dy in (-TS, 0, TS):
                blob(img, "purple", cx + dx, cy + dy, rx, ry, 0.85 + dv,
                     lit=0.8, dark=0.5)
    for _ in range(4):                              # the hard fracture edges
        x, y = rnd.randrange(TS), rnd.randrange(TS)
        a = rnd.uniform(0, math.pi)
        fx, fy = float(x), float(y)
        for k in range(rnd.randrange(6, 12)):
            fx += math.cos(a)
            fy += math.sin(a)
            put(img, int(round(fx)) % TS, int(round(fy)) % TS, "stone", 2.4)
            put(img, int(round(fx)) % TS, (int(round(fy)) + 1) % TS,
                "stone", 0.1)
    for _ in range(3):                              # glare on a facet
        x, y = rnd.randrange(TS), rnd.randrange(TS)
        for k in range(rnd.randrange(2, 5)):
            put(img, (x + k) % TS, (y + k // 2) % TS, "metal", 4.2)
    if hot:
        # The crust of a flow that has not finished cooling. Ember, and only in
        # the cracks: a face of it would be the brightest thing on screen and
        # the bird is an ember-red sprite.
        for x in range(TS):
            put(img, x, 0, "stone", 2.0 + rnd.uniform(-0.3, 0.3))
            put(img, x, 1, "stone", 1.0 + rnd.uniform(-0.3, 0.3))
        y = 0
        for x in range(TS):                         # the hot seam under it
            y = max(0, min(4, y + rnd.choice((-1, 0, 0, 1))))
            put(img, x, y + 1, "ember", 5.6)
            put(img, x, y + 2, "ember", 3.4)
        for _ in range(3):                          # heat running down a crack
            x = rnd.randrange(TS)
            for k in range(rnd.randrange(3, 8)):
                put(img, x + (k % 2), 3 + k, "ember", 4.2 - k * 0.35)
    return img


def t_nest_wall(seed):
    """Background glass. The facets are still there but the glare is gone —
    what is behind you in the Nest is a wall you cannot read, which is the
    point of the place."""
    rnd = random.Random(seed)
    img = fill(tile(255), "stone", 0.12, rnd, grain=0.12)
    for _ in range(5):
        wrap_blob(img, "purple", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(2.6, 5.0), rnd.uniform(1.8, 3.2), 0.35,
                  lit=0.5, dark=0.35)
    for _ in range(2):
        x, y = rnd.randrange(TS), rnd.randrange(TS)
        a = rnd.uniform(0, math.pi)
        fx, fy = float(x), float(y)
        for _k in range(9):
            fx += math.cos(a)
            fy += math.sin(a)
            put(img, int(round(fx)) % TS, int(round(fy)) % TS, "stone", 1.3)
    speckle(img, "stone", rnd, 8, 0.4, (-0.2, 0.7))
    return img


def t_nest_block(seed):
    """Cut basalt: the Nest's masonry, and the only square thing in it. Two
    courses like the ruins, but the joints glow instead of holding water."""
    rnd = random.Random(seed)
    img = tile(255)
    for y in range(TS):
        jy = 0 if y < 8 else 8
        jx = 0 if y < 8 else 8
        for x in range(TS):
            if y == jy or x == jx:
                put(img, x, y, "ember", 0.9 + rnd.uniform(-0.3, 0.3))
                continue
            ly, lx = y - jy, (x - jx) % TS
            lvl = 1.5
            if ly == 1:
                lvl += 1.3
            elif ly == 7:
                lvl -= 0.9
            if lx == 1:
                lvl += 0.7
            elif lx == 15:
                lvl -= 0.8
            put(img, x, y, "stone", lvl + rnd.uniform(-0.25, 0.25))
    for _ in range(3):
        blob(img, "purple", rnd.randrange(2, 14), rnd.randrange(2, 14),
             rnd.uniform(1.0, 1.8), rnd.uniform(0.8, 1.4), 1.6)
    for _ in range(2):                              # one short live joint
        x = rnd.randrange(TS - 4)
        y = 0 if rnd.random() < 0.5 else 8
        for k in range(rnd.randrange(2, 5)):
            put(img, x + k, y, "ember", 4.0)
    return img


def t_nest_void(seed):
    """The void. Violet-black, so the Nest never reads as the Deeps even where
    both are nearly empty."""
    rnd = random.Random(seed)
    img = fill(tile(255), "purple", 0.2, rnd, grain=0.14)
    speckle(img, "purple", rnd, 9, 0.4, (-0.2, 0.7))
    if rnd.random() < 0.45:                         # one ember drifting
        put(img, rnd.randrange(TS), rnd.randrange(TS), "ember", 3.4)
    return img


def t_nest_flue(seed):
    """A flue standing behind the play field: a column of glass with the heat
    still running up the inside of it."""
    rnd = random.Random(seed)
    img = fill(tile(255), "purple", 0.25, rnd, grain=0.14)
    x0, wdt = 2, 12
    for x in range(x0, x0 + wdt):
        t = (x - x0) / float(wdt - 1)
        for y in range(TS):
            lvl = 1.1 + (1.1 if t < 0.2 else (-0.7 if t > 0.82 else 0.0))
            put(img, x, y, "stone", lvl + rnd.uniform(-0.22, 0.22))
    cx = x0 + wdt // 2
    for y in range(TS):                             # the heat inside it
        if rnd.random() < 0.7:
            put(img, cx + rnd.choice((-1, 0, 0, 1)), y, "ember", 3.2)
    for _ in range(3):
        x = rnd.randrange(x0, x0 + wdt)
        for y in range(TS):
            if rnd.random() < 0.4:
                put(img, x, y, "stone", 0.2)
    return img


def t_nest_ledge(seed):
    """One-way ledge: a slab of cooled flow, hot underneath where it has not
    finished giving up its heat."""
    rnd = random.Random(seed)
    img = tile(0)
    for x in range(TS):
        put(img, x, 0, "stone", 2.6 + rnd.uniform(-0.25, 0.25))
        put(img, x, 1, "stone", 1.4 + rnd.uniform(-0.3, 0.3))
        put(img, x, 2, "purple", 1.0 + rnd.uniform(-0.3, 0.3))
        put_ink(img, x, 3)
    for x in range(TS):                             # the glow on its underside
        if rnd.random() < 0.45:
            put(img, x, 2, "ember", 3.2)
    for sx in (6, 12):
        for y in range(0, 3):
            put(img, sx, y, "stone", 0.4)
    for x in (2, 9):                                # glare along the top
        put(img, x, 0, "metal", 4.4)
    return img


def t_nest_shard(seed):
    """The hazard: a field of obsidian shards standing point-up. Black, with a
    lit left flank and a hard ink edge on the right — the same trick the iron
    spikes use, because it is the only one that stops a triangle reading as a
    triangle."""
    rnd = random.Random(seed)
    img = tile(0)
    for x in range(TS):                             # the flow they grew out of
        put(img, x, 13, "stone", 1.8 + rnd.uniform(-0.3, 0.3))
        put(img, x, 14, "purple", 0.9 + rnd.uniform(-0.3, 0.3))
        put_ink(img, x, 15)
        if rnd.random() < 0.3:
            put(img, x, 14, "ember", 2.8)
    for cx in (2.5, 7.5, 12.5):
        top = 3 + rnd.randrange(2)
        for y in range(top, 14):
            half = (y - top) / float(13 - top) * 2.6
            lo, hi = int(math.floor(cx - half)), int(math.ceil(cx + half))
            for x in range(lo, hi + 1):
                if not 0 <= x < TS:
                    continue
                t = (x - cx) / max(half, 0.6)
                if abs(t) > 1.05:
                    continue
                put(img, x, y, "purple", 1.0 - t * 1.0)
                if t < -0.55:                       # the one lit facet
                    put(img, x, y, "stone", 2.2)
            put_ink(img, hi, y)
        # Hot points (Kaya Refit phase 3): the shards were the quietest hazard
        # in the game, dark glass on a dark wall. Glass this close to the
        # Nest's heat glows at the tip, and a glowing tip says "do not land".
        put(img, int(cx), top, "ember", 6.0)
        put(img, int(cx), top + 1, "ember", 5.0)
        put(img, int(cx) - 1, top + 1, "ember", 4.0)
        put(img, int(cx), top + 2, "ember", 3.0)
    return img


def t_nest_chain(seed):
    """The climbable: a chain of the Nest's own iron, hot where it has been
    hanging in the updraught."""
    rnd = random.Random(seed)
    img = tile(0)
    for y in range(TS):
        k = y % 4
        if k in (0, 2):
            for dx in (-2, -1, 0, 1, 2):
                put(img, 8 + dx, y, "metal", 3.8 - abs(dx) * 0.7)
        else:
            put(img, 6, y, "metal", 3.4)
            put(img, 10, y, "metal", 1.6)
        put(img, 7, y, "metal", 4.4 if k in (0, 2) else 2.8)
        put(img, 9, y, "metal", 1.4)
        if rnd.random() < 0.22:                     # the heat in the iron
            put(img, 8, y, "ember", 4.0)
    return img


def t_nest_vein(seed):
    """Background flow: dead glass with a live vein still running through it.
    A fill, so the vein is one pixel wide and the rest is under luma 40."""
    rnd = random.Random(seed)
    img = fill(tile(255), "stone", 0.45, rnd, grain=0.16)
    for _ in range(4):
        wrap_blob(img, "purple", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(2.4, 4.4), rnd.uniform(1.6, 2.8), 0.8,
                  lit=0.6, dark=0.4)
    for _ in range(3):                              # the veins
        x, y = rnd.randrange(TS), rnd.randrange(TS)
        a = rnd.uniform(0, math.pi)
        fx, fy = float(x), float(y)
        for k in range(rnd.randrange(7, 14)):
            fx += math.cos(a)
            fy += math.sin(a)
            a += rnd.uniform(-0.35, 0.35)
            put(img, int(round(fx)) % TS, int(round(fy)) % TS, "ember",
                3.0 if k % 3 else 4.0)
    speckle(img, "stone", rnd, 8, 0.5, (-0.2, 0.6))
    return img


def t_nest_plate(seed):
    """Riveted plate, as the Nest builds it: iron that has been in a furnace
    long enough to scale. The one tile in the world with a bright face, and it
    is bounded — a plate is an object, not a mass."""
    rnd = random.Random(seed)
    img = fill(tile(255), "metal", 2.0, rnd, grain=0.2, bevel=block_bevel)
    for y in range(2, 14):
        if y % 4 == 0:
            for x in range(TS):
                put(img, x, y, "metal", 1.0)
                put(img, x, y + 1, "metal", 3.0)
    for _ in range(5):                              # scale
        wrap_blob(img, "ember", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(1.0, 2.0), rnd.uniform(0.8, 1.5), 1.8,
                  lit=0.8, dark=0.6)
    for (rx, ry) in ((2, 3), (13, 3), (2, 12), (13, 12)):
        blob(img, "metal", rx, ry, 1.6, 1.6, 2.6)
    return img


def t_nest_crust(seed):
    """Breakable: a bubble in the flow, thin enough to put a boot through. The
    tell is the ring of hot cracks around a dark centre."""
    rnd = random.Random(seed)
    img = t_nest_glass(seed + 700)
    cx, cy = 7 + rnd.randrange(-1, 2), 7 + rnd.randrange(-1, 2)
    blob(img, "stone", cx, cy, 4.2, 3.8, 0.2, lit=0.4, dark=0.3)
    for ang in range(0, 360, 30):                   # the ring
        a = math.radians(ang)
        px = int(round(cx + math.cos(a) * 4.4))
        py = int(round(cy + math.sin(a) * 3.9))
        put(img, px, py, "ember", 4.4)
        put(img, px, py + 1, "ember", 2.0)
    for ang in range(0, 360, 90):                   # and the cracks off it
        a = math.radians(ang + rnd.randrange(-20, 21))
        fx, fy = cx + math.cos(a) * 4.4, cy + math.sin(a) * 3.9
        for k in range(4):
            fx += math.cos(a)
            fy += math.sin(a)
            put(img, int(round(fx)), int(round(fy)), "ember", 3.4 - k * 0.5)
    return img



# ---------------------------------------------------------------- registry
TILE_DEFS = []


def T(img):
    assert img.size == (TS, TS), img.size
    TILE_DEFS.append(img)


T(tile(0))                                            # 0  empty
T(t_dirt(11))                                         # 1  dirt
T(t_grass_top(12))                                    # 2  grass top
T(t_stone(21))                                        # 3  stone
T(t_stone(22, mossy=True))                            # 4  stone top (mossy)
T(t_platform(5))                                      # 5  wood one-way platform
T(auto_shade(VINE_ROWS, VINE_MAP, depth=2, lit=1.3))  # 6  vine ladder
T(t_water(31, surface=True))                          # 7  water surface
T(t_water(32))                                        # 8  water body
T(t_spikes(9))                                        # 9  spikes
T(t_crate(7))                                         # 10 crate (breakable)
T(t_switch("gold", True, 11, _diamond()))             # 11 switch block A (on)
T(t_switch("purple", True, 12, _square()))            # 12 switch block B (on)
T(t_bg_leaves(41))                                    # 13 background leaves
T(t_trunk(14))                                        # 14 tree trunk
T(t_bg_rock(51))                                      # 15 background rock
T(t_grass_edge(13, "left"))                           # 16 grass left edge
T(t_grass_edge(14, "right"))                          # 17 grass right edge
T(t_bg_dark(61))                                      # 18 dark background fill
T(t_bridge(19))                                       # 19 rope bridge
T(t_hub_grass(71))                                    # 20 hub grass
T(t_hub_path(72))                                     # 21 hub path
T(t_hub_water(73))                                    # 22 hub water
T(t_hub_tree(74))                                     # 23 hub tree canopy
T(t_lava(24))                                         # 24 lava / hot rock
T(t_metal(25))                                        # 25 metal plate
T(t_switch("gold", False, 26, _diamond()))            # 26 switch block A (off)
T(t_switch("purple", False, 27, _square()))           # 27 switch block B (off)


# ---------------------------------------------------------- worlds 2-5 ids
# Ids 220-399 are the four new worlds (M2-M5). They are placed *by index*
# rather than appended, because the id ranges are an interface between agents
# working in parallel: 200-219 belongs to the new movement verbs, 220-399 to
# the tilesets below. A gap is a blank atlas cell that no level and no manifest
# ever names, which costs 256 bytes of texture and buys the guarantee that
# nobody has to renumber anything that has already shipped.
def T_AT(tid, img):
    """Place a tile at an explicit atlas index, padding the gap before it."""
    assert img.size == (TS, TS), img.size
    assert tid >= len(TILE_DEFS), (
        "tile %d would overwrite an id already placed" % tid)
    while len(TILE_DEFS) < tid:
        TILE_DEFS.append(tile(0))
    TILE_DEFS.append(img)


# ------------------------------------------------------------- movement verbs
# Ids 200-219 are the verbs added for worlds 2-4: currents, drafts and walls you
# can break. They are painted here rather than by the agent that gave them
# behaviour, because that agent owns flags and numbers and this file owns pixels.
# A verb you cannot SEE is a verb that reads as a bug: a current has to announce
# which way it pushes before it pushes you, or the room is unfair.

def t_current(seed, dx, dy, fast=False):
    """Water with chevrons running the way it pushes."""
    img = t_water(seed)
    rnd = random.Random(seed + 7)
    n = 3 if fast else 2
    for i in range(n):
        off = rnd.randrange(TS)
        for k in range(-3, 4):
            a = abs(k)
            if dx:
                x = (off + k * (1 if dx > 0 else -1)) % TS
                y = (off * 5 + 4 + i * 6 + a) % TS
                put(img, x, y, "water", 6.4 if fast else 5.9)
                put(img, (x - (1 if dx > 0 else -1)) % TS, y, "water", 5.2)
            else:
                y = (off + k * (1 if dy > 0 else -1)) % TS
                x = (off * 5 + 4 + i * 6 + a) % TS
                put(img, x, y, "water", 6.4 if fast else 5.9)
                put(img, x, (y - (1 if dy > 0 else -1)) % TS, "water", 5.2)
    return img


def t_draft(seed, dy, strong=False, sideways=0):
    """Moving air. Mostly transparent — it sits in front of the backdrop."""
    img = tile(0)
    rnd = random.Random(seed)
    streaks = 5 if strong else 3
    for i in range(streaks):
        x = rnd.randrange(TS)
        y = rnd.randrange(TS)
        run = rnd.randrange(4, 9)
        for k in range(run):
            lvl = 6.6 - abs(k - run * 0.5) * 0.35
            if sideways:
                px, py = (x + k * sideways) % TS, (y + (k // 5)) % TS
            else:
                px, py = (x + (k // 4)) % TS, (y + k * (1 if dy > 0 else -1)) % TS
            put(img, px, py, "cloth", lvl, alpha=150 if strong else 110)
    return img


def t_cracked(seed, base):
    """A wall the blade can open. The cracks are the tell."""
    img = t_stone(seed) if base == "stone" else t_dirt(seed)
    rnd = random.Random(seed + 3)
    ramp = "stone" if base == "stone" else "dirt"
    for _ in range(3):
        crack(img, ramp, rnd.randrange(2, TS - 2), rnd.randrange(1, 5),
              rnd.randrange(6, 11), 1.4, rnd)
    return img


def t_termite_wall(seed):
    img = t_dirt(seed)
    rnd = random.Random(seed + 5)
    for _ in range(14):                       # chewed cells
        wrap_blob(img, "dirt", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(0.9, 1.8), rnd.uniform(0.8, 1.5), 2.2,
                  lit=0.7, dark=1.5)
    return img


def t_luminous_wall(seed):
    """Breakable, and the only light in a dark room — so breaking it is a
    choice, not a freebie."""
    img = t_stone(seed, mossy=False)
    rnd = random.Random(seed + 9)
    for _ in range(3):
        x, y = rnd.randrange(2, TS - 2), rnd.randrange(2, TS - 2)
        for k in range(rnd.randrange(4, 8)):
            put(img, (x + k) % TS, (y + (k // 2)) % TS, "gold", 6.5)
            put(img, (x + k) % TS, (y + (k // 2) + 1) % TS, "gold", 4.6)
    return img


def t_rubble(seed):
    """What a broken wall leaves. Not solid; it is dressing."""
    img = tile(0)
    rnd = random.Random(seed)
    for _ in range(9):
        x, y = rnd.randrange(TS), rnd.randrange(10, TS)
        blob(img, "stone", x, y, rnd.uniform(0.8, 1.6), rnd.uniform(0.7, 1.2), 3.0)
    return img


T_AT(200, t_current(2001, 1, 0))                      # water current, east
T_AT(201, t_current(2011, -1, 0))                     # water current, west
T_AT(202, t_current(2021, 0, -1))                     # water current, up
T_AT(203, t_current(2031, 0, 1))                      # water current, down
T_AT(204, t_current(2041, 1, 0, fast=True))           # fast current, east
T_AT(205, t_current(2051, -1, 0, fast=True))          # fast current, west
T_AT(206, t_draft(2061, -1))                          # updraft
T_AT(207, t_draft(2071, -1, strong=True))             # strong updraft
T_AT(208, t_draft(2081, 1))                           # downdraft
T_AT(209, t_draft(2091, 0, sideways=1))               # gust, east
T_AT(210, t_draft(2101, 0, sideways=-1))              # gust, west
T_AT(211, t_cracked(2111, "stone"))                   # cracked stone
T_AT(212, t_cracked(2121, "dirt"))                    # cracked dirt
T_AT(213, t_termite_wall(2131))                       # termite wall
T_AT(214, t_luminous_wall(2141))                      # luminous wall
T_AT(215, t_rubble(2151))                             # rubble


# The void tile of each new world (224, 244, 264, 284) is painted empty and
# flagged see_through in data/tiles.json: it is where the world's parallax
# backdrop shows. Back-walls stay solid art, so caves still read as enclosed.
# 2. SUNKEN RUINS
T_AT(220, t_ruin_stone(2201))                         # waterlogged ashlar
T_AT(221, t_ruin_stone(2211, algae=True))             # ... capped with algae
T_AT(222, t_ruin_wall(2221))                          # background masonry
T_AT(223, t_ruin_silt(2231))                          # cold silt
T_AT(224, tile(0))  # flooded void: see-through, the world's parallax shows here
T_AT(225, t_ruin_column(2251))                        # fluted column (bg)
T_AT(226, t_ruin_slab(2261))                          # one-way slab
T_AT(227, t_ruin_urchin(2271))                        # urchins (hazard)
T_AT(228, t_ruin_grate(2281))                         # iron grate
T_AT(229, t_kelp(2291))                               # kelp (climbable)
T_AT(230, t_ruin_algae(2301))                         # background algae mat
T_AT(231, t_ruin_cracked(2311))                       # cracked block (breakable)

# 3. THERMAL HEIGHTS
T_AT(240, t_heights_rock(2401))                       # highland rock
T_AT(241, t_heights_rock(2411, sun=True))             # ... sun-bleached crust
T_AT(242, t_heights_wall(2421))                       # background cliff
T_AT(243, t_heights_scree(2431))                      # loose scree
T_AT(244, tile(0))  # pale sky fill (bg): see-through, the world's parallax shows here
T_AT(245, t_heights_stack(2451))                      # basalt stack (bg)
T_AT(246, t_heights_plank(2461))                      # one-way walkway
T_AT(247, t_heights_vent(2471))                       # fumarole (hazard)
T_AT(248, t_heights_chain(2481))                      # chain (climbable)
T_AT(249, t_heights_basalt(2491))                      # cut basalt block
T_AT(250, t_heights_cloud(2501))                      # cloud deck (bg)
T_AT(251, t_heights_shell(2511))                      # cracked crust (breakable)

# 4. TERMITE DEEPS
T_AT(260, t_deep_earth(2601))                         # packed spoil
T_AT(261, t_deep_crust(2611))                         # ... capped with chitin
T_AT(262, t_deep_comb(2621))                          # background comb
T_AT(263, t_deep_chitin(2631))                        # chitin plate block
T_AT(264, tile(0))  # tunnel void (bg): see-through, the world's parallax shows here
T_AT(265, t_deep_root(2651))                          # great root (bg)
T_AT(266, t_deep_shelf(2661))                         # one-way chitin shelf
T_AT(267, t_deep_spore(2671))                         # spore vent (hazard)
T_AT(268, t_deep_ladder(2681))                        # hanging root (climbable)
T_AT(269, t_deep_fungus(2691))                        # fungus mat (bg, glowing)
T_AT(270, t_deep_glowwall(2701))                      # luminous wall (breakable)
T_AT(271, t_deep_packed(2711))                        # rammed-earth block

# 5. THE OBSIDIAN NEST
T_AT(280, t_nest_glass(2801))                         # obsidian
T_AT(281, t_nest_glass(2811, hot=True))               # ... still cooling
T_AT(282, t_nest_wall(2821))                          # background glass
T_AT(283, t_nest_block(2831))                         # cut basalt masonry
T_AT(284, tile(0))  # the void (bg): see-through, the world's parallax shows here
T_AT(285, t_nest_flue(2851))                          # flue (bg)
T_AT(286, t_nest_ledge(2861))                         # one-way ledge
T_AT(287, t_nest_shard(2871))                         # obsidian shards (hazard)
T_AT(288, t_nest_chain(2881))                         # chain (climbable)
T_AT(289, t_nest_vein(2891))                          # ember-veined flow (bg)
T_AT(290, t_nest_plate(2901))                         # riveted plate
T_AT(291, t_nest_crust(2911))                         # bubble crust (breakable)



# Kaya Refit phase 3: every ladder, one-way and hazard is inked — see
# tiles_p3.ink_interactive(). Done here, once every id is placed, and again to
# each variant interior in _cases_for(), so variant 0 still equals the base.
for _tid in sorted(tiles_p3.INKED):
    tiles_p3.ink_interactive(TILE_DEFS[_tid])


# ================================================================== phase 2
# Tile variety and autotiling — docs/art-direction.md phase 2.
#
# Phase 1 ended with a corollary it could not act on: a fill tile has exactly
# one variant, so any structure strong enough to *read* also repeats visibly
# across a whole screen. The hub grass proved it — authored tufts turned the
# overworld into a perfect lattice. The fix is more tiles, not weaker tiles.
#
# Two mechanisms, and both are **derived** rather than authored, so
# `levels/*.json` and `tools/build_levels.py` do not change:
#
#   random variants   several interchangeable paintings of one fill tile,
#                     picked by a hash of the tile's position at load. Stable
#                     across frames and reloads, so nothing shimmers.
#   autotiling        the 47-case blob set per terrain material, resolved from
#                     the eight neighbours at load. A mass of terrain grows a
#                     sunlit crest, an occluded underside, lit cheeks and
#                     inside corners instead of reading as a rectangle.
#
# Everything is appended to the same atlas after the 28 gameplay ids, and
# `assets/tiles/variants.json` tells the engine which cell to draw. A variant
# is never a gameplay id: `TileWorld` still stores the authored id, so
# `is_solid()` and every collision test see exactly the array they saw before.

# The first free atlas cell after the gameplay ids. It is 400 rather than 32
# because data/tiles.json now reaches to 399: 200-219 for the new movement
# verbs and 220-399 for the four new worlds' tilesets below. Moving it costs
# blank cells for the ids nobody has claimed - 23 atlas rows, 23 KB of
# texture - and is what lets every id below it stay exactly where the shipped
# levels expect to find it.
VARIANT_BASE = 400

# Neighbour bits, clockwise from north.
BIT_N, BIT_NE, BIT_E, BIT_SE = 1, 2, 4, 8
BIT_S, BIT_SW, BIT_W, BIT_NW = 16, 32, 64, 128
MASK_FULL = 255             # every neighbour is the same material: interior


def canon_mask(raw):
    """Reduce a raw eight-neighbour mask to one of the 47 blob cases.

    A diagonal neighbour only changes how a tile is drawn when both cardinals
    beside it are also present — otherwise the edge along that side already
    covers the corner. That reduction is what turns 256 combinations into the
    47 the blob set actually needs.
    """
    m = raw & (BIT_N | BIT_E | BIT_S | BIT_W)
    if raw & BIT_N and raw & BIT_E and raw & BIT_NE:
        m |= BIT_NE
    if raw & BIT_E and raw & BIT_S and raw & BIT_SE:
        m |= BIT_SE
    if raw & BIT_S and raw & BIT_W and raw & BIT_SW:
        m |= BIT_SW
    if raw & BIT_W and raw & BIT_N and raw & BIT_NW:
        m |= BIT_NW
    return m


BLOB_CASES = sorted({canon_mask(raw) for raw in range(256)})
assert len(BLOB_CASES) == 47, "the blob set is 47 cases, got %d" % len(BLOB_CASES)


# ---------------------------------------------------------------- rim paint
# The fills are already rendered to pixels, so an edge is painted by
# *overdrawing* a band at an explicit level rather than by shading what is
# underneath. That is how t_grass_edge() has always drawn its cliff face; this
# generalises it to all four sides and to the corners.
def _band_pixel(side, k, i):
    if side == "top":
        return i, k
    if side == "bottom":
        return i, TS - 1 - k
    if side == "left":
        return k, i
    return TS - 1 - k, i


def rim_band(img, ramp, rnd, side, base, deltas, jitter=0.28, ragged=0.0,
             broken=0.0):
    """Overdraw a lit or occluded band `len(deltas)` pixels deep along a side.

    `ragged` is the chance that a column stops one pixel short and `broken` the
    chance it is skipped altogether. Without them the band is a ruled line, and
    a ruled line is exactly what the water foam comment in t_water() warns
    about: it reads as paint rather than as a face catching the light.
    """
    for i in range(TS):
        depth = len(deltas)
        if broken and rnd.random() < broken:
            continue
        if ragged and rnd.random() < ragged:
            depth -= 1
        for k in range(depth):
            x, y = _band_pixel(side, k, i)
            put(img, x, y, ramp, base + deltas[k] + rnd.uniform(-jitter, jitter))


CORNERS = (("nw", BIT_NW, BIT_N, BIT_W), ("ne", BIT_NE, BIT_N, BIT_E),
           ("sw", BIT_SW, BIT_S, BIT_W), ("se", BIT_SE, BIT_S, BIT_E))


def corner_pocket(img, ramp, rnd, corner, base, occ, radius=5):
    """Ambient occlusion in an inside corner.

    Where two arms of the same material meet, the notch between them is the one
    place the light from the upper left cannot reach. Without this an L-shaped
    mass reads as two rectangles that happen to touch.
    """
    for y in range(radius):
        for x in range(radius):
            d = math.hypot(x + 0.5, y + 0.5)
            if d > radius:
                continue
            px = x if corner in ("nw", "sw") else TS - 1 - x
            py = y if corner in ("nw", "ne") else TS - 1 - y
            k = 1.0 - d / radius
            put(img, px, py, ramp, base - occ * k + rnd.uniform(-0.2, 0.2))


def convex_corner(img, ramp, rnd, corner, base, lift):
    """The outer corner where two exposed edges meet: rounded off with one
    step of extra light on the sunward side and extra shadow away from it."""
    sunward = corner == "nw"
    away = corner == "se"
    if not (sunward or away):
        lift *= 0.45
    for (x, y) in ((0, 0), (1, 0), (0, 1)):
        px = x if corner in ("nw", "sw") else TS - 1 - x
        py = y if corner in ("nw", "ne") else TS - 1 - y
        d = lift if sunward else (-lift if away else lift * 0.5)
        put(img, px, py, ramp, base + d + rnd.uniform(-0.2, 0.2))


def paint_edges(img, mask, rim, rnd, group=None, tid=None):
    """Turn an interior fill into the blob case `mask`."""
    ramp = rim["ramp"]
    base = rim["base"]
    sides = (("top", BIT_N, rim.get("top")), ("bottom", BIT_S, rim.get("bottom")),
             ("left", BIT_W, rim.get("left")), ("right", BIT_E, rim.get("right")))
    for side, bit, deltas in sides:
        if deltas is None or mask & bit:
            continue
        rim_band(img, ramp, rnd, side, base, deltas,
                 ragged=rim.get("ragged", 0.0), broken=rim.get("broken", 0.0))
    for corner, dbit, c1, c2 in CORNERS:
        open1 = not mask & c1
        open2 = not mask & c2
        if open1 and open2:
            convex_corner(img, ramp, rnd, corner, base, rim.get("convex", 1.2))
        elif not open1 and not open2 and not mask & dbit:
            corner_pocket(img, ramp, rnd, corner, base, rim.get("occlusion", 1.7))
    deco = rim.get("decorate")
    if deco is not None:
        deco(img, mask, rnd)
    edge_light_course(img, mask, rim, group)
    # Kaya Refit phase 3: the absolute rim that has to read under a 40 px hero.
    tiles_p3.refit_rim(img, mask, group, tid, random.Random(rnd.random()))


# ------------------------------------------------- phase C: tile edge light
# docs/plan-art-motion.md: "top edges of standable solid runs get a +1
# ramp-step highlight course; a 1 px ambient-occlusion row under overhangs."
#
# The RIM_* dicts above already carry hand-tuned `top=`/`bottom=` gradients
# per material -- this is the systematised, uniform course on top of them:
# one discrete ramp STEP (not a fractional dither blend) on the exposed top
# row, one discrete step darker on the exposed bottom row, the same rule for
# every standable solid material rather than whatever its own rim happened to
# specify. ADDITIVE, reusing a signal the rim dicts already encode: a spec
# whose `top` is already `None` (RIM_SOD, RIM_STONE_MOSSY, RIM_RUIN_ALGAE,
# RIM_HEIGHTS_SUN, RIM_DEEPS_CRUST, RIM_NEST_HOT) is the capped variant of a
# material -- t_grass_top(), t_stone(mossy=True) and the rest paint their own
# sunlit cap into the base art before the rim ever runs, which is exactly the
# hand-placed `solid_alt` cap the brief says not to double-light. Background
# materials (the `*_bg` groups) are never standable and are left alone.
STANDABLE_GROUPS = {"earth", "stone", "hub_grass", "hub_path",
                     "ruin", "heights", "deeps", "nest"}


def _step_at(img, x, y, ramp):
    """The ramp-step index already painted at (x, y), or the ramp's middle
    step if the pixel is not currently one of that ramp's own colours (it is
    ink, transparent, or a different material) -- a safe, visible fallback
    rather than a crash on a texture this function was not meant to touch."""
    c = img.getpixel((x, y))[:3]
    steps = RAMPS[ramp]
    for i, s in enumerate(steps):
        if s == c:
            return i
    return len(steps) // 2


def edge_light_course(img, mask, rim, group):
    if group not in STANDABLE_GROUPS:
        return
    ramp = rim["ramp"]
    top_capped = rim.get("top") is None
    if not mask & BIT_N and not top_capped:
        for x in range(TS):
            i = _step_at(img, x, 0, ramp)
            put(img, x, 0, ramp, min(len(RAMPS[ramp]) - 1, i + 1))
    if not mask & BIT_S:
        for x in range(TS):
            i = _step_at(img, x, TS - 1, ramp)
            put(img, x, TS - 1, ramp, max(0, i - 1))


# ------------------------------------------------------------ edge dressing
# A rim of the right brightness says "this face is exposed". What says *what it
# is made of* is the loose material that collects on an exposed face, and it is
# per-material.
def dress_earth(img, mask, rnd):
    if not mask & BIT_N:                                 # sunlit crust
        for _ in range(3):
            blob(img, "stone", rnd.randrange(1, 15), rnd.randrange(0, 3),
                 rnd.uniform(0.9, 1.5), rnd.uniform(0.8, 1.2), 3.6)
    if not mask & BIT_S:                                 # soil crumbling off
        for x in range(TS):
            if rnd.random() < 0.4:
                for k in range(rnd.randrange(1, 3)):
                    put(img, x, TS - 1 - k, "dirt", 1.0 + k * 0.55)
    for side, bit in (("left", BIT_W), ("right", BIT_E)):
        if mask & bit:
            continue
        for _ in range(2):                               # root ends in the face
            y = rnd.randrange(3, 13)
            for k in range(rnd.randrange(1, 3)):
                x, py = _band_pixel(side, k, y)
                put(img, x, py, "wood", 2.4 - k * 0.6)


def dress_sod(img, mask, rnd):
    """Grass-topped earth: the sod wraps over any exposed shoulder and hangs a
    little way down the cliff, which is what tiles 16 and 17 do by hand."""
    dress_earth(img, mask, rnd)
    for side, bit in (("left", BIT_W), ("right", BIT_E)):
        if mask & bit:
            continue
        run = 4 + rnd.randrange(4)
        for y in range(run):
            w = 2 if y < run - 2 else 1
            for k in range(w):
                x, py = _band_pixel(side, k, y)
                lvl = (4.6 if side == "left" else 3.4) - y * 0.45
                put(img, x, py, "grass", lvl)


def dress_stone(img, mask, rnd):
    """Cut stone: an exposed course is a chipped, dressed face, not a sawn
    one — so the rim gets bitten into in a few places."""
    for side, bit in (("top", BIT_N), ("bottom", BIT_S),
                      ("left", BIT_W), ("right", BIT_E)):
        if mask & bit:
            continue
        for _ in range(3):
            i = rnd.randrange(TS)
            for k in range(rnd.randrange(1, 3)):
                x, y = _band_pixel(side, k, i)
                put(img, x, y, "stone", 1.4 + rnd.uniform(-0.3, 0.5))


def dress_hub_grass(img, mask, rnd):
    """Top-down grass: blades lean out over whatever the meadow ends against."""
    for side, bit in (("top", BIT_N), ("bottom", BIT_S),
                      ("left", BIT_W), ("right", BIT_E)):
        if mask & bit:
            continue
        for i in range(TS):
            if rnd.random() < 0.5:
                for k in range(rnd.randrange(1, 4)):
                    x, y = _band_pixel(side, k, i)
                    put(img, x, y, "grass", 4.3 + rnd.uniform(-0.8, 0.8) - k * 0.9)


def dress_hub_path(img, mask, rnd):
    """Top-down path: gravel piles up along the kerb where the tread ends."""
    for side, bit in (("top", BIT_N), ("bottom", BIT_S),
                      ("left", BIT_W), ("right", BIT_E)):
        if mask & bit:
            continue
        for _ in range(4):
            i = rnd.randrange(TS)
            x, y = _band_pixel(side, rnd.randrange(2), i)
            blob(img, "stone", x, y, rnd.uniform(0.8, 1.4),
                 rnd.uniform(0.7, 1.2), 3.4)


def dress_bg_rock(img, mask, rnd):
    """Background rock stays quiet: the exposed lip is the only thing that
    catches any light at all, and even that is held two steps down."""
    if not mask & BIT_N:
        for x in range(TS):
            if rnd.random() < 0.35:
                put(img, x, 0, "stone", 2.3)


def dress_ruin(img, mask, rnd):
    """Waterlogged ashlar: an exposed face is where the algae gets light, so it
    grows on the shoulders and trails down; the underside weeps."""
    for side, bit in (("left", BIT_W), ("right", BIT_E)):
        if mask & bit:
            continue
        run = 3 + rnd.randrange(4)
        for y in range(run):
            for k in range(2 if y < run - 2 else 1):
                x, py = _band_pixel(side, k, y)
                put(img, x, py, "foliage", (3.2 if side == "left" else 2.2)
                    - y * 0.4)
    if not mask & BIT_N:                                 # wet crest
        for x in range(TS):
            if rnd.random() < 0.26:
                put(img, x, 0, "water", 5.6)
    if not mask & BIT_S:                                 # weeping underside
        for x in range(TS):
            if rnd.random() < 0.3:
                for k in range(rnd.randrange(1, 3)):
                    put(img, x, TS - 1 - k, "water", 1.4 + k * 0.5)


def dress_ruin_algae(img, mask, rnd):
    """The capped tile. Same as above, plus the mat wrapping over any exposed
    shoulder — held dark on purpose: a bright ledge here would take the frog."""
    dress_ruin(img, mask, rnd)
    for side, bit in (("left", BIT_W), ("right", BIT_E)):
        if mask & bit:
            continue
        run = 4 + rnd.randrange(4)
        for y in range(run):
            for k in range(2 if y < run - 2 else 1):
                x, py = _band_pixel(side, k, y)
                put(img, x, py, "foliage", (3.6 if side == "left" else 2.6)
                    - y * 0.42)


def dress_ruin_bg(img, mask, rnd):
    if not mask & BIT_N:
        for x in range(TS):
            if rnd.random() < 0.35:
                put(img, x, 0, "stone", 2.1)


def dress_heights(img, mask, rnd):
    """Wind-cut rock: the exposed top bleaches, the exposed underside sheds."""
    if not mask & BIT_N:
        for _ in range(4):
            x = rnd.randrange(TS)
            for k in range(rnd.randrange(1, 3)):
                put(img, x, k, "metal", 5.0 - k * 1.2)
    if not mask & BIT_S:
        for x in range(TS):
            if rnd.random() < 0.45:
                for k in range(rnd.randrange(1, 3)):
                    put(img, x, TS - 1 - k, "dirt", 0.9 + k * 0.6)
    for side, bit in (("left", BIT_W), ("right", BIT_E)):
        if mask & bit:
            continue
        for _ in range(3):                               # strata ends
            y = rnd.randrange(2, 14)
            for k in range(rnd.randrange(1, 3)):
                x, py = _band_pixel(side, k, y)
                put(img, x, py, "stone", 2.8 - k * 0.7)


def dress_heights_bg(img, mask, rnd):
    if not mask & BIT_N:
        for x in range(TS):
            if rnd.random() < 0.32:
                put(img, x, 0, "dirt", 1.7)


def dress_deeps(img, mask, rnd):
    """Chewed earth: a face the termites have worked is scalloped, and the odd
    amber fleck of chitin shows where a plate was pulled out of it."""
    for side, bit in (("top", BIT_N), ("bottom", BIT_S),
                      ("left", BIT_W), ("right", BIT_E)):
        if mask & bit:
            continue
        for _ in range(3):
            i = rnd.randrange(TS)
            for k in range(rnd.randrange(1, 3)):
                x, y = _band_pixel(side, k, i)
                put(img, x, y, "dirt", 0.5 + rnd.uniform(-0.2, 0.4))
    if not mask & BIT_N:
        for _ in range(3):
            put(img, rnd.randrange(TS), rnd.randrange(2), "gold", 2.8)
    if not mask & BIT_S:
        for x in range(TS):
            if rnd.random() < 0.3:
                put(img, x, TS - 1, "wood", 1.2)


def dress_deeps_crust(img, mask, rnd):
    """The capped tile: the carapace wraps whichever shoulder is exposed."""
    dress_deeps(img, mask, rnd)
    for side, bit in (("left", BIT_W), ("right", BIT_E)):
        if mask & bit:
            continue
        run = 3 + rnd.randrange(3)
        for y in range(run):
            for k in range(2 if y < run - 1 else 1):
                x, py = _band_pixel(side, k, y)
                put(img, x, py, "wood", (3.4 if side == "left" else 2.4)
                    - y * 0.5)
        gx, gy = _band_pixel(side, 0, 0)
        put(img, gx, gy, "gold", 3.4)                    # the amber lip again


def dress_deeps_bg(img, mask, rnd):
    if not mask & BIT_N:
        for x in range(TS):
            if rnd.random() < 0.3:
                put(img, x, 0, "wood", 2.2)


def dress_nest(img, mask, rnd):
    """Glass: an exposed edge is a fracture, so it glares rather than glowing,
    and the heat is trapped under the overhang where it cannot get out."""
    for side, bit in (("top", BIT_N), ("left", BIT_W), ("right", BIT_E)):
        if mask & bit:
            continue
        for _ in range(3):
            i = rnd.randrange(TS)
            x, y = _band_pixel(side, 0, i)
            put(img, x, y, "metal", 4.0)
    if not mask & BIT_S:                                 # heat under the lip
        for x in range(TS):
            if rnd.random() < 0.38:
                put(img, x, TS - 1, "ember", 3.6)
                if rnd.random() < 0.4:
                    put(img, x, TS - 2, "ember", 2.2)


def dress_nest_hot(img, mask, rnd):
    """The cooling-crust tile: wherever it is exposed, the seam runs."""
    dress_nest(img, mask, rnd)
    for side, bit in (("left", BIT_W), ("right", BIT_E)):
        if mask & bit:
            continue
        for y in range(2 + rnd.randrange(3)):
            x, py = _band_pixel(side, 1, y)
            put(img, x, py, "ember", 4.8 - y * 0.6)


def dress_nest_bg(img, mask, rnd):
    if not mask & BIT_N:
        for x in range(TS):
            if rnd.random() < 0.28:
                put(img, x, 0, "stone", 1.4)


# ------------------------------------------------------------------- rims
RIM_DIRT = dict(ramp="dirt", base=3.0, top=[2.3, 1.3, 0.5], bottom=[-2.2, -1.1],
                left=[1.5, 0.7], right=[-1.5, -0.7], ragged=0.4, broken=0.2, occlusion=1.8,
                convex=1.3, decorate=dress_earth)
RIM_SOD = dict(RIM_DIRT, top=None, decorate=dress_sod)
RIM_STONE = dict(ramp="stone", base=3.1, top=[1.9, 0.8], bottom=[-1.9, -0.9],
                 left=[1.2, 0.5], right=[-1.3, -0.6], ragged=0.15, occlusion=1.6,
                 convex=1.1, decorate=dress_stone)
RIM_STONE_MOSSY = dict(RIM_STONE, top=None)
RIM_BG_ROCK = dict(ramp="stone", base=1.25, top=[0.9, 0.4], bottom=[-0.8, -0.4],
                   left=[0.6, 0.3], right=[-0.6, -0.3], ragged=0.35, broken=0.3,
                   occlusion=0.8, convex=0.5, decorate=dress_bg_rock)
RIM_HUB_GRASS = dict(ramp="grass", base=2.4, top=[1.3, 0.6], bottom=[-1.2, -0.5],
                     left=[1.0, 0.4], right=[-1.1, -0.5], ragged=0.45, broken=0.3,
                     occlusion=1.2, convex=0.9, decorate=dress_hub_grass)
RIM_HUB_PATH = dict(ramp="dirt", base=4.7, top=[1.0, 0.4], bottom=[-1.4, -0.7],
                    left=[0.9, 0.4], right=[-1.0, -0.5], ragged=0.4, broken=0.2,
                    occlusion=1.4, convex=0.8, decorate=dress_hub_path)

# The four new worlds. Each pair is the mass and its capped form, and the
# capped one drops `top` because the cap is what the top *is*.
RIM_RUIN = dict(ramp="stone", base=2.5, top=[1.7, 0.7], bottom=[-1.7, -0.8],
                left=[1.1, 0.5], right=[-1.2, -0.6], ragged=0.2, broken=0.05,
                occlusion=1.5, convex=1.0, decorate=dress_ruin)
RIM_RUIN_ALGAE = dict(RIM_RUIN, top=None, decorate=dress_ruin_algae)
RIM_RUIN_BG = dict(ramp="stone", base=0.85, top=[0.8, 0.35],
                   bottom=[-0.7, -0.35], left=[0.55, 0.25],
                   right=[-0.55, -0.25], ragged=0.35, broken=0.3,
                   occlusion=0.7, convex=0.45, decorate=dress_ruin_bg)
RIM_HEIGHTS = dict(ramp="dirt", base=2.6, top=[2.0, 1.1, 0.4],
                   bottom=[-2.0, -1.0], left=[1.4, 0.6], right=[-1.4, -0.7],
                   ragged=0.4, broken=0.15, occlusion=1.7, convex=1.2,
                   decorate=dress_heights)
RIM_HEIGHTS_SUN = dict(RIM_HEIGHTS, top=None)
RIM_HEIGHTS_BG = dict(ramp="dirt", base=0.55, top=[0.85, 0.4],
                      bottom=[-0.75, -0.35], left=[0.6, 0.3],
                      right=[-0.6, -0.3], ragged=0.35, broken=0.3,
                      occlusion=0.75, convex=0.5, decorate=dress_heights_bg)
RIM_DEEPS = dict(ramp="dirt", base=2.3, top=[1.5, 0.8, 0.3],
                 bottom=[-1.1, -0.55], left=[1.0, 0.45], right=[-1.0, -0.5],
                 ragged=0.45, broken=0.2, occlusion=1.0, convex=0.9,
                 decorate=dress_deeps)
RIM_DEEPS_CRUST = dict(RIM_DEEPS, top=None, decorate=dress_deeps_crust)
RIM_DEEPS_BG = dict(ramp="dirt", base=0.22, top=[0.7, 0.3],
                    bottom=[-0.6, -0.3], left=[0.5, 0.22],
                    right=[-0.5, -0.22], ragged=0.4, broken=0.3,
                    occlusion=0.6, convex=0.4, decorate=dress_deeps_bg)
RIM_NEST = dict(ramp="stone", base=0.85, top=[1.6, 0.7], bottom=[-0.8, -0.4],
                left=[1.0, 0.45], right=[-0.8, -0.4], ragged=0.25,
                broken=0.08, occlusion=0.7, convex=1.0, decorate=dress_nest)
RIM_NEST_HOT = dict(RIM_NEST, top=None, decorate=dress_nest_hot)
RIM_NEST_BG = dict(ramp="stone", base=0.12, top=[0.6, 0.25],
                   bottom=[-0.25, -0.12], left=[0.4, 0.18],
                   right=[-0.35, -0.16], ragged=0.4, broken=0.3,
                   occlusion=0.25, convex=0.3, decorate=dress_nest_bg)


# --------------------------------------------------------- decorative overlay
# Phase 2's third item: roots, hanging vines, cracks and moss, scattered over
# the *background* layer only. They are picked by the same position hash as the
# fill variants, at a low rate, so a cave wall gets the occasional root without
# any of it being authored into a level.
def d_crack(img, rnd):
    x = rnd.randrange(3, 13)
    y = rnd.randrange(0, 4)
    crack(img, "stone", x, y, 11, 1.6, rnd, drift=(-1, 0, 1))
    if rnd.random() < 0.6:                                # a branch off it
        crack(img, "stone", x + rnd.choice((-2, 2)), y + 5, 5, 1.5, rnd)
    return img


def d_roots(img, rnd):
    """A woody root crossing the tile, lit along its upper shoulder."""
    y = rnd.randrange(2, 12)
    x = 0
    while x < TS:
        run = rnd.randrange(2, 5)
        for _ in range(run):
            if x >= TS:
                break
            put(img, x, y, "wood", 2.6)
            put(img, x, y - 1, "wood", 4.0)               # sunlit shoulder
            put(img, x, y + 1, "wood", 1.2)               # its own shadow
            x += 1
        y += rnd.choice((-1, 0, 0, 1))
        y = max(1, min(TS - 2, y))
    for _ in range(2):                                    # rootlets dropping off
        rx = rnd.randrange(TS)
        for k in range(rnd.randrange(2, 5)):
            put(img, rx, min(TS - 1, y + 1 + k), "wood", 1.8)
    return img


def d_vines(img, rnd):
    """One or two strands hanging from the top of the tile."""
    for _ in range(rnd.randrange(1, 3)):
        x = rnd.randrange(1, 15)
        run = rnd.randrange(9, TS + 1)
        for y in range(run):
            put(img, x, y, "foliage", 3.2)
            put(img, x + 1, y, "foliage", 1.8)
            if y % 3 == 1:                                # leaves off the stem
                side = -1 if (y // 3) % 2 == 0 else 2
                put(img, x + side, y, "grass", 3.4)
                put(img, x + side, y + 1, "foliage", 2.4)
            if rnd.random() < 0.3:
                x = max(1, min(13, x + rnd.choice((-1, 1))))
    return img


def d_moss(img, rnd):
    """A patch of moss clinging where damp collects."""
    for _ in range(rnd.randrange(3, 6)):
        cx, cy = rnd.randrange(TS), rnd.randrange(TS)
        wrap_blob(img, "foliage", cx, cy, rnd.uniform(2.0, 3.6),
                  rnd.uniform(1.2, 2.2), 2.6, lit=1.0, dark=0.8)
    speckle(img, "foliage", rnd, 18, 3.0, (-0.8, 0.9))
    return img


def d_kelp_hang(img, rnd):
    """SUNKEN RUINS: kelp trailing from whatever is above the cell."""
    for _ in range(rnd.randrange(1, 3)):
        x = rnd.randrange(1, 15)
        for y in range(rnd.randrange(8, TS + 1)):
            put(img, x, y, "wood", 2.4)
            put(img, x + 1, y, "wood", 1.0)
            if y % 4 == 2:
                side = -1 if (y // 4) % 2 == 0 else 2
                put(img, x + side, y, "foliage", 2.8)
                put(img, x + side, y + 1, "foliage", 1.6)
            if rnd.random() < 0.3:
                x = max(1, min(13, x + rnd.choice((-1, 1))))
    return img


def d_chain_hang(img, rnd):
    """THERMAL HEIGHTS / THE OBSIDIAN NEST: a length of chain left hanging."""
    x = rnd.randrange(2, 13)
    for y in range(rnd.randrange(7, TS + 1)):
        if y % 3 == 0:
            put(img, x, y, "metal", 3.8)
            put(img, x + 1, y, "metal", 1.8)
        else:
            put(img, x, y, "metal", 2.6)
    return img


def d_glow_spots(img, rnd):
    """TERMITE DEEPS: a few fungal caps, violet, small. The luminous accent is
    allowed here and nowhere else in a fill, because a background cell is
    behind the player rather than around them."""
    for _ in range(rnd.randrange(2, 5)):
        cx, cy = rnd.randrange(TS), rnd.randrange(TS)
        blob(img, "purple", cx, cy, rnd.uniform(1.2, 2.2),
             rnd.uniform(0.8, 1.5), 2.6)
        put(img, cx, cy - 1, "purple", 4.8)
    return img


def d_ember_seam(img, rnd):
    """THE OBSIDIAN NEST: one live seam crossing the cell, a pixel wide."""
    x, y = rnd.randrange(TS), rnd.randrange(TS)
    a = rnd.uniform(0, math.pi)
    fx, fy = float(x), float(y)
    for k in range(rnd.randrange(10, 18)):
        fx += math.cos(a)
        fy += math.sin(a)
        a += rnd.uniform(-0.3, 0.3)
        put(img, int(round(fx)) % TS, int(round(fy)) % TS, "ember",
            4.2 if k % 3 else 2.8)
        put(img, int(round(fx)) % TS, (int(round(fy)) + 1) % TS, "ember", 1.4)
    return img


def d_bones(img, rnd):
    """Old roots gone to splinters — the dry counterpart to d_moss."""
    for _ in range(rnd.randrange(2, 4)):
        x, y = rnd.randrange(2, 13), rnd.randrange(2, 13)
        run = rnd.randrange(3, 7)
        for k in range(run):
            put(img, x + k, y + (k // 3), "metal", 4.8)
            put(img, x + k, y + 1 + (k // 3), "metal", 2.0)
    return img


# --------------------------------------------------------------- the registry
# Which materials count as "the same" when a tile looks at its neighbours. The
# list includes ids that carry no variants of their own (16 and 17 are authored
# edges): they still have to read as earth, or a platform would grow a second
# cliff face against its own corner tile.
GROUPS = {
    "earth":     [1, 2, 16, 17],
    "stone":     [3, 4],
    "bg_rock":   [15],
    "hub_grass": [20],
    "hub_path":  [21],
    # Worlds 2-5. Each world contributes one mass (the fill and its capped
    # form, which have to autotile *against each other* or a ledge grows a
    # cliff face against its own floor) and one background wall.
    "ruin":      [220, 221],
    "ruin_bg":   [222],
    "heights":   [240, 241],
    "heights_bg": [242],
    "deeps":     [260, 261],
    "deeps_bg":  [262],
    "nest":      [280, 281],
    "nest_bg":   [282],
}

# Decorative overlays, background layer only. `needs` gates a decoration on the
# *foreground* around the cell, so vines hang from something and roots sit on
# something, rather than floating in the middle of a cave.
DECOR = {
    13: (130, [(d_vines, "any"), (d_vines, "ceiling"), (d_moss, "any")]),
    15: (170, [(d_crack, "any"), (d_crack, "any"), (d_roots, "floor"),
               (d_moss, "any"), (d_moss, "any"), (d_vines, "ceiling")]),
    18: (120, [(d_roots, "floor"), (d_vines, "ceiling"), (d_moss, "any"),
               (d_bones, "any")]),
    # Worlds 2-5, on their background walls and voids only.
    222: (160, [(d_crack, "any"), (d_moss, "any"), (d_moss, "any"),
                (d_kelp_hang, "ceiling")]),
    224: (90, [(d_kelp_hang, "ceiling"), (d_moss, "any"), (d_crack, "any")]),
    242: (150, [(d_crack, "any"), (d_crack, "any"), (d_bones, "any"),
                (d_chain_hang, "ceiling")]),
    244: (60, [(d_crack, "any"), (d_bones, "any"), (d_chain_hang, "ceiling")]),
    262: (170, [(d_roots, "floor"), (d_glow_spots, "any"),
                (d_glow_spots, "any"), (d_crack, "any")]),
    264: (110, [(d_glow_spots, "any"), (d_roots, "floor"),
                (d_roots, "ceiling")]),
    282: (140, [(d_ember_seam, "any"), (d_ember_seam, "any"),
                (d_crack, "any"), (d_chain_hang, "ceiling")]),
    284: (90, [(d_ember_seam, "any"), (d_crack, "any"),
               (d_chain_hang, "ceiling")]),
}


# Kaya Refit phase 3: extra paintings for the cases a level is made of.
# Counted over all 27 levels, the exposed case a player sees most is the top of
# a floor (124) and then the one-tile-thick strip (68); both had three
# paintings, so a ledge was a three-cell stamp. Each standable material gets
# four more of each — two plain, two carrying one accent — and every background
# wall gets three more interiors, because 255 is ~80% of every wall. Budgeted:
# 63 cells, four atlas rows, well inside the 4096 px the sheet must fit in.
CASE_TOP, CASE_STRIP = 124, 68
EXTRA_TOP = ((None, 0), (None, 1), (0, 2), (1, 3))       # (accent, seed slot)
EXTRA_BG = 3
REFIT_BG = {"bg_rock", "ruin_bg", "heights_bg", "deeps_bg", "nest_bg"}


def _extras(tid, seeds, group):
    if group in tiles_p3.RIM:
        out = {}
        for m in (CASE_TOP, CASE_STRIP):
            out[m] = [(seeds[0] * 7 + m * 13 + k, a) for a, k in EXTRA_TOP]
        return out
    if group in REFIT_BG:
        return {MASK_FULL: [(seeds[0] * 11 + k, None) for k in range(EXTRA_BG)]}
    return {}


def V(tid, build, seeds, group=None, rim=None):
    """One variant-capable tile. `seeds[0]` must reproduce the base tile
    exactly — the base atlas cell is reused as variant 0, and build_variants()
    asserts the two are pixel-identical so a mistyped seed cannot quietly
    change what an authored level looks like."""
    permille, decor = DECOR.get(tid, (0, []))
    return dict(id=tid, build=build, seeds=seeds, group=group, rim=rim,
                decor=decor, decor_permille=permille,
                extra=_extras(tid, seeds, group) if rim is not None else {})


#: Four paintings of every fill, and the 47-case blob set for the seven
#: materials that form masses. Everything else in the atlas is a one-off
#: object — a crate, a spike plate, a switch block — where a repeat is the
#: point rather than a defect.
#:
#: A few tiles get six or eight instead of four. They are the ones a level
#: lays down in the hundreds with no edges to break them up: ROOT HOLLOW is
#: fifteen hundred cells of background rock, and the hub borders its whole map
#: with the tree canopy.
VARIANT_SPECS = [
    V(1, t_dirt, [11, 1101, 1102, 1103], "earth", RIM_DIRT),
    V(2, t_grass_top, [12, 1201, 1202, 1203], "earth", RIM_SOD),
    V(3, t_stone, [21, 2101, 2102, 2103], "stone", RIM_STONE),
    V(4, lambda s: t_stone(s, mossy=True), [22, 2201, 2202, 2203], "stone",
      RIM_STONE_MOSSY),
    V(5, t_platform, [5, 501, 502, 503]),
    V(8, t_water, [32, 3201, 3202, 3203]),
    V(13, t_bg_leaves, [41, 4101, 4102, 4103, 4104, 4105]),
    V(14, t_trunk, [14, 1401, 1402, 1403]),
    V(15, t_bg_rock, [51, 5101, 5102, 5103, 5104, 5105], "bg_rock", RIM_BG_ROCK),
    V(16, lambda s: t_grass_edge(s, "left"), [13, 1301, 1302, 1303]),
    V(17, lambda s: t_grass_edge(s, "right"), [14, 1441, 1442, 1443]),
    V(18, t_bg_dark, [61, 6101, 6102, 6103, 6104, 6105]),
    V(20, t_hub_grass, [71, 7101, 7102, 7103], "hub_grass", RIM_HUB_GRASS),
    V(21, t_hub_path, [72, 7201, 7202, 7203], "hub_path", RIM_HUB_PATH),
    V(22, t_hub_water, [73, 7301, 7302, 7303]),
    V(23, t_hub_tree, [74, 7401, 7402, 7403, 7404, 7405, 7406, 7407]),
    V(25, t_metal, [25, 2501, 2502, 2503]),

    # ---------------------------------------------------------- 2. SUNKEN RUINS
    # The autotiled masses get three paintings per case rather than four. That
    # is a budget decision, not an aesthetic one: four worlds x three autotiled
    # materials x 47 cases is what decides the height of the atlas, and the
    # sheet has to stay inside the 4096 px every target guarantees. Background
    # fills, which are the tiles a level lays down in the hundreds, keep six.
    V(220, t_ruin_stone, [2201, 22011, 22012], "ruin", RIM_RUIN),
    V(221, lambda s: t_ruin_stone(s, algae=True), [2211, 22111, 22112],
      "ruin", RIM_RUIN_ALGAE),
    V(222, t_ruin_wall, [2221, 22211, 22212], "ruin_bg", RIM_RUIN_BG),
    V(223, t_ruin_silt, [2231, 22311, 22312, 22313]),
    V(225, t_ruin_column, [2251, 22511, 22512, 22513]),
    V(226, t_ruin_slab, [2261, 22611, 22612, 22613]),
    V(228, t_ruin_grate, [2281, 22811, 22812]),
    V(229, t_kelp, [2291, 22911, 22912]),
    V(230, t_ruin_algae, [2301, 23011, 23012, 23013, 23014, 23015]),
    V(231, t_ruin_cracked, [2311, 23111, 23112]),

    # ------------------------------------------------------- 3. THERMAL HEIGHTS
    V(240, t_heights_rock, [2401, 24011, 24012], "heights", RIM_HEIGHTS),
    V(241, lambda s: t_heights_rock(s, sun=True), [2411, 24111, 24112],
      "heights", RIM_HEIGHTS_SUN),
    V(242, t_heights_wall, [2421, 24211, 24212], "heights_bg", RIM_HEIGHTS_BG),
    V(243, t_heights_scree, [2431, 24311, 24312, 24313]),
    V(245, t_heights_stack, [2451, 24511, 24512, 24513]),
    V(246, t_heights_plank, [2461, 24611, 24612, 24613]),
    V(248, t_heights_chain, [2481, 24811, 24812]),
    V(249, t_heights_basalt, [2491, 24911, 24912, 24913]),
    V(250, t_heights_cloud, [2501, 25011, 25012, 25013, 25014, 25015]),
    V(251, t_heights_shell, [2511, 25111, 25112]),

    # --------------------------------------------------------- 4. TERMITE DEEPS
    V(260, t_deep_earth, [2601, 26011, 26012], "deeps", RIM_DEEPS),
    V(261, t_deep_crust, [2611, 26111, 26112], "deeps", RIM_DEEPS_CRUST),
    V(262, t_deep_comb, [2621, 26211, 26212], "deeps_bg", RIM_DEEPS_BG),
    V(263, t_deep_chitin, [2631, 26311, 26312, 26313]),
    V(265, t_deep_root, [2651, 26511, 26512, 26513]),
    V(266, t_deep_shelf, [2661, 26611, 26612, 26613]),
    V(268, t_deep_ladder, [2681, 26811, 26812]),
    V(269, t_deep_fungus, [2691, 26911, 26912, 26913, 26914, 26915]),
    V(270, t_deep_glowwall, [2701, 27011, 27012]),
    V(271, t_deep_packed, [2711, 27111, 27112, 27113]),

    # ----------------------------------------------------- 5. THE OBSIDIAN NEST
    V(280, t_nest_glass, [2801, 28011, 28012], "nest", RIM_NEST),
    V(281, lambda s: t_nest_glass(s, hot=True), [2811, 28111, 28112],
      "nest", RIM_NEST_HOT),
    V(282, t_nest_wall, [2821, 28211, 28212], "nest_bg", RIM_NEST_BG),
    V(283, t_nest_block, [2831, 28311, 28312, 28313]),
    V(285, t_nest_flue, [2851, 28511, 28512, 28513]),
    V(286, t_nest_ledge, [2861, 28611, 28612, 28613]),
    V(288, t_nest_chain, [2881, 28811, 28812]),
    V(289, t_nest_vein, [2891, 28911, 28912, 28913, 28914, 28915]),
    V(290, t_nest_plate, [2901, 29011, 29012, 29013]),
    V(291, t_nest_crust, [2911, 29111, 29112]),
]


def _cases_for(spec):
    """{canon mask: [images]} for one spec. Non-autotiled tiles have the single
    interior case; autotiled ones have all 47, each built by dressing the edges
    of one of the interior paintings."""
    interiors = [spec["build"](s) for s in spec["seeds"]]
    if spec["id"] in tiles_p3.INKED:
        for img in interiors:
            tiles_p3.ink_interactive(img)
    cases = {MASK_FULL: interiors}
    rim = spec["rim"]
    if rim is None:
        return cases
    for m in BLOB_CASES:
        if m == MASK_FULL:
            continue
        # Every case gets the full set, not just the interior. The first pass
        # gave the edge cases one painting each on the theory that they are
        # rare — but the commonest tile in a platformer is the top of a ledge,
        # which is one single case, and a hundred metres of it came out as one
        # cell repeated. Rarity is a property of the level, not of the mask.
        imgs = []
        for i, interior in enumerate(interiors):
            img = interior.copy()
            paint_edges(img, m, rim,
                        random.Random(spec["seeds"][0] * 131 + m * 17 + i),
                        group=spec["group"], tid=spec["id"])
            imgs.append(img)
        cases[m] = imgs
    # Phase 3's extra paintings, appended after the originals so every index
    # an earlier build handed out still names the painting it always did.
    for m, extra in sorted(spec.get("extra", {}).items()):
        for seed, acc in extra:
            img = spec["build"](seed)
            if m != MASK_FULL:
                paint_edges(img, m, rim, random.Random(seed * 131 + m * 17),
                            group=spec["group"], tid=spec["id"])
            if acc is not None:
                tiles_p3.accent(img, spec["group"], spec["id"], acc, seed + 5)
            cases[m].append(img)
    return cases


def build_variants():
    """Render every variant and hand back (extra atlas cells, manifest dict)."""
    extra = []
    tiles = {}

    def slot(img):
        extra.append(img)
        return VARIANT_BASE + len(extra) - 1

    for spec in VARIANT_SPECS:
        tid = spec["id"]
        cases = _cases_for(spec)
        assert cases[MASK_FULL][0].tobytes() == TILE_DEFS[tid].tobytes(), (
            "tile %d: seeds[0] no longer reproduces the base tile" % tid)
        out_cases = {}
        for m in sorted(cases):
            ids = []
            for i, img in enumerate(cases[m]):
                # Variant 0 of the interior case *is* the gameplay tile.
                ids.append(tid if (m == MASK_FULL and i == 0) else slot(img))
            out_cases[str(m)] = ids
        decor = []
        for i, (fn, needs) in enumerate(spec["decor"]):
            src = cases[MASK_FULL][i % len(cases[MASK_FULL])].copy()
            fn(src, random.Random(spec["seeds"][0] * 977 + i * 37))
            decor.append({"index": slot(src), "needs": needs})
        tiles[str(tid)] = {
            "group": spec["group"],
            "autotile": spec["rim"] is not None,
            "cases": out_cases,
            "decor": decor,
            "decor_permille": spec["decor_permille"],
        }

    groups = {}
    for name in sorted(GROUPS):
        for tid in GROUPS[name]:
            groups[str(tid)] = name
    manifest = {
        "_comment": ("Generated by tools/art/tiles.py (docs/art-direction.md "
                     "phase 2). Do not edit. Maps a gameplay tile id plus its "
                     "eight neighbours to an atlas cell; the gameplay id itself "
                     "never changes, so collision is unaffected."),
        "tile_size": TS,
        "atlas_columns": 16,
        "variant_base": VARIANT_BASE,
        "full_mask": MASK_FULL,
        "case_count": len(BLOB_CASES),
        "groups": groups,
        "group_members": {k: sorted(v) for k, v in sorted(GROUPS.items())},
        "tiles": tiles,
        "contact_shadow": tiles_p3.contact_shadow_manifest(),
    }
    return extra, manifest


def build_tileset():
    cols = 16
    assert len(TILE_DEFS) <= VARIANT_BASE, "gameplay ids overflow into the variants"
    extra, manifest = build_variants()
    total = VARIANT_BASE + len(extra)
    rows = (total + cols - 1) // cols
    img = Image.new("RGBA", (cols * TS, rows * TS), (0, 0, 0, 0))
    for i, t in enumerate(TILE_DEFS):
        img.alpha_composite(t, ((i % cols) * TS, (i // cols) * TS))
    for j, t in enumerate(extra):
        i = VARIANT_BASE + j
        img.alpha_composite(t, ((i % cols) * TS, (i // cols) * TS))
    img.save(os.path.join(TILES, "tileset.png"))
    tiles_p3.contact_shadow_sheet().save(os.path.join(TILES, "contact_shadow.png"))
    path = os.path.join(TILES, "variants.json")
    with open(path, "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=False)
        f.write("\n")
    autotiled = sum(1 for s in VARIANT_SPECS if s["rim"] is not None)
    print("tileset.png  %d gameplay tiles + %d variants (%d autotiled materials)"
          % (len(TILE_DEFS), len(extra), autotiled))
    print("variants.json  %d cases per autotiled material" % len(BLOB_CASES))


# ================================================================ HD (2x)
# docs/plan-hd.md, phase H0 look sample: a slice of the jungle set drawn
# natively at 32x32 texels per tile (two per world unit). Nothing here is
# registered with T(), so the atlas, its ids and every level are untouched;
# tools/art/hd_look.py is the only reader.
#
# The rule is the same as at 1x -- structure first, shading second -- but at
# 2x the structures can be things instead of marks: blades of grass instead of
# a green band, pebbles with a cast shadow, mortar with chipped arrises, planks
# with grain that runs round a knot. Shading resolves to whole ramp steps
# (CLEAN_FILL) and every structure is drawn wrapped, so tiles still tile.
HTS = TS * 2


def tile_hd(alpha=0):
    return Image.new("RGBA", (HTS, HTS), (0, 0, 0, alpha))


def put_hd(img, x, y, ramp, level, alpha=255):
    """Whole-step pixel, wrapped onto the tile: structures cross edges."""
    img.putpixel((int(x) % HTS, int(y) % HTS),
                 RAMPS[ramp][max(0, min(6, int(round(level))))] + (alpha,))


def get_hd(img, x, y):
    return img.getpixel((int(x) % HTS, int(y) % HTS))


def blob_hd(img, ramp, cx, cy, rx, ry, base, lit=1.4, dark=1.3, shadow=None):
    """A lit lump, wrapped, in whole steps. `shadow` darkens a crescent of
    the ground below-right of it by that much, so it sits IN the material."""
    for y in range(int(cy - ry - 3), int(cy + ry + 4)):
        for x in range(int(cx - rx - 3), int(cx + rx + 4)):
            nx, ny = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
            d = nx * nx + ny * ny
            if d > 1.0:
                if shadow is not None:
                    sx, sy = (x + 0.5 - cx - 1.2) / rx, (y + 0.5 - cy - 1.4) / ry
                    if sx * sx + sy * sy <= 1.0:
                        p = get_hd(img, x, y)
                        lvl = _level_of(p, ramp_hint="dirt")
                        if lvl is not None:
                            put_hd(img, x, y, lvl[0], lvl[1] - shadow)
                continue
            lvl = base + (1.0 - d) * 1.1
            facing = -nx - ny
            if facing > 0.55:
                lvl += lit
            elif facing < -0.6:
                lvl -= dark
            if d > 0.72 and facing < -0.2:
                lvl -= 0.6
            put_hd(img, x, y, ramp, lvl)


_LOOKUP = {c: (n, i) for n, steps in RAMPS.items() for i, c in enumerate(steps)}


def _level_of(p, ramp_hint=None):
    return _LOOKUP.get(tuple(p[:3]))


def darken_hd(img, x, y, by):
    m = _level_of(get_hd(img, x, y))
    if m:
        put_hd(img, x, y, m[0], m[1] - by)


def fill_hd(img, ramp, base, rnd, grain=0.3, cell=2):
    """Flat material with grain in 2x2 cells: per-texel grain at 2x is a
    finer noise than 1x ever showed and reads as static, not as soil."""
    g = {}
    for y in range(HTS):
        for x in range(HTS):
            k = (x // cell, y // cell)
            if k not in g:
                g[k] = rnd.uniform(-grain, grain)
            put_hd(img, x, y, ramp, base + g[k])
    return img


def root_hd(img, rnd, x, y, length, base=3.0):
    """A root fibre: a wandering dark line with a lit lip below it, that may
    fork once."""
    dx = rnd.choice((-1, 1))
    for i in range(length):
        put_hd(img, x, y, "dirt", base - 1.9)
        put_hd(img, x, y + 1, "dirt", base + 0.9)
        x += dx
        if rnd.random() < 0.35:
            y += rnd.choice((-1, 1))
        if i == length // 2 and rnd.random() < 0.6:
            root_hd(img, rnd, x, y + 1, length // 3, base)


def t_dirt_hd(seed):
    rnd = random.Random(seed)
    img = fill_hd(tile_hd(255), "dirt", 3.0, rnd, grain=0.32)
    for _ in range(7):                                   # clods
        blob_hd(img, "dirt", rnd.uniform(0, HTS), rnd.uniform(0, HTS),
                rnd.uniform(3.0, 5.5), rnd.uniform(2.2, 3.8), 2.4, lit=1.0, dark=0.9)
    for _ in range(3):
        root_hd(img, rnd, rnd.randrange(HTS), rnd.randrange(HTS), rnd.randrange(7, 13))
    for _ in range(4):                                   # pebbles, cast shadow
        blob_hd(img, "stone", rnd.uniform(0, HTS), rnd.uniform(0, HTS),
                rnd.uniform(1.6, 2.8), rnd.uniform(1.3, 2.2), 2.9, shadow=1.3)
    for _ in range(9):                                   # grit: a lit grain on its shadow
        x, y = rnd.randrange(HTS), rnd.randrange(HTS)
        put_hd(img, x, y, "dirt", 4.6)
        put_hd(img, x + 1, y + 1, "dirt", 1.6)
    for _ in range(3):                                   # worm holes
        x, y = rnd.randrange(HTS), rnd.randrange(HTS)
        put_hd(img, x, y, "dirt", 0.6)
        put_hd(img, x + 1, y, "dirt", 1.2)
        put_hd(img, x, y + 1, "dirt", 4.0)
    return img


def t_grass_top_hd(seed):
    """Sod over dirt. The top edge is a row of blades, not a ruler: the cap
    has a dark root mat, individual blades rising out of it with a lit left
    flank and a few hanging over the soil, and transparent notches between
    the tallest tips so the skyline of a ledge is grass-shaped."""
    rnd = random.Random(seed)
    img = t_dirt_hd(seed + 100)
    depth = []
    for x in range(HTS):                                 # the mat
        d = 7 + (1 if math.sin(x * math.pi / 8 + 1.0) > 0.3 else 0) + rnd.choice((0, 0, 1))
        for y in range(0, d):
            put_hd(img, x, y, "grass", 3.6 - y * 0.32)
        put_hd(img, x, d, "grass", 1.4)
        depth.append(d)
        for k in range(3):                               # sun on the soil below
            put_hd(img, x, d + 1 + k, "dirt", 4.5 - k * 0.8)
    for x in range(HTS):                                 # top notches
        if x % 4 == 2 or (x % 7 == 0):
            img.putpixel((x, 0), (0, 0, 0, 0))
            if x % 8 == 2:
                img.putpixel((x, 1), (0, 0, 0, 0))
    for i in range(16):                                  # blades
        x = (i * 2 + rnd.choice((0, 1))) % HTS
        top = rnd.choice((0, 1, 1, 2))
        ln = rnd.randrange(4, 8)
        lean = rnd.choice((-1, 0, 1))
        for k in range(ln):
            bx = x + (lean if k < ln // 2 else 0)
            put_hd(img, bx, top + k, "grass", 6.0 - k * 0.55)
            put_hd(img, bx + 1, top + k + 1, "grass", 2.2)
    for _ in range(5):                                   # strands hanging into the soil
        x = rnd.randrange(HTS)
        for k in range(rnd.randrange(2, 5)):
            put_hd(img, x, depth[x] + k, "grass", 3.0 - k * 0.5)
    for _ in range(2):                                   # a seed head
        x = rnd.randrange(2, HTS - 2)
        put_hd(img, x, 2, "gold", 5)
        put_hd(img, x, 3, "gold", 4)
    return img


def t_stone_hd(seed):
    """Two courses of half-offset blocks, 16 texels high. Each block has a
    two-texel sunlit top, a lit left arris, an occluded foot and right side;
    mortar is a dark joint with a lit lip under it; corners are chipped and a
    few faces carry pits, a hairline crack and a lichen spot."""
    rnd = random.Random(seed)
    img = tile_hd(255)
    jit = {}
    for y in range(HTS):
        course = y // 16
        ly = y % 16
        jx = 0 if course == 0 else 16
        for x in range(HTS):
            lx = (x - jx) % HTS
            if ly == 0 or lx == 0:
                lvl = 0.6                                # joint
            elif ly == 1 or lx == 1:
                lvl = 1.6 if lx != 1 or ly < 2 else 1.4  # mortar bed
            else:
                k = (lx // 2, ly // 2, course)
                if k not in jit:
                    jit[k] = rnd.uniform(-0.6, 0.6)
                # the face falls off from its lit corner, and the grain is
                # big enough to survive rounding to whole steps
                lvl = 3.3 + jit[k] - (lx / 32.0 + ly / 16.0) * 0.45
                if ly == 2:
                    lvl += 2.0
                elif ly == 3:
                    lvl += 1.0
                elif ly == 15:
                    lvl -= 1.6
                elif ly == 14:
                    lvl -= 0.8
                if lx == 2:
                    lvl += 1.0
                elif lx == 31:
                    lvl -= 1.4
                elif lx == 30:
                    lvl -= 0.6
            put_hd(img, x, y, "stone", lvl)
    # chipped arrises: a bite out of a block corner, dark inside, lit edge below
    for (bx, by) in ((2, 2), (29, 13), (18, 18), (13, 29), (31, 3)):
        for dy in range(3):
            for dx in range(3 - dy):
                put_hd(img, bx + (dx if bx < 16 else -dx), by + (dy if by % 16 < 8 else -dy),
                       "stone", 1.2)
        put_hd(img, bx + (3 if bx < 16 else -3), by, "stone", 4.4)
    for _ in range(10):                                  # pits
        x, y = rnd.randrange(4, 28), rnd.randrange(4, 28)
        if y % 16 < 4 or y % 16 > 13:
            continue
        put_hd(img, x, y, "stone", 1.4)
        put_hd(img, x + 1, y, "stone", 2.0)
        put_hd(img, x, y + 1, "stone", 4.2)
    x, y = rnd.randrange(6, 14), 20                     # hairline crack
    for _ in range(9):
        put_hd(img, x, y, "stone", 1.0)
        put_hd(img, x + 1, y + 1, "stone", 4.0)
        x += 1
        y += rnd.choice((0, 1, 1, -1))
        if y % 16 < 3 or y % 16 > 13:
            break
    for (lx, ly) in ((22, 7), (23, 7), (22, 8), (6, 24)):  # lichen
        put_hd(img, lx, ly, "grass", 4.0)
    put_hd(img, 21, 8, "grass", 2.6)
    return img


def t_platform_hd(seed):
    """The one-way platform: eight texel rows of plank -- a sunlit top edge,
    grain lines that run along the board and swirl round a knot, butt joints
    between three boards, nail heads with a highlight and a rust streak, and a
    hard ink line under it. Thickness is the 1x four rows, in world units."""
    rnd = random.Random(seed)
    img = tile_hd(0)
    for x in range(HTS):
        for y in range(7):
            lvl = (5.6, 4.8, 4.0, 3.6, 3.4, 3.0, 2.0)[y]
            put_hd(img, x, y, "wood", lvl)
        put_ink(img, x, 7)
    for gy, phase in ((2, 0.0), (4, 2.0), (5, 4.1)):   # grain
        for x in range(HTS):
            if math.sin(x * math.pi / 8 + phase + gy) > 0.15:
                put_hd(img, x, gy, "wood", 2.6)
    kx = 20                                             # knot
    for (dx, dy, l) in ((0, 0, 1.4), (1, 0, 1.8), (-1, 0, 3.6), (0, -1, 3.8),
                        (2, 0, 2.6), (-2, 0, 4.2)):
        put_hd(img, kx + dx, 3 + dy, "wood", l)
    for sx in (11, 27):                                  # butt joints
        for y in range(1, 7):
            put_hd(img, sx, y, "wood", 1.2)
            put_hd(img, sx + 1, y, "wood", 4.6)
    for nx in (3, 9, 14, 25, 30):                        # nails
        put_hd(img, nx, 2, "metal", 6)
        put_hd(img, nx + 1, 2, "metal", 3)
        put_hd(img, nx, 3, "metal", 2)
        put_hd(img, nx + 1, 3, "ember", 2)              # rust bleeding into the grain
    return img


VINE_MAP_HD = {'G': ("foliage", 2.4), 'g': ("foliage", 3.6), 'l': ("grass", 3.6),
               'L': ("grass", 2.5), 'm': ("foliage", 1.2), 'c': ("grass", 4.8)}


def t_vine_hd(seed):
    """The vine ladder: two stems twisting round each other (period 32, so it
    tiles vertically), with leaves alternating left and right -- each a pointed
    leaf with a midrib and a lit upper side -- and a curled tendril. Built as a
    material grid and lit with auto_shade like 1x, so it shades the same way."""
    rnd = random.Random(seed)
    g = [['.'] * HTS for _ in range(HTS)]

    def setc(x, y, ch, only=None):
        x, y = int(x), int(y) % HTS
        if 0 <= x < HTS and (only is None or g[y][x] in only):
            g[y][x] = ch

    for y in range(HTS):                                  # braided stems
        for k, ph in enumerate((0.0, math.pi)):
            cx = 15.5 + 2.2 * math.sin(y * 2 * math.pi / HTS + ph)
            front = math.cos(y * 2 * math.pi / HTS + ph) > 0
            for dx in (-1, 0, 1):
                if front or g[y][int(cx + dx)] == '.':
                    setc(cx + dx, y, 'g' if front else 'G')

    def leaf(bx, by, sgn, ln, droop):
        pts = []
        for i in range(ln + 1):
            t = i / ln
            x = bx + sgn * i
            yc = by + droop * t * t
            half = 2.6 * math.sin(math.pi * min(1.0, t * 1.15))
            for yy in range(int(yc - half), int(yc + half) + 1):
                setc(x, yy, 'l' if yy <= yc else 'L')
            pts.append((x, yc))
        for x, yc in pts[1:-1]:
            setc(x, round(yc), 'm')                       # midrib

    # Rungs: a pair of leaves every half tile, offset a few texels, so a
    # column of these reads as a ladder the way the 1x leaf pairs do.
    for by, ln in ((6, 12), (22, 11)):
        leaf(17, by, 1, ln, 3.0)
        leaf(14, by + 3, -1, ln + 1, 3.4)
    leaf(17, 14, 1, 6, 1.5)
    leaf(14, 29, -1, 6, 1.5)
    for (x, y) in ((24, 13), (25, 12), (26, 12), (27, 13), (27, 14), (26, 15)):
        setc(x, y, 'c')                                   # tendril curl
    rows = ["".join(r) for r in g]
    return auto_shade(rows, VINE_MAP_HD, depth=2, lit=1.3, dark=1.0)


def _caustic(x, y, seed):
    """A caustic net periodic in 32 both ways, so the water tiles."""
    a = 2 * math.pi / HTS
    v = (math.sin(a * x + 1.3 * math.sin(a * y * 2 + seed))
         + math.sin(a * y + 1.1 * math.sin(a * x * 2 + seed * 1.7))
         + 0.6 * math.sin(a * (x + y) * 2 + seed))
    return v


def t_water_hd(seed, surface=False):
    """Water: a body graded by depth, a caustic net of thin bright lines
    (periodic, so it tiles in both directions), and a couple of bubbles. The
    surface adds a swell of period 32 with foam on the rising faces, flecks of
    spray above it and a lit band just under it."""
    rnd = random.Random(seed)
    img = tile_hd(255)
    for y in range(HTS):
        for x in range(HTS):
            lvl = 4.0
            if surface:
                lvl = 5.0 - min(y, 12) * 0.08
            c = _caustic(x, y, seed % 7)
            if abs(c) < 0.16:
                lvl += 1.2                               # the net: thin ridges
            elif abs(c) < 0.42 and c > 0:
                lvl += 0.6
            put_hd(img, x, y, "water", lvl)
    for (bx, by) in ((7, 20), (24, 11)):                 # bubbles
        for (dx, dy) in ((0, -1), (-1, 0), (1, 0), (0, 1)):
            put_hd(img, bx + dx, by + dy, "water", 6)
        put_hd(img, bx - 1, by - 1, "metal", 6)
        put_hd(img, bx + 3, by + 3, "water", 6)
    if surface:
        for x in range(HTS):
            swell = math.sin(x * 2 * math.pi / HTS)
            crest = int(round(2 - 2 * swell))           # 0..4 rows down
            for y in range(crest):
                img.putpixel((x, y), (0, 0, 0, 0))       # air above the swell
            put_hd(img, x, crest, "metal", 6 if swell > -0.2 else 5)
            if swell > 0.3:                              # foam on the rising face
                put_hd(img, x, crest + 1, "metal", 5)
                if swell > 0.8:
                    put_hd(img, x, crest + 2, "metal", 4)
            put_hd(img, x, crest + 2 + (1 if swell > 0.8 else 0), "water", 6)
            put_hd(img, x, crest + 3 + (1 if swell > 0.8 else 0), "water", 5)
        for (x, y) in ((5, 0), (9, 1), (27, 4), (30, 2)):  # spray
            if img.getpixel((x, y))[3] == 0:
                put_hd(img, x, y, "metal", 6)
    return img


def t_spikes_hd(seed):
    """Three iron spikes on a bolted plate. Each cone is lit down its left
    flank with a specular streak, shades round to its right, carries a rust
    stain at the root, and is inked down the dark side so the silhouette is
    a hazard at a glance."""
    img = tile_hd(0)
    for x in range(HTS):                                  # plate
        put_hd(img, x, 26, "metal", 5)
        put_hd(img, x, 27, "metal", 4)
        put_hd(img, x, 28, "metal", 3)
        put_hd(img, x, 29, "metal", 2)
        put_hd(img, x, 30, "metal", 1)
        put_ink(img, x, 31)
    for bx in (3, 13, 23):                                # bolts
        put_hd(img, bx, 27, "metal", 6)
        put_hd(img, bx + 1, 27, "metal", 4)
        put_hd(img, bx, 28, "metal", 3)
        put_hd(img, bx + 1, 28, "metal", 1)
    for cx in (5.5, 15.5, 25.5):
        for y in range(6, 26):
            half = (y - 6) / 19.0 * 5.2
            lo, hi = int(math.floor(cx - half)), int(math.ceil(cx + half))
            for x in range(lo, hi + 1):
                t = (x + 0.5 - cx) / max(half, 0.5)
                if abs(t) > 1.05:
                    continue
                lvl = 5.1 - t * 2.3
                if -0.55 < t < -0.25 and y > 8:
                    lvl = 6.0                             # specular streak
                put_hd(img, x, y, "metal", lvl)
            if y > 22 and (y + int(cx)) % 2 == 0:         # rust at the root
                put_hd(img, int(cx + 2), y, "ember", 1.6)
            put_ink(img, hi + 1 if hi + 1 < HTS else hi, y)
            put_ink(img, lo - 1 if lo > 0 else lo, y) if y < 10 else None
        put_ink(img, int(cx), 5)
        put_hd(img, int(cx), 6, "metal", 6)               # tip glint
    return img


def t_crate_hd(seed):
    """Crate: a frame of four boards with mitred corners, three planks with
    grain and a knot, a diagonal brace with its own bevel, iron corner
    brackets and nails. Breakable reads from the planks and the brace."""
    rnd = random.Random(seed)
    img = tile_hd(255)
    for y in range(HTS):
        for x in range(HTS):
            frame = x < 4 or x > 27 or y < 4 or y > 27
            if frame:
                if y < 4 and y <= x and y <= 31 - x:
                    lvl = (5.4, 4.8, 4.2, 3.2)[y]
                elif x < 4 and x < y and x <= 31 - y:
                    lvl = (5.0, 4.4, 3.8, 3.0)[x]
                elif y > 27:
                    lvl = (2.4, 2.0, 1.6, 1.0)[y - 28]
                else:
                    lvl = (2.6, 2.2, 1.8, 1.2)[x - 28]
                if (y < 4 or y > 27) and math.sin(x * 0.7 + y) > 0.6:
                    lvl -= 0.6                            # grain along the board
                if (x < 4 or x > 27) and math.sin(y * 0.7 + x) > 0.6:
                    lvl -= 0.6
            else:
                ly = (y - 4) % 8
                lvl = 3.2
                if ly == 0:
                    lvl = 1.4                             # seam
                elif ly == 1:
                    lvl = 4.4                             # lip
                elif ly == 7:
                    lvl = 2.4
                g = math.sin(x * 0.45 + 2.5 * math.sin(y * 0.9 + (y // 8)))
                if g > 0.8 and 1 < ly < 7:
                    lvl -= 0.8
            put_hd(img, x, y, "wood", lvl)
    for i in range(4, 28):                                # brace, bottom-left to top-right
        x, y = i, 31 - i
        put_hd(img, x, y - 2, "wood", 4.8)
        put_hd(img, x, y - 1, "wood", 3.8)
        put_hd(img, x, y, "wood", 3.4)
        put_hd(img, x, y + 1, "wood", 1.4)
    for (bx, by, sx, sy) in ((1, 1, 1, 1), (30, 1, -1, 1), (1, 30, 1, -1), (30, 30, -1, -1)):
        for k in range(5):                                # iron bracket
            put_hd(img, bx + sx * k, by, "metal", 4 if sy > 0 else 2)
            put_hd(img, bx, by + sy * k, "metal", 4 if sx > 0 else 2)
        put_hd(img, bx + sx * 2, by + sy * 2, "metal", 6)
        put_hd(img, bx + sx * 3, by + sy * 3, "metal", 1)
    for (nx, ny) in ((10, 6), (21, 6), (10, 22), (21, 22)):
        put_hd(img, nx, ny, "metal", 6)
        put_hd(img, nx + 1, ny + 1, "metal", 2)
    return img


def t_bg_leaves_hd(seed):
    """Background leaves: a mat of pointed leaves, each with a midrib, a lit
    upper edge and a shaded underside, held to the dark end of the foliage
    ramp so the player stays in front of it. Wrapped, so it tiles."""
    rnd = random.Random(seed)
    img = fill_hd(tile_hd(255), "foliage", 0.9, rnd, grain=0.25, cell=4)
    for _ in range(16):
        cx, cy = rnd.uniform(0, HTS), rnd.uniform(0, HTS)
        ang = rnd.uniform(-0.9, 0.9) + (math.pi if rnd.random() < 0.5 else 0)
        ln, wd = rnd.uniform(7, 11), rnd.uniform(2.2, 3.4)
        ca, sa = math.cos(ang), math.sin(ang)
        for y in range(int(cy - ln - 2), int(cy + ln + 3)):
            for x in range(int(cx - ln - 2), int(cx + ln + 3)):
                u = (x + 0.5 - cx) * ca + (y + 0.5 - cy) * sa
                v = -(x + 0.5 - cx) * sa + (y + 0.5 - cy) * ca
                t = (u + ln) / (2 * ln)
                if not 0 <= t <= 1:
                    continue
                half = wd * math.sin(math.pi * t) ** 0.8
                if abs(v) > half:
                    continue
                lvl = 1.8
                if abs(v) < 0.5:
                    lvl = 2.9                            # midrib
                elif v < 0:
                    lvl = 2.4                            # lit half
                if abs(v) > half - 0.9 and v > 0:
                    lvl = 0.8                            # shaded rim
                put_hd(img, x, y, "foliage", lvl)
    for _ in range(10):
        put_hd(img, rnd.randrange(HTS), rnd.randrange(HTS), "foliage", 3)
    return img


def t_trunk_hd(seed):
    """Bark: six ribs whose grooves wander (period 32 vertically, so it
    tiles), each with a lit left shoulder; flakes, horizontal splits, a knot
    hole and a strand of moss in one groove."""
    rnd = random.Random(seed)
    img = tile_hd(255)
    edges = [0, 6, 11, 17, 22, 27, 32]
    for y in range(HTS):
        wob = [int(round(1.2 * math.sin(y * 2 * math.pi / HTS + i * 1.7))) if 0 < i < 6 else 0
               for i, _ in enumerate(edges)]
        es = [e + w for e, w in zip(edges, wob)]
        for i in range(6):
            x0, x1 = es[i], es[i + 1]
            for x in range(x0, x1):
                lvl = 2.2
                if x == x0:
                    lvl = 0.6
                elif x == x0 + 1:
                    lvl = 1.4
                elif x == x0 + 2:
                    lvl = 3.4
                elif x == x0 + 3:
                    lvl = 2.8
                elif x == x1 - 1:
                    lvl = 1.6
                put_hd(img, x, y, "wood", lvl + rnd.uniform(-0.3, 0.3))
    for _ in range(6):                                  # flakes
        x, y = rnd.randrange(HTS), rnd.randrange(HTS)
        for k in range(rnd.randrange(2, 4)):
            put_hd(img, x, y + k, "wood", 4.2)
            put_hd(img, x + 1, y + k, "wood", 1.0)
    for _ in range(3):                                  # splits
        x, y = rnd.randrange(HTS), rnd.randrange(HTS)
        for k in range(rnd.randrange(3, 6)):
            put_hd(img, x + k, y, "wood", 0.6)
            put_hd(img, x + k, y + 1, "wood", 3.6)
    for (dx, dy, l) in ((0, 0, 0.2), (1, 0, 0.2), (0, 1, 0.4), (1, 1, 0.8),
                        (-1, 0, 3.6), (0, -1, 3.8), (1, -1, 3.4), (2, 1, 1.4), (0, 2, 3.0)):
        put_hd(img, 14 + dx, 18 + dy, "wood", l)        # knot hole
    for y in range(HTS):                                # moss in a groove
        if math.sin(y * 2 * math.pi / HTS) > -0.1:
            put_hd(img, 22 + int(round(1.2 * math.sin(y * 2 * math.pi / HTS + 4 * 1.7))),
                    y, "grass", 2.6 + (0.8 if y % 3 == 0 else 0))
    return img


#: The look sample's slice, by the 1x id each one would replace.
HD_SLICE = [
    (2, "grass top", lambda: t_grass_top_hd(12)),
    (1, "dirt", lambda: t_dirt_hd(11)),
    (3, "stone", lambda: t_stone_hd(21)),
    (5, "one-way platform", lambda: t_platform_hd(5)),
    (6, "vine ladder", lambda: t_vine_hd(6)),
    (9, "spikes", lambda: t_spikes_hd(9)),
    (10, "crate", lambda: t_crate_hd(7)),
    (7, "water surface", lambda: t_water_hd(31, surface=True)),
    (8, "water body", lambda: t_water_hd(32)),
    (13, "bg leaves", lambda: t_bg_leaves_hd(41)),
    (14, "trunk", lambda: t_trunk_hd(14)),
]
