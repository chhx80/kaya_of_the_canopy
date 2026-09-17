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

from .palette import (TILES, auto_shade, blob, crack, put, put_ink, speckle)

TS = 16


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
            put(img, x, y, ramp, lvl)
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
    every step of structure in here is a step stolen from the tiles in front."""
    rnd = random.Random(seed)
    # Base sits on a whole ramp step rather than between two. A fractional
    # level here resolves through the Bayer matrix, and a Bayer checkerboard
    # over 400x240 of flat fill is the most visible thing on the screen.
    img = fill(tile(255), "metal", 5.0, rnd, grain=0.0)
    for _ in range(4):                              # soft shadow in the haze
        wrap_blob(img, "metal", rnd.randrange(TS), rnd.randrange(TS),
                  rnd.uniform(3.0, 5.5), rnd.uniform(2.0, 3.4), 4.55,
                  lit=0.0, dark=0.0)
    speckle(img, "metal", rnd, 6, 5.0, (-0.45, 0.0))
    return img


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
    for the same reason t_heights_air() is."""
    rnd = random.Random(seed)
    img = fill(tile(255), "metal", 5.0, rnd, grain=0.0)
    for _ in range(6):
        cx, cy = rnd.randrange(TS), rnd.randrange(TS)
        for dx in (-TS, 0, TS):
            for dy in (-TS, 0, TS):
                blob(img, "metal", cx + dx, cy + dy, rnd.uniform(2.4, 4.0),
                     rnd.uniform(1.4, 2.4), 4.9, lit=0.55, dark=0.55)
    speckle(img, "metal", rnd, 8, 5.0, (-0.4, 0.0))
    return img


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
        put(img, int(cx), top, "metal", 5.0)        # glint on the point
        put(img, int(cx) - 1, top + 1, "metal", 3.4)
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


# 2. SUNKEN RUINS
T_AT(220, t_ruin_stone(2201))                         # waterlogged ashlar
T_AT(221, t_ruin_stone(2211, algae=True))             # ... capped with algae
T_AT(222, t_ruin_wall(2221))                          # background masonry
T_AT(223, t_ruin_silt(2231))                          # cold silt
T_AT(224, t_ruin_deep(2241))                          # the flooded void
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
T_AT(244, t_heights_air(2441))                        # pale sky fill (bg)
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
T_AT(264, t_deep_void(2641))                          # tunnel void (bg)
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
T_AT(284, t_nest_void(2841))                          # the void (bg)
T_AT(285, t_nest_flue(2851))                          # flue (bg)
T_AT(286, t_nest_ledge(2861))                         # one-way ledge
T_AT(287, t_nest_shard(2871))                         # obsidian shards (hazard)
T_AT(288, t_nest_chain(2881))                         # chain (climbable)
T_AT(289, t_nest_vein(2891))                          # ember-veined flow (bg)
T_AT(290, t_nest_plate(2901))                         # riveted plate
T_AT(291, t_nest_crust(2911))                         # bubble crust (breakable)



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


def paint_edges(img, mask, rim, rnd):
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


def V(tid, build, seeds, group=None, rim=None):
    """One variant-capable tile. `seeds[0]` must reproduce the base tile
    exactly — the base atlas cell is reused as variant 0, and build_variants()
    asserts the two are pixel-identical so a mistyped seed cannot quietly
    change what an authored level looks like."""
    permille, decor = DECOR.get(tid, (0, []))
    return dict(id=tid, build=build, seeds=seeds, group=group, rim=rim,
                decor=decor, decor_permille=permille)


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
    V(224, t_ruin_deep, [2241, 22411, 22412, 22413, 22414, 22415]),
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
    V(244, t_heights_air, [2441, 24411, 24412, 24413, 24414, 24415]),
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
    V(264, t_deep_void, [2641, 26411, 26412, 26413, 26414, 26415]),
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
    V(284, t_nest_void, [2841, 28411, 28412, 28413, 28414, 28415]),
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
                        random.Random(spec["seeds"][0] * 131 + m * 17 + i))
            imgs.append(img)
        cases[m] = imgs
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
    path = os.path.join(TILES, "variants.json")
    with open(path, "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=False)
        f.write("\n")
    autotiled = sum(1 for s in VARIANT_SPECS if s["rim"] is not None)
    print("tileset.png  %d gameplay tiles + %d variants (%d autotiled materials)"
          % (len(TILE_DEFS), len(extra), autotiled))
    print("variants.json  %d cases per autotiled material" % len(BLOB_CASES))
