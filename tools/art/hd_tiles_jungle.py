"""THE JUNGLE, and the tiles every world shares, drawn natively at 2x.

Ids 0-27 (data/tiles.json): the jungle's own set, the hub's four overworld
tiles, and the shared ones (water, switch blocks, lava, metal). The movement
verbs 200-215 are in hd_tiles_verbs.py; each other world has its own module.

This file is the worked example of docs/hd-tiles-howto.md. Its sections, in
order: the approved look-sample tiles (moved here from tiles.py unchanged in
design), the rest of the jungle, the overworld, the shared tiles, then the
2x twins of the jungle's edge dressers, accents and background decorations,
and finally the registrations.

Every painter takes the same seed as its 1x namesake in tiles.py, returns a
32x32 RGBA image in whole ramp steps, and draws its structures wrapped so a
fill tiles in both directions.
"""
import math
import random

from .hd_tilekit import (BIT_E, BIT_N, BIT_S, BIT_W, N, WU, blob, clear, corner_xy,
                         crack, decoration, dresser, ellipse, fill, get, grit, ink,
                         leaf, level_of, new, put, put_c, root, shift, side_xy, tile,
                         wave)
from .hd_tilekit import ACCENTS, CAP_ACCENTS
from .palette import auto_shade


# ============================================================ approved slice
# The eleven tiles of the H0 look sample the owner approved. Kept as drawn.
def t_dirt_hd(seed):
    rnd = random.Random(seed)
    img = fill(new(255), "dirt", 3.0, rnd, grain=0.32)
    for _ in range(7):                                   # clods
        blob(img, "dirt", rnd.uniform(0, N), rnd.uniform(0, N),
                rnd.uniform(3.0, 5.5), rnd.uniform(2.2, 3.8), 2.4, lit=1.0, dark=0.9)
    for _ in range(3):
        root(img, rnd, rnd.randrange(N), rnd.randrange(N), rnd.randrange(7, 13))
    for _ in range(4):                                   # pebbles, cast shadow
        blob(img, "stone", rnd.uniform(0, N), rnd.uniform(0, N),
                rnd.uniform(1.6, 2.8), rnd.uniform(1.3, 2.2), 2.9, shadow=1.3)
    for _ in range(9):                                   # grit: a lit grain on its shadow
        x, y = rnd.randrange(N), rnd.randrange(N)
        put(img, x, y, "dirt", 4.6)
        put(img, x + 1, y + 1, "dirt", 1.6)
    for _ in range(3):                                   # worm holes
        x, y = rnd.randrange(N), rnd.randrange(N)
        put(img, x, y, "dirt", 0.6)
        put(img, x + 1, y, "dirt", 1.2)
        put(img, x, y + 1, "dirt", 4.0)
    return img


def t_grass_top_hd(seed):
    """Sod over dirt. The top edge is a row of blades, not a ruler: the cap
    has a dark root mat, individual blades rising out of it with a lit left
    flank and a few hanging over the soil, and transparent notches between
    the tallest tips so the skyline of a ledge is grass-shaped."""
    rnd = random.Random(seed)
    img = t_dirt_hd(seed + 100)
    depth = []
    for x in range(N):                                 # the mat
        d = 7 + (1 if math.sin(x * math.pi / 8 + 1.0) > 0.3 else 0) + rnd.choice((0, 0, 1))
        for y in range(0, d):
            put(img, x, y, "grass", 3.6 - y * 0.32)
        put(img, x, d, "grass", 1.4)
        depth.append(d)
        for k in range(3):                               # sun on the soil below
            put(img, x, d + 1 + k, "dirt", 4.5 - k * 0.8)
    for x in range(N):                                 # top notches
        if x % 4 == 2 or (x % 7 == 0):
            img.putpixel((x, 0), (0, 0, 0, 0))
            if x % 8 == 2:
                img.putpixel((x, 1), (0, 0, 0, 0))
    for i in range(16):                                  # blades
        x = (i * 2 + rnd.choice((0, 1))) % N
        top = rnd.choice((0, 1, 1, 2))
        ln = rnd.randrange(4, 8)
        lean = rnd.choice((-1, 0, 1))
        for k in range(ln):
            bx = x + (lean if k < ln // 2 else 0)
            put(img, bx, top + k, "grass", 6.0 - k * 0.55)
            put(img, bx + 1, top + k + 1, "grass", 2.2)
    for _ in range(5):                                   # strands hanging into the soil
        x = rnd.randrange(N)
        for k in range(rnd.randrange(2, 5)):
            put(img, x, depth[x] + k, "grass", 3.0 - k * 0.5)
    for _ in range(2):                                   # a seed head
        x = rnd.randrange(2, N - 2)
        put(img, x, 2, "gold", 5)
        put(img, x, 3, "gold", 4)
    return img


def t_stone_hd(seed):
    """Two courses of half-offset blocks, 16 texels high. Each block has a
    two-texel sunlit top, a lit left arris, an occluded foot and right side;
    mortar is a dark joint with a lit lip under it; corners are chipped and a
    few faces carry pits, a hairline crack and a lichen spot."""
    rnd = random.Random(seed)
    img = new(255)
    jit = {}
    for y in range(N):
        course = y // 16
        ly = y % 16
        jx = 0 if course == 0 else 16
        for x in range(N):
            lx = (x - jx) % N
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
            put(img, x, y, "stone", lvl)
    # chipped arrises: a bite out of a block corner, dark inside, lit edge below
    for (bx, by) in ((2, 2), (29, 13), (18, 18), (13, 29), (31, 3)):
        for dy in range(3):
            for dx in range(3 - dy):
                put(img, bx + (dx if bx < 16 else -dx), by + (dy if by % 16 < 8 else -dy),
                       "stone", 1.2)
        put(img, bx + (3 if bx < 16 else -3), by, "stone", 4.4)
    for _ in range(10):                                  # pits
        x, y = rnd.randrange(4, 28), rnd.randrange(4, 28)
        if y % 16 < 4 or y % 16 > 13:
            continue
        put(img, x, y, "stone", 1.4)
        put(img, x + 1, y, "stone", 2.0)
        put(img, x, y + 1, "stone", 4.2)
    x, y = rnd.randrange(6, 14), 20                     # hairline crack
    for _ in range(9):
        put(img, x, y, "stone", 1.0)
        put(img, x + 1, y + 1, "stone", 4.0)
        x += 1
        y += rnd.choice((0, 1, 1, -1))
        if y % 16 < 3 or y % 16 > 13:
            break
    for (lx, ly) in ((22, 7), (23, 7), (22, 8), (6, 24)):  # lichen
        put(img, lx, ly, "grass", 4.0)
    put(img, 21, 8, "grass", 2.6)
    return img


def t_platform_hd(seed):
    """The one-way platform: eight texel rows of plank -- a sunlit top edge,
    grain lines that run along the board and swirl round a knot, butt joints
    between three boards, nail heads with a highlight and a rust streak, and a
    hard ink line under it. Thickness is the 1x four rows, in world units."""
    rnd = random.Random(seed)
    img = new(0)
    for x in range(N):
        for y in range(7):
            lvl = (5.6, 4.8, 4.0, 3.6, 3.4, 3.0, 2.0)[y]
            put(img, x, y, "wood", lvl)
        ink(img, x, 7)
    for gy, phase in ((2, 0.0), (4, 2.0), (5, 4.1)):   # grain
        for x in range(N):
            if math.sin(x * math.pi / 8 + phase + gy) > 0.15:
                put(img, x, gy, "wood", 2.6)
    kx = 20                                             # knot
    for (dx, dy, l) in ((0, 0, 1.4), (1, 0, 1.8), (-1, 0, 3.6), (0, -1, 3.8),
                        (2, 0, 2.6), (-2, 0, 4.2)):
        put(img, kx + dx, 3 + dy, "wood", l)
    for sx in (11, 27):                                  # butt joints
        for y in range(1, 7):
            put(img, sx, y, "wood", 1.2)
            put(img, sx + 1, y, "wood", 4.6)
    for nx in (3, 9, 14, 25, 30):                        # nails
        put(img, nx, 2, "metal", 6)
        put(img, nx + 1, 2, "metal", 3)
        put(img, nx, 3, "metal", 2)
        put(img, nx + 1, 3, "ember", 2)              # rust bleeding into the grain
    return img


VINE_MAP_HD = {'G': ("foliage", 2.4), 'g': ("foliage", 3.6), 'l': ("grass", 3.6),
               'L': ("grass", 2.5), 'm': ("foliage", 1.2), 'c': ("grass", 4.8)}


def t_vine_hd(seed):
    """The vine ladder: two stems twisting round each other (period 32, so it
    tiles vertically), with leaves alternating left and right -- each a pointed
    leaf with a midrib and a lit upper side -- and a curled tendril. Built as a
    material grid and lit with auto_shade like 1x, so it shades the same way."""
    rnd = random.Random(seed)
    g = [['.'] * N for _ in range(N)]

    def setc(x, y, ch, only=None):
        x, y = int(x), int(y) % N
        if 0 <= x < N and (only is None or g[y][x] in only):
            g[y][x] = ch

    for y in range(N):                                  # braided stems
        for k, ph in enumerate((0.0, math.pi)):
            cx = 15.5 + 2.2 * math.sin(y * 2 * math.pi / N + ph)
            front = math.cos(y * 2 * math.pi / N + ph) > 0
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
    a = 2 * math.pi / N
    v = (math.sin(a * x + 1.3 * math.sin(a * y * 2 + seed))
         + math.sin(a * y + 1.1 * math.sin(a * x * 2 + seed * 1.7))
         + 0.6 * math.sin(a * (x + y) * 2 + seed))
    return v


def t_water_hd(seed, surface=False):
    """Water: a body graded by depth, a caustic net of thin bright lines
    (periodic, so it tiles in both directions), and a couple of bubbles. The
    surface adds a swell of period 32 with foam on the rising faces, flecks of
    spray above it and a lit band just under it.

    H1: the net's phase and the bubbles come from the seed's random stream
    (the look sample keyed both to seed % 7 and fixed spots, so two of the four
    body paintings were the same net and every cell put its bubbles in the
    same place -- a lattice across a pool)."""
    rnd = random.Random(seed)
    phase = rnd.uniform(0, 7)
    img = new(255)
    for y in range(N):
        for x in range(N):
            lvl = 4.0
            if surface:
                lvl = 5.0 - min(y, 12) * 0.08
            c = _caustic(x, y, phase)
            if abs(c) < 0.16:
                lvl += 1.2                               # the net: thin ridges
            elif abs(c) < 0.42 and c > 0:
                lvl += 0.6
            put(img, x, y, "water", lvl)
    for (bx, by) in ((rnd.randrange(3, 13), rnd.randrange(16, 27)),
                     (rnd.randrange(18, 28), rnd.randrange(7, 15))):   # bubbles
        for (dx, dy) in ((0, -1), (-1, 0), (1, 0), (0, 1)):
            put(img, bx + dx, by + dy, "water", 6)
        put(img, bx - 1, by - 1, "metal", 6)
        put(img, bx + 3, by + 3, "water", 6)
    if surface:
        for x in range(N):
            swell = math.sin(x * 2 * math.pi / N)
            crest = int(round(2 - 2 * swell))           # 0..4 rows down
            for y in range(crest):
                img.putpixel((x, y), (0, 0, 0, 0))       # air above the swell
            put(img, x, crest, "metal", 6 if swell > -0.2 else 5)
            if swell > 0.3:                              # foam on the rising face
                put(img, x, crest + 1, "metal", 5)
                if swell > 0.8:
                    put(img, x, crest + 2, "metal", 4)
            put(img, x, crest + 2 + (1 if swell > 0.8 else 0), "water", 6)
            put(img, x, crest + 3 + (1 if swell > 0.8 else 0), "water", 5)
        for (x, y) in ((5, 0), (9, 1), (27, 4), (30, 2)):  # spray
            if img.getpixel((x, y))[3] == 0:
                put(img, x, y, "metal", 6)
    return img


def t_spikes_hd(seed):
    """Three iron spikes on a bolted plate. Each cone is lit down its left
    flank with a specular streak, shades round to its right, carries a rust
    stain at the root, and is inked down the dark side so the silhouette is
    a hazard at a glance."""
    img = new(0)
    for x in range(N):                                  # plate
        put(img, x, 26, "metal", 5)
        put(img, x, 27, "metal", 4)
        put(img, x, 28, "metal", 3)
        put(img, x, 29, "metal", 2)
        put(img, x, 30, "metal", 1)
        ink(img, x, 31)
    for bx in (3, 13, 23):                                # bolts
        put(img, bx, 27, "metal", 6)
        put(img, bx + 1, 27, "metal", 4)
        put(img, bx, 28, "metal", 3)
        put(img, bx + 1, 28, "metal", 1)
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
                put(img, x, y, "metal", lvl)
            if y > 22 and (y + int(cx)) % 2 == 0:         # rust at the root
                put(img, int(cx + 2), y, "ember", 1.6)
            ink(img, hi + 1 if hi + 1 < N else hi, y)
            ink(img, lo - 1 if lo > 0 else lo, y) if y < 10 else None
        ink(img, int(cx), 5)
        put(img, int(cx), 6, "metal", 6)               # tip glint
    return img


def t_crate_hd(seed):
    """Crate: a frame of four boards with mitred corners, three planks with
    grain and a knot, a diagonal brace with its own bevel, iron corner
    brackets and nails. Breakable reads from the planks and the brace."""
    rnd = random.Random(seed)
    img = new(255)
    for y in range(N):
        for x in range(N):
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
            put(img, x, y, "wood", lvl)
    for i in range(4, 28):                                # brace, bottom-left to top-right
        x, y = i, 31 - i
        put(img, x, y - 2, "wood", 4.8)
        put(img, x, y - 1, "wood", 3.8)
        put(img, x, y, "wood", 3.4)
        put(img, x, y + 1, "wood", 1.4)
    for (bx, by, sx, sy) in ((1, 1, 1, 1), (30, 1, -1, 1), (1, 30, 1, -1), (30, 30, -1, -1)):
        for k in range(5):                                # iron bracket
            put(img, bx + sx * k, by, "metal", 4 if sy > 0 else 2)
            put(img, bx, by + sy * k, "metal", 4 if sx > 0 else 2)
        put(img, bx + sx * 2, by + sy * 2, "metal", 6)
        put(img, bx + sx * 3, by + sy * 3, "metal", 1)
    for (nx, ny) in ((10, 6), (21, 6), (10, 22), (21, 22)):
        put(img, nx, ny, "metal", 6)
        put(img, nx + 1, ny + 1, "metal", 2)
    return img


def t_bg_leaves_hd(seed):
    """Background leaves: a mat of pointed leaves, each with a midrib, a lit
    upper edge and a shaded underside, held to the dark end of the foliage
    ramp so the player stays in front of it. Wrapped, so it tiles."""
    rnd = random.Random(seed)
    img = fill(new(255), "foliage", 0.9, rnd, grain=0.25, cell=4)
    for _ in range(16):
        cx, cy = rnd.uniform(0, N), rnd.uniform(0, N)
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
                put(img, x, y, "foliage", lvl)
    for _ in range(10):
        put(img, rnd.randrange(N), rnd.randrange(N), "foliage", 3)
    return img


def t_trunk_hd(seed):
    """Bark: six ribs whose grooves wander (period 32 vertically, so it
    tiles), each with a lit left shoulder; flakes, horizontal splits, a knot
    hole and a strand of moss in one groove."""
    rnd = random.Random(seed)
    img = new(255)
    edges = [0, 6, 11, 17, 22, 27, 32]
    for y in range(N):
        wob = [int(round(1.2 * math.sin(y * 2 * math.pi / N + i * 1.7))) if 0 < i < 6 else 0
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
                put(img, x, y, "wood", lvl + rnd.uniform(-0.3, 0.3))
    for _ in range(6):                                  # flakes
        x, y = rnd.randrange(N), rnd.randrange(N)
        for k in range(rnd.randrange(2, 4)):
            put(img, x, y + k, "wood", 4.2)
            put(img, x + 1, y + k, "wood", 1.0)
    for _ in range(3):                                  # splits
        x, y = rnd.randrange(N), rnd.randrange(N)
        for k in range(rnd.randrange(3, 6)):
            put(img, x + k, y, "wood", 0.6)
            put(img, x + k, y + 1, "wood", 3.6)
    for (dx, dy, l) in ((0, 0, 0.2), (1, 0, 0.2), (0, 1, 0.4), (1, 1, 0.8),
                        (-1, 0, 3.6), (0, -1, 3.8), (1, -1, 3.4), (2, 1, 1.4), (0, 2, 3.0)):
        put(img, 14 + dx, 18 + dy, "wood", l)        # knot hole
    for y in range(N):                                # moss in a groove
        if math.sin(y * 2 * math.pi / N) > -0.1:
            put(img, 22 + int(round(1.2 * math.sin(y * 2 * math.pi / N + 4 * 1.7))),
                    y, "grass", 2.6 + (0.8 if y % 3 == 0 else 0))
    return img



# ============================================================ the rest of the jungle
def _moss_cap(img, rnd, lo=4, hi=7):
    """A cushion of moss over the top of a block: a lit crown, lumps with
    their own light, a dark lower edge that casts onto the stone, and tufts
    hanging down out of it. Returns its depth per column."""
    s = rnd.randrange(1 << 20)
    depth = []
    for x in range(N):
        h = lo + int(round((hi - lo) * (wave(x, s) * 0.5 + 0.5)))
        h += 1 if rnd.random() < 0.25 else 0
        for y in range(h):
            put_c(img, x, y, "foliage", 4.4 - y * 0.5)
        put_c(img, x, 0, "foliage", 5.6 if wave(x, s + 1) > -0.35 else 4.6)
        put_c(img, x, h, "foliage", 1.0)
        shift(img, x, h + 1, -1)
        depth.append(h)
    for _ in range(5):                                   # cushions
        blob(img, "foliage", rnd.uniform(0, N), rnd.uniform(1.5, 3.5),
             rnd.uniform(2.5, 4.5), rnd.uniform(1.6, 2.4), 3.6, lit=1.6, dark=1.0,
             wrap=False)
    for _ in range(4):                                   # tufts hanging lower
        x = rnd.randrange(N)
        for k in range(rnd.randrange(3, 9)):
            put_c(img, x, depth[x] + k, "foliage", 3.2 - k * 0.3)
            shift(img, x + 1, depth[x] + k, -1)
    for _ in range(6):                                   # sporophytes catching the sun
        x = rnd.randrange(N)
        put_c(img, x, 0, "grass", 4)
        put_c(img, x, 1, "foliage", 5)
    return depth


def t_stone_mossy_hd(seed):
    """Tile 4: the cut stone with a moss cap. Lichen also creeps into the
    upper mortar joint, which is where the damp sits."""
    rnd = random.Random(seed)
    img = t_stone_hd(seed)
    _moss_cap(img, rnd)
    for _ in range(3):
        x = rnd.randrange(N)
        for k in range(rnd.randrange(2, 5)):
            if level_of(get(img, x + k, 16)) and level_of(get(img, x + k, 16))[1] <= 1:
                put(img, x + k, 16, "foliage", 2)
    return img


def t_bg_rock_hd(seed):
    """Background rock: a conglomerate face of bedded boulders, each lit on
    its upper left and seated in its own shadow, with hairline cracks. Held
    at the dark, low-contrast end of the ramp like 1x."""
    rnd = random.Random(seed)
    img = fill(new(255), "stone", 1.25, rnd, grain=0.3, cell=4)
    for _ in range(4):
        blob(img, "stone", rnd.uniform(0, N), rnd.uniform(0, N),
             rnd.uniform(5.0, 9.0), rnd.uniform(3.5, 6.0), 0.6, lit=0.9, dark=0.5,
             shadow=0.6)
    for _ in range(3):
        crack(img, "stone", rnd.randrange(N), rnd.randrange(N), rnd.randrange(8, 15),
              1.6, rnd, drift=(-1, 0, 1))
    grit(img, rnd, "stone", 10, 2.4, 0.4)
    return img


def t_bg_dark_hd(seed):
    """The void behind everything: almost flat, on purpose. A mottle of
    one step and a scatter of specks, so it is a surface and not a hole."""
    rnd = random.Random(seed)
    img = fill(new(255), "stone", 0.25, rnd, grain=0.2, cell=4)
    for _ in range(2):
        ellipse(img, "stone", rnd.uniform(0, N), rnd.uniform(0, N),
                rnd.uniform(2.0, 3.5), rnd.uniform(1.2, 2.2), 1)
    for _ in range(12):
        x, y = rnd.randrange(N), rnd.randrange(N)
        put(img, x, y, "stone", 1 if rnd.random() < 0.8 else 2)
    return img


def _sod_over_shoulder(img, rnd, side, run_min=8, run_max=16):
    """The grass mat wrapping over an exposed shoulder: a tongue of turf that
    thins as it hangs down the face, its own shadow line on the soil, and a
    few loose strands below it. Lit on the left face, shaded on the right."""
    lit = side == "left"
    s = rnd.randrange(1 << 20)
    run = rnd.randrange(run_min, run_max)
    for y in range(run + 4):
        w = int(round(4.4 * (1 - y / float(run + 3)) + wave(y, s, period=64) * 1.3))
        for k in range(max(0, w)):
            x, py = side_xy(side, k, y)
            put_c(img, x, py, "grass", (4.6 if lit else 3.4) - y * 0.16 - k * 0.4)
        if w > 0:
            x, py = side_xy(side, w, y)
            put_c(img, x, py, "grass", 1.2)
    for _ in range(3):
        k = rnd.randrange(0, 3)
        y0 = rnd.randrange(3, run)
        for j in range(rnd.randrange(4, 10)):
            x, py = side_xy(side, k, y0 + j)
            put_c(img, x, py, "grass", (4.0 if lit else 3.0) - j * 0.25)


def t_grass_edge_hd(seed, side):
    """Tiles 16/17: the left or right end of a grass platform. The cliff face
    is lit (left) or occluded (right) four texels deep, the turf wraps over the
    shoulder and hangs down it, and the top corner is rounded off."""
    rnd = random.Random(seed)
    img = t_grass_top_hd(seed)
    deltas = (2, 1, 1, 0) if side == "left" else (-2, -1, -1, 0)
    for y in range(N):
        for k in range(4):
            x, py = side_xy(side, k, y)
            shift(img, x, py, deltas[k])
    _sod_over_shoulder(img, rnd, side, 12, 20)
    corner = "nw" if side == "left" else "ne"
    for (x, y) in ((0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (0, 2)):
        clear(img, *corner_xy(corner, x, y))
    for (x, y) in ((3, 0), (2, 1), (1, 2), (0, 3)):
        px, py = corner_xy(corner, x, y)
        put_c(img, px, py, "grass", 5 if side == "left" else 3)
    return img


# ------------------------------------------------------------- the bridge
def t_bridge_hd(seed):
    """Rope bridge (one-way): a sag of separate planks, each with a lit top
    edge, grain and its own tone, two ropes threaded under them that show in
    the gaps with a lashing at every plank, and a knotted anchor at each end."""
    rnd = random.Random(seed)
    img = new(0)

    def top_at(x):
        t = (x + 0.5 - N / 2.0) / (N / 2.0)
        return 4 + int(round(5.2 * (1.0 - t * t)))

    tone = {}
    for x in range(N):
        top = top_at(x)
        plank = (x + 3) // 8
        gap = (x + 3) % 8 == 7
        if plank not in tone:
            tone[plank] = rnd.uniform(-0.45, 0.45)
        if gap:
            put_c(img, x, top + 2, "straw", 3)             # the rope, seen in the gap
            put_c(img, x, top + 3, "straw", 1)
            continue
        t = tone[plank]
        put_c(img, x, top, "wood", 5.4 + t)
        put_c(img, x, top + 1, "wood", 4.0 + t)
        put_c(img, x, top + 2, "wood", 3.3 + t)
        put_c(img, x, top + 3, "wood", 2.4 + t)
        put_c(img, x, top + 4, "wood", 1.4)
        if (x + plank) % 4 == 1:
            put_c(img, x, top + 2, "wood", 2.4 + t)        # grain
        if (x + 3) % 8 == 0:                                 # a lashing at each plank end
            put_c(img, x, top + 3, "straw", 4)
    for ax in (0, N - 3):                                    # anchors
        for y in range(1, 7):
            for k in range(3):
                put_c(img, ax + k, y, "straw", (4 if k == 0 else 3 if k == 1 else 2)
                      - (0.6 if y % 2 else 0))
        put_c(img, ax + 1, 0, "straw", 5)
        put_c(img, ax, 7, "straw", 2)
        put_c(img, ax + 2, 7, "straw", 1)
    return img


# ============================================================ the overworld
# Top-down: ambient light, no side bevel, as at 1x.
def t_hub_grass_hd(seed):
    """Meadow: mottled turf, and tufts as little fans of blades -- lit tips,
    a dark heart and a shadow at the root -- instead of single bright dots.
    Still no flowers in the fill (tiles.py says why)."""
    rnd = random.Random(seed)
    img = fill(new(255), "grass", 2.4, rnd, grain=0.35, cell=3)
    for _ in range(7):
        blob(img, "grass", rnd.uniform(0, N), rnd.uniform(0, N), rnd.uniform(3.6, 6.4),
             rnd.uniform(2.8, 4.8), 1.6, lit=0.8, dark=0.8)
    for _ in range(8):
        x, y = rnd.randrange(N), rnd.randrange(N)
        put(img, x + 1, y + 1, "grass", 1.0)
        for dx, h in ((-1, rnd.randrange(2, 4)), (0, rnd.randrange(3, 5)),
                      (1, rnd.randrange(2, 4))):
            for k in range(h):
                bx = x + dx * (1 if k >= h - 1 else 0) + (dx if k >= 2 else 0)
                put(img, bx, y - k, "grass", 3.0 + k * 0.7)
    for _ in range(10):
        x, y = rnd.randrange(N), rnd.randrange(N)
        put(img, x, y, "foliage", 3)
        put(img, x + 1, y, "foliage", 2)
    return img


def t_hub_path_hd(seed):
    """Trodden sand: patches of tracked-in earth, pebbles each seated in a
    shadow, and grit."""
    rnd = random.Random(seed)
    img = fill(new(255), "dirt", 4.8, rnd, grain=0.2)
    for _ in range(3):                                   # tracked-in earth: soft, no rim
        ellipse(img, "dirt", rnd.uniform(0, N), rnd.uniform(0, N), rnd.uniform(3.0, 5.5),
                rnd.uniform(1.8, 3.0), 4)
    for _ in range(14):                                  # sand grains, light and dark
        put(img, rnd.randrange(N), rnd.randrange(N), "dirt", rnd.choice((4, 6)))
    for _ in range(4):
        blob(img, "stone", rnd.uniform(0, N), rnd.uniform(0, N), rnd.uniform(1.2, 2.0),
             rnd.uniform(1.0, 1.6), 3.2, shadow=1.0)
    grit(img, rnd, "dirt", 8, 5.6, 4.0)
    return img


def t_hub_water_hd(seed):
    """Pond seen from above: a faint caustic net, and ripple rings drawn as
    ellipses -- the far arc catching the sky, the near arc in shadow."""
    rnd = random.Random(seed)
    img = fill(new(255), "water", 4.6, rnd, grain=0.3, cell=4)
    for y in range(N):
        for x in range(N):
            if abs(_caustic(x, y, seed % 7)) < 0.13:
                shift(img, x, y, +1, wrap=True)
    for _ in range(4):
        cx, cy = rnd.uniform(0, N), rnd.uniform(0, N)
        r = rnd.uniform(3.5, 8.5)
        for a in range(0, 360, 4):
            x = cx + r * math.cos(math.radians(a))
            y = cy + r * 0.6 * math.sin(math.radians(a))
            put(img, x, y, "water", 6 if a > 180 else 3)
    for _ in range(5):
        x, y = rnd.randrange(N), rnd.randrange(N)
        put(img, x, y, "metal", 6)
    return img


def t_hub_tree_hd(seed):
    """Overworld tree from above: a crown of leaf clusters, sunlit on the
    upper left with single leaves standing out of the mass, a dark rim on the
    shadow side, and (on most variants) a short trunk with roots. The same
    random walk as 1x, so trunk placement and the canopy-only third survive."""
    rnd = random.Random(seed)
    img = new(0)
    for _ in range(14):
        blob(img, "foliage", rnd.randrange(2, 14) * WU, rnd.randrange(1, 9) * WU,
             rnd.uniform(2.4, 4.0) * WU, rnd.uniform(2.0, 3.2) * WU, 3.0, wrap=False)
    for _ in range(9):
        blob(img, "grass", rnd.randrange(2, 13) * WU, rnd.randrange(0, 6) * WU,
             rnd.uniform(1.4, 2.6) * WU, rnd.uniform(1.1, 2.0) * WU, 2.6, wrap=False)
    tx = rnd.randrange(4, 9) * WU
    tw = rnd.randrange(3, 5) * WU
    top = (8 + rnd.randrange(0, 3)) * WU
    canopy_only = rnd.random() > 0.72
    lr = random.Random(seed * 7 + 1)
    for _ in range(22):                                  # leaves standing proud of the mass
        x, y = lr.uniform(2, N - 2), lr.uniform(1, 20)
        if get(img, x, y)[3] == 0:
            continue
        ramp = "grass" if y < 12 and lr.random() < 0.6 else "foliage"
        leaf(img, x, y, lr.uniform(0, 2 * math.pi), lr.uniform(3.0, 5.0),
             lr.uniform(1.2, 1.8), ramp, 3.4 if ramp == "foliage" else 3.0, wrap=False)
    px = img.load()
    rim = []
    for y in range(N):
        for x in range(N):
            if px[x, y][3] and (x + 1 >= N or y + 1 >= N or not px[x + 1, y][3]
                                or not px[x, y + 1][3]):
                rim.append((x, y))
    for x, y in rim:                                     # the crown's shadow side
        shift(img, x, y, -2)
    if canopy_only:
        for x in range(6, 26):
            put_c(img, x, N - 1, "foliage", 2.6 + lr.uniform(-0.5, 0.5))
            put_c(img, x, N - 2, "foliage", 1.6)
        return img
    for y in range(top, N):
        for x in range(tx, tx + tw):
            lvl = 3.4
            if x == tx:
                lvl += 1.6
            elif x == tx + 1:
                lvl += 0.8
            elif x == tx + tw - 1:
                lvl -= 1.6
            elif x == tx + tw - 2:
                lvl -= 0.7
            if (x - tx) % 3 == 2 and 0 < x - tx < tw - 1:
                lvl -= 0.8                               # bark furrow
            put_c(img, x, y, "wood", lvl)
    for x in range(tx, tx + tw):                         # the crown's shadow on the trunk
        put_c(img, x, top, "wood", 1.2)
        put_c(img, x, top + 1, "wood", 2.2)
    for x in range(max(0, tx - 4), min(N, tx + tw + 4)):
        put_c(img, x, N - 1, "grass", 2.6 + lr.uniform(-0.6, 0.6))
        if tx - 2 <= x < tx + tw + 2:
            put_c(img, x, N - 2, "wood", 2.6 if x < tx else 1.8)   # root flare
    return img


# ============================================================ shared tiles
def t_lava_hd(seed):
    """Molten rock: plates of cooled crust, each lit on its upper left and
    falling into shadow, floating on a glowing seam network that is brightest
    at its core and bleeds onto the plate edges; a molten skin along the top
    and a few bubbles. Plates are a periodic cell pattern, so it tiles (and
    tile_anim.png scrolls it vertically without a seam)."""
    rnd = random.Random(seed)
    pts = [(rnd.uniform(0, N), rnd.uniform(0, N)) for _ in range(7)]
    img = new(255)
    for y in range(N):
        for x in range(N):
            best = []
            for (px, py) in pts:
                for ox in (-N, 0, N):
                    for oy in (-N, 0, N):
                        cx, cy = px + ox, py + oy
                        dx, dy = x + 0.5 - cx, y + 0.5 - cy
                        best.append((math.hypot(dx, dy), dx, dy, cx, cy))
            best.sort()
            d1, dx, dy, ax, ay = best[0]
            d2, _, _, bx, by = best[1]
            # distance to the seam: the bisector of the two nearest plates
            s = (d2 * d2 - d1 * d1) / (2.0 * max(0.5, math.hypot(ax - bx, ay - by)))
            if s < 0.55:
                lvl = 6
            elif s < 1.1:
                lvl = 5
            elif s < 1.8:
                lvl = 3.6
            else:
                facing = -(dx + dy) / max(d1, 0.5)
                lvl = 1.9 + facing * 0.8 - min(d1, 8) * 0.07
            put(img, x, y, "ember", lvl)
    for y, skin in enumerate((6.2, 5.6, 5.0, 4.4)):
        for x in range(N):
            m = level_of(get(img, x, y))
            if m and m[1] < skin:
                put(img, x, y, "ember", skin - (0.6 if (x + y * 3) % 7 == 0 else 0))
    for (bx, by) in ((8, 18), (22, 25), (16, 11)):
        for (ddx, ddy) in ((0, -1), (-1, 0), (1, 0), (0, 1)):
            put(img, bx + ddx, by + ddy, "ember", 5)
        put(img, bx, by, "ember", 6)
        put(img, bx - 1, by - 1, "gold", 6)
    return img


def t_metal_hd(seed):
    """Tread plate: a bevelled slab (lit top and left, occluded bottom and
    right), a diamond tread of raised bars each with its own highlight and
    shadow, domed rivets in the corners, and per-variant scratches and a
    rust bloom."""
    rnd = random.Random(seed)
    img = new(255)
    for y in range(N):
        for x in range(N):
            lvl = 3.2
            lvl = {0: 5.8, 1: 5.0, 2: 4.2, N - 1: 0.8, N - 2: 1.6, N - 3: 2.4}.get(y, lvl)
            if x == 0:
                lvl = min(lvl + 1.3, 5.8)
            elif x == 1:
                lvl = min(lvl + 0.6, 5.8)
            elif x == N - 1:
                lvl -= 1.4
            elif x == N - 2:
                lvl -= 0.7
            put(img, x, y, "metal", lvl)
    for row, cy in enumerate(range(7, 26, 6)):
        for cx in range(5 + (row % 2) * 5, 28, 10):
            sgn = 1 if (row + cx // 10) % 2 == 0 else -1
            for k in range(-2, 2):
                x, y = cx + k, cy + sgn * k
                put(img, x, y, "metal", 4.6)
                put(img, x + 1, y + 1 - (1 if sgn < 0 else 0), "metal", 2.0)
    for (rx, ry) in ((4, 5), (27, 5), (4, 26), (27, 26)):
        blob(img, "metal", rx, ry, 2.2, 2.2, 3.0, shadow=1.0, wrap=False)
        put(img, rx - 1, ry - 1, "metal", 6)
    for _ in range(rnd.randrange(1, 4)):                 # scratches, catching the light
        x, y = rnd.randrange(6, 22), rnd.randrange(8, 24)
        for k in range(rnd.randrange(4, 8)):
            if level_of(get(img, x + k, y - k // 2))[1] == 3:
                put_c(img, x + k, y - k // 2, "metal", 4)
    if rnd.random() < 0.6:                               # rust weeping from a rivet
        rx, ry = rnd.choice(((4, 5), (27, 5), (4, 26)))
        for k in range(rnd.randrange(3, 7)):
            put_c(img, rx + rnd.choice((-1, 0, 1)), ry + 3 + k, "ember", 2 if k < 3 else 1)
    return img


def _rune(x, y, glyph):
    """Ring membership and the outward normal of the switch rune at a texel."""
    dx, dy = x + 0.5 - 16.0, y + 0.5 - 15.0
    if glyph == "diamond":
        d = abs(dx) + abs(dy)
        on, outer = 5.5 <= d <= 8.5, d > 7.0
    else:
        d = max(abs(dx), abs(dy))
        on, outer = 5.0 <= d <= 7.5, d > 6.25
    nx = (1 if dx > 0 else -1) if abs(dx) >= abs(dy) or glyph == "diamond" else 0
    ny = (1 if dy > 0 else -1) if abs(dy) >= abs(dx) or glyph == "diamond" else 0
    return on, outer, nx, ny


def t_switch_on_hd(ramp, seed, glyph):
    """Switch block, solid state: a machined block with a two-step bevel, a
    recessed panel whose lower-right walls catch the light, a brushed face,
    four screws, and the raised rune -- lit on the faces that look up-left,
    with a drop shadow into the panel."""
    rnd = random.Random(seed)
    img = new(255)
    for y in range(N):
        for x in range(N):
            if y == N - 1:
                lvl = 0.2
            elif y == N - 2:
                lvl = 1.0
            elif x <= 1 or y <= 1 or x >= N - 2:
                lit = y <= 1 or x <= 1
                lvl = (5.8 if (x == 0 or y == 0) else 5.0) if lit else (1.4 if x == N - 1 else 2.0)
            elif x <= 3 or y <= 3 or x >= N - 4 or y >= N - 5:
                lvl = 4.4 if (y <= 3 or x <= 3) else 2.2
            elif y == 4 or x == 4:
                lvl = 1.4                                # panel wall in shadow
            elif y == N - 6 or x == N - 5:
                lvl = 3.6                                # panel wall catching light
            else:
                lvl = 2.6 + (0.6 if (y * 5 + x // 6) % 11 == 0 else 0)
                lvl += rnd.uniform(-0.2, 0.2)
            put(img, x, y, ramp, lvl)
    for (sx, sy) in ((2, 2), (N - 3, 2), (2, N - 4), (N - 3, N - 4)):
        put(img, sx, sy, ramp, 6)
        put(img, sx + 1, sy + 1, ramp, 1)
    for y in range(5, N - 6):
        for x in range(5, N - 5):
            on, outer, nx, ny = _rune(x, y, glyph)
            if not on:
                continue
            facing = -(nx + ny) if outer else (nx + ny)
            put(img, x, y, ramp, 6 if facing > 0 else 4)
            if not _rune(x + 1, y + 1, glyph)[0]:
                put(img, x + 1, y + 1, ramp, 1.2)
    put(img, 15, 14, ramp, 6)
    put(img, 16, 14, ramp, 5)
    put(img, 15, 15, ramp, 5)
    put(img, 16, 15, ramp, 3)
    return img


def t_switch_off_hd(ramp, seed, glyph):
    """Switch block, ghost state: a dashed outline (a lit dash with a fainter
    inner texel) and every other segment of the rune at partial alpha. Mostly
    transparent, so it reads as not there."""
    img = new(0)
    for x in range(N):
        if (x // 4) % 2 == 0:
            put_c(img, x, 0, ramp, 4.6)
            put_c(img, x, 1, ramp, 4.6, alpha=110)
            put_c(img, x, 29, ramp, 3.4)
            put_c(img, x, 28, ramp, 3.4, alpha=110)
    for y in range(2, 28):
        if (y // 4) % 2 == 0:
            put_c(img, 0, y, ramp, 4.6)
            put_c(img, 1, y, ramp, 4.6, alpha=110)
            put_c(img, N - 1, y, ramp, 3.4)
            put_c(img, N - 2, y, ramp, 3.4, alpha=110)
    for y in range(5, N - 6):
        for x in range(5, N - 5):
            on, outer, _, _ = _rune(x, y, glyph)
            if on and ((x + y) // 3) % 2 == 0:
                put_c(img, x, y, ramp, 4.0, alpha=170 if outer else 120)
    return img


# ============================================================ edge dressers
@dresser("dress_earth")
def dress_earth_hd(img, mask, rnd, crust=True):
    """Exposed earth: pebbles bedded under a sunlit crust, soil crumbling off
    an underside (with a few crumbs gone, so the edge is not a ruler), and cut
    root ends -- a lit ring round a dark heart -- in the side faces."""
    if crust and not mask & BIT_N:
        for _ in range(3):
            blob(img, "stone", rnd.uniform(3, N - 3), rnd.uniform(5, 9), rnd.uniform(1.6, 2.6),
                 rnd.uniform(1.3, 2.0), 3.4, shadow=1.2, wrap=False)
    if not mask & BIT_S:
        s = rnd.randrange(1 << 20)
        for x in range(N):
            d = int(round((wave(x, s) * 0.5 + 0.5) * 4)) + (1 if rnd.random() < 0.25 else 0)
            for k in range(d):
                put_c(img, x, N - 1 - k, "dirt", 1.0 + k * 0.45)
            if d and rnd.random() < 0.14:
                clear(img, x, N - 1)
        for _ in range(3):                               # root threads to the underside
            x = rnd.randrange(2, N - 2)
            for k in range(rnd.randrange(3, 7)):
                put_c(img, x, N - 1 - k, "wood", 2.6)
                put_c(img, x - 1, N - 1 - k, "wood", 3.6)
    for side, bit in (("left", BIT_W), ("right", BIT_E)):
        if mask & bit:
            continue
        for _ in range(2):
            y = rnd.uniform(6, 26)
            x = 2.0 if side == "left" else N - 2.0
            blob(img, "wood", x, y, rnd.uniform(1.4, 2.0), rnd.uniform(1.6, 2.2), 2.4,
                 lit=1.6, dark=1.2, wrap=False)
            put_c(img, int(x), int(y), "wood", 1)


@dresser("dress_sod")
def dress_sod_hd(img, mask, rnd):
    """Grass-topped earth: everything above, plus the turf wrapping over any
    exposed shoulder (what tiles 16 and 17 do by hand)."""
    dress_earth_hd(img, mask, rnd, crust=False)
    for side, bit in (("left", BIT_W), ("right", BIT_E)):
        if not mask & bit:
            _sod_over_shoulder(img, rnd, side)


@dresser("dress_stone")
def dress_stone_hd(img, mask, rnd):
    """Cut stone: an exposed arris is chipped in a few places -- a rounded
    bite, dark inside, its floor catching the light on a top or left face."""
    for side, bit in (("top", BIT_N), ("bottom", BIT_S), ("left", BIT_W), ("right", BIT_E)):
        if mask & bit:
            continue
        for _ in range(3):
            i = rnd.randrange(2, N - 7)
            w = rnd.randrange(3, 6)
            dmax = rnd.randrange(2, 4)
            for j in range(w):
                d = max(1, int(round(dmax * math.sin(math.pi * (j + 0.5) / w))))
                for k in range(d):
                    x, y = side_xy(side, k, i + j)
                    put_c(img, x, y, "stone", 1.0 if k < d - 1 else 1.6)
                x, y = side_xy(side, d, i + j)
                put_c(img, x, y, "stone", 4.4 if side in ("top", "left") else 1.4)


@dresser("dress_bg_rock")
def dress_bg_rock_hd(img, mask, rnd):
    """Background rock stays quiet: only short runs of its exposed lip catch
    any light, held two steps down."""
    if not mask & BIT_N:
        x = 0
        while x < N:
            if rnd.random() < 0.3:
                for k in range(rnd.randrange(2, 6)):
                    put_c(img, x + k, 0, "stone", 2.4)
                    put_c(img, x + k, 1, "stone", 1.8)
                x += 6
            else:
                x += 1


@dresser("dress_hub_grass")
def dress_hub_grass_hd(img, mask, rnd):
    """Top-down meadow edge: blades lean out over whatever it ends against,
    each a short lit stroke pointing outward with a dark root."""
    for side, bit in (("top", BIT_N), ("bottom", BIT_S), ("left", BIT_W), ("right", BIT_E)):
        if mask & bit:
            continue
        for i in range(0, N, 2):
            if rnd.random() < 0.55:
                h = rnd.randrange(2, 6)
                lean = rnd.choice((-1, 0, 1))
                for k in range(h):
                    x, y = side_xy(side, k, i + (lean if k < 2 else 0))
                    put_c(img, x, y, "grass", 4.6 - k * 0.6 + rnd.uniform(-0.4, 0.4))
                x, y = side_xy(side, h, i)
                put_c(img, x, y, "grass", 1.4)


@dresser("dress_hub_path")
def dress_hub_path_hd(img, mask, rnd):
    """Top-down path: gravel piles up along the kerb, pebble on pebble."""
    for side, bit in (("top", BIT_N), ("bottom", BIT_S), ("left", BIT_W), ("right", BIT_E)):
        if mask & bit:
            continue
        for _ in range(3):
            x, y = side_xy(side, rnd.uniform(1, 3), rnd.uniform(1, N - 1))
            blob(img, "stone", x, y, rnd.uniform(1.2, 1.9), rnd.uniform(1.0, 1.6), 3.2,
                 shadow=1.0, wrap=False)


# ============================================================ accents
def pebble(img, rnd, ramp, lvl, y0=0):
    """A stone sitting in the top face: lit crown, body, a dark seat."""
    x = rnd.uniform(5, N - 9)
    rx, ry = rnd.uniform(3.0, 4.2), rnd.uniform(2.2, 2.8)
    cy = y0 + ry + 0.5
    for xx in range(int(x - rx - 1), int(x + rx + 2)):           # its seat
        put_c(img, xx, int(cy + ry), ramp, 0)
    blob(img, ramp, x, cy, rx, ry, lvl - 0.6, lit=1.6, dark=1.4, wrap=False)
    put_c(img, int(x - rx * 0.4), int(cy - ry * 0.6), ramp, min(6, lvl + 2))


def chip(img, rnd, ramp, lip):
    """A bite out of the lip: the course stops, the broken face below is in
    shadow, and the far side of the break catches the light."""
    x = rnd.randrange(4, N - 12)
    w = rnd.randrange(6, 10)
    for k in range(w):
        d = 2 + int(round(2.2 * math.sin(math.pi * (k + 0.5) / w)))
        for y in range(d):
            if y == 0 and (k == 0 or k == w - 1):
                clear(img, x + k, 0)
            else:
                put_c(img, x + k, y, ramp, 0 if y < d - 1 else 1)
        put_c(img, x + k, d, ramp, 2)
    put_c(img, x + w, 0, ramp, min(6, lip + 1))
    put_c(img, x + w, 1, ramp, lip)
    put_c(img, x + w, 2, ramp, lip - 1)


def crack_down(img, rnd, ramp, depth=7):
    """A crack opening from the lip down into the face, one texel wide with
    a lit right lip, branching once."""
    x = rnd.randrange(6, N - 6)
    for y in range(depth * WU):
        put_c(img, x, y, ramp, 0)
        put_c(img, x + 1, y, ramp, 4)
        if y == depth and rnd.random() < 0.7:
            bx = x
            for k in range(rnd.randrange(3, 6)):
                bx -= 1
                put_c(img, bx, y + k, ramp, 0)
                put_c(img, bx, y + k + 1, ramp, 4)
        x = max(2, min(N - 3, x + rnd.choice((-1, 0, 0, 1))))


def flower(img, rnd):
    """A small yellow flower on the sod: a stem with one leaf, five petals
    lit from the upper left, and a darker heart."""
    x = rnd.randrange(6, N - 8)
    for y in range(4, 11):
        put_c(img, x, y, "grass", 3)
        put_c(img, x + 1, y, "grass", 1.6)
    leaf(img, x + 1, 8, -0.5, 4, 1.3, "grass", 3.6, wrap=False)
    for (dx, dy, st) in ((0, -2, 6), (-2, 0, 6), (2, 0, 5), (-1, 2, 5), (1, 2, 4),
                         (-1, -1, 6), (1, -1, 5), (-1, 1, 5), (1, 1, 4), (0, -1, 6),
                         (-1, 0, 6), (1, 0, 5), (0, 1, 5)):
        put_c(img, x + dx, 3 + dy, "gold", st)
    put_c(img, x, 3, "ember", 4)


ACCENTS["earth"] = [lambda i, r: pebble(i, r, "stone", 4),
                    lambda i, r: crack_down(i, r, "dirt")]
ACCENTS["stone"] = [lambda i, r: chip(i, r, "stone", 5),
                    lambda i, r: crack_down(i, r, "stone")]
CAP_ACCENTS[2] = [flower, lambda i, r: pebble(i, r, "stone", 4, y0=12)]


# ============================================================ decorations
# Background-layer dressing, picked by position hash (tiles.DECOR). These five
# are used by every world's background walls, so a world that redraws its
# walls gets them for free; the world-specific ones live in each world module.
@decoration("d_crack")
def d_crack_hd(img, rnd):
    x = rnd.randrange(6, 26)
    y = rnd.randrange(0, 8)
    crack(img, "stone", x, y, 22, 1.8, rnd, drift=(-1, 0, 1), wrap=False)
    if rnd.random() < 0.6:
        crack(img, "stone", x + rnd.choice((-4, 4)), y + 10, 10, 1.7, rnd, wrap=False)
    return img


@decoration("d_roots")
def d_roots_hd(img, rnd):
    """A woody root crossing the cell: a lit shoulder, a bark body with
    furrows, its own shadow, and rootlets dropping off it."""
    y = rnd.randrange(5, 24)
    x = 0
    while x < N:
        run = rnd.randrange(4, 9)
        for _ in range(run):
            if x >= N:
                break
            put_c(img, x, y - 2, "wood", 4.2)
            put_c(img, x, y - 1, "wood", 3.2)
            put_c(img, x, y, "wood", 2.6 if x % 5 else 1.8)
            put_c(img, x, y + 1, "wood", 2.0)
            shift(img, x, y + 2, -1)
            x += 1
        y = max(3, min(N - 4, y + rnd.choice((-1, 0, 0, 1))))
    for _ in range(3):
        rx, ry = rnd.randrange(N), y + 2
        for k in range(rnd.randrange(4, 10)):
            put_c(img, rx, ry + k, "wood", 2.4)
            if rnd.random() < 0.3:
                rx += rnd.choice((-1, 1))
    return img


@decoration("d_vines")
def d_vines_hd(img, rnd):
    """One or two strands hanging from the top of the cell: a stem lit on
    its left with leaves off it in turn, each a small pointed leaf."""
    for _ in range(rnd.randrange(1, 3)):
        x = rnd.randrange(3, N - 4)
        run = rnd.randrange(18, N + 1)
        for y in range(run):
            put_c(img, x, y, "foliage", 3.4)
            put_c(img, x + 1, y, "foliage", 2.0)
            if y % 6 == 3:
                left = (y // 6) % 2 == 0
                leaf(img, x + (0 if left else 1), y, (math.pi * 0.8) if left else 0.35,
                     4.5, 1.5, "grass", 3.0, wrap=False)
            if rnd.random() < 0.15:
                x = max(3, min(N - 4, x + rnd.choice((-1, 1))))
    return img


@decoration("d_moss")
def d_moss_hd(img, rnd):
    """A patch of moss where damp collects: soft cushions with lit crowns
    and a speckle of sporophytes."""
    for _ in range(rnd.randrange(3, 6)):
        blob(img, "foliage", rnd.uniform(0, N), rnd.uniform(0, N), rnd.uniform(4, 7),
             rnd.uniform(2.4, 4.4), 2.2, lit=1.0, dark=0.8)
    for _ in range(18):
        x, y = rnd.randrange(N), rnd.randrange(N)
        if level_of(get(img, x, y)) and level_of(get(img, x, y))[0] == "foliage":
            put(img, x, y, "foliage", 4)
    return img


@decoration("d_bones")
def d_bones_hd(img, rnd):
    """Old roots gone to splinters: pale slivers with a shadow under each."""
    for _ in range(rnd.randrange(2, 4)):
        x, y = rnd.randrange(4, 22), rnd.randrange(4, 26)
        run = rnd.randrange(6, 13)
        for k in range(run):
            yy = y + (k // 4)
            put_c(img, x + k, yy, "metal", 4.8 if k < run - 2 else 3.6)
            put_c(img, x + k, yy + 1, "metal", 2.0)
        put_c(img, x, y - 1, "metal", 5.6)
    return img


# ============================================================ registrations
# id, the seed its T() line uses, painter. Order follows data/tiles.json.
tile(1, 11)(t_dirt_hd)
tile(2, 12)(t_grass_top_hd)
tile(3, 21)(t_stone_hd)
tile(4, 22)(t_stone_mossy_hd)
tile(5, 5)(t_platform_hd)
tile(6, 6)(t_vine_hd)
tile(7, 31)(lambda s: t_water_hd(s, surface=True))
tile(8, 32)(t_water_hd)
tile(9, 9)(t_spikes_hd)
tile(10, 7)(t_crate_hd)
tile(11, 11)(lambda s: t_switch_on_hd("gold", s, "diamond"))
tile(12, 12)(lambda s: t_switch_on_hd("purple", s, "square"))
tile(13, 41)(t_bg_leaves_hd)
tile(14, 14)(t_trunk_hd)
tile(15, 51)(t_bg_rock_hd)
tile(16, 13)(lambda s: t_grass_edge_hd(s, "left"))
tile(17, 14)(lambda s: t_grass_edge_hd(s, "right"))
tile(18, 61)(t_bg_dark_hd)
tile(19, 19)(t_bridge_hd)
tile(20, 71)(t_hub_grass_hd)
tile(21, 72)(t_hub_path_hd)
tile(22, 73)(t_hub_water_hd)
tile(23, 74)(t_hub_tree_hd)
tile(24, 24)(t_lava_hd)
tile(25, 25)(t_metal_hd)
tile(26, 26)(lambda s: t_switch_off_hd("gold", s, "diamond"))
tile(27, 27)(lambda s: t_switch_off_hd("purple", s, "square"))


#: The H0 look sample's slice, by the 1x id each one replaces
#: (tools/art/hd_look.py reads it through tiles.HD_SLICE).
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
