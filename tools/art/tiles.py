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

VARIANT_BASE = 32           # first free atlas row after the 28 gameplay ids

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
