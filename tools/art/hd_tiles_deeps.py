"""4. TERMITE DEEPS (ids 260-271), drawn natively at 2x.

The world's rule from tiles.py holds at 2x -- "a world must not swallow the
player": the bulk of every solid is dirt/wood 1-2 (luma 21-60), anything
brighter is a lip, a grain or a rim a texel or two wide, and the luminous
accent is violet (`purple`, the one ramp no form uses) and never a fill.

The level is unlit except for pools of light, which multiply the whole frame
down. So the detail here is carried by VALUE STRUCTURE, not hue: every feature
is a dark hollow beside a lit lip (a bored gallery, a comb cell, a pellet, the
overlap of a plate), which survives being darkened where a hue shift would not.

Variants of a fill are laid side by side at random, so anything that crosses a
cell edge is drawn the same in every variant: the mud layers meet the edge at
fixed heights (`_layer`), the comb is one lattice for every seed (`_comb_cell`),
the plates of the chitin wall always break on the cell edge, and the roots and
the climbable pass through fixed points at the top and bottom of the cell.
Seeds only change what lives inside.

Sections: helpers, the solids (260, 261, 263, 271), the background (262, 265,
269), the interactive tiles (266, 267, 268, 270), dressers, accents, the
decoration, and the registrations. 264 is the see-through void: nothing is
registered for it.
"""
import math
import random

from .hd_tilekit import (BIT_E, BIT_N, BIT_S, BIT_W, N, blob, crack, decoration,
                         dresser, ellipse, fill, get, level_of, new, pit, put, put_c, shift,
                         side_xy, tile, wave)
from .hd_tilekit import ACCENTS, CAP_ACCENTS
from .hd_tiles_jungle import pebble


# ============================================================ helpers
def _layer(x, y0, amp):
    """A mud-layer boundary: height `y0` at both cell edges (so every variant
    meets its neighbour there), bowing by `amp` texels in between."""
    return y0 + amp * math.sin(math.pi * x / N)


def _pellets(img, rnd, ramp, lvl, count, box=None, rmin=1.2, rmax=2.2):
    """What a mound is built of: chewed earth rolled into pellets and pressed
    into place. Each is a small lump lit on its upper left with a dark seat
    on its lower right, so a field of them reads as packed, not as noise."""
    x0, y0, x1, y1 = box or (0, 0, N, N)
    for _ in range(count):
        cx, cy = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        r = rnd.uniform(rmin, rmax)
        blob(img, ramp, cx, cy, r, r * rnd.uniform(0.7, 0.95), lvl, lit=1.0, dark=0.9,
             shadow=0.8)


def _gallery(img, rnd, cx, cy, rx, ry, ramp="dirt", lvl=0.3):
    """A bored gallery: hd_tilekit.pit(), plus the gnawed floor the workers
    left -- a short ramp of crumbs on its lit lower lip."""
    pit(img, ramp, cx, cy, rx, ry, lvl)
    for k in range(int(rx)):
        if rnd.random() < 0.5:
            put(img, cx - rx * 0.4 + k, cy + ry + 1, ramp, lvl + 2.4)


def _fibres(img, rnd, count, box=None, lvl=2.6):
    """Chewed wood: short pale slivers, each with its shadow under it."""
    x0, y0, x1, y1 = box or (0, 0, N, N)
    for _ in range(count):
        x, y = rnd.randrange(x0, x1), rnd.randrange(y0, y1)
        run = rnd.randrange(2, 5)
        dy = rnd.choice((0, 0, 1))
        for k in range(run):
            put(img, x + k, y + (k * dy) // 2, "wood", lvl + (0.6 if k == 0 else 0))
            put(img, x + k, y + (k * dy) // 2 + 1, "wood", lvl - 1.6)


def _grit(img, rnd, count, lvl=2.6, box=None):
    """Grey grit that would not pack down: a stone grain, lit, on its shadow."""
    x0, y0, x1, y1 = box or (0, 0, N, N)
    for _ in range(count):
        x, y = rnd.randrange(x0, x1), rnd.randrange(y0, y1)
        put(img, x, y, "stone", lvl + 1)
        put(img, x + 1, y, "stone", lvl)
        put(img, x + 1, y + 1, "dirt", 0.6)


def _plate(img, x0, x1, y0, h, rnd, overlap=2, clip=True):
    """One chitin plate of a shingled row, seen edge-on: it spans texels
    x0..x1 and laps `overlap` texels over the next plate to its right. A lit
    arris along the top, a body falling off to a rounded belly `h` deep, a
    growth ridge (a dark line with a lit one under it) across the middle, its
    thin right edge rolled down and amber, and the shadow it casts both under
    its belly and onto the plate it overlaps. Draw a row right to left."""
    p = put_c if clip else put
    end = x1 + overlap
    w = end - x0
    ridge = int(h * 0.5)
    for i in range(w):
        t = (i + 0.5) / w
        d = int(round(h * (0.62 + 0.38 * math.sin(math.pi * min(1.0, t * 1.1)))))
        roll = t > 1.0 - 2.5 / w                             # the rolled right edge
        for k in range(d):
            if k == 0:
                lvl = 4.4 - t * 0.9
            elif k == 1:
                lvl = 3.6 - t * 0.6
            elif k == d - 1:
                lvl = 1.2
            else:
                lvl = 3.0 - (k / float(d)) * 1.2 - t * 0.4
                if k == ridge:
                    lvl = 1.6
                elif k == ridge + 1:
                    lvl += 0.6
            if roll:
                lvl -= 1.0
            p(img, x0 + i, y0 + k, "wood", lvl)
        p(img, x0 + i, y0 + d, "dirt", 0)                    # the shadow under the belly
        if rnd.random() < 0.6:
            p(img, x0 + i, y0 + d + 1, "dirt", 0.8)
    p(img, end - 2, y0, "gold", 3.6)                         # amber where it is thin
    p(img, end - 1, y0, "gold", 2.6)
    p(img, end - 2, y0 + 1, "gold", 2.2)
    for k in range(int(h)):                                  # its shadow on the next plate
        p(img, end, y0 + k, "wood", 1.0)


# ============================================================ solids
def t_deep_earth_hd(seed):
    """Packed spoil. Termites build out of what they chew, so this is earth
    with the grain of having been placed: laid in mud layers a few world
    units thick, each a step apart and each pressed out of pellets, with the
    grey grit and the chewed wood that would not pack down caught in it, and
    now and then a gallery bored through."""
    rnd = random.Random(seed)
    img = fill(new(255), "dirt", 2.3, rnd, grain=0.3)
    # three layers, meeting the cell edges at 9 and 21 and 31
    amps = [rnd.uniform(-2.5, 2.5) for _ in range(3)]
    for x in range(N):
        b0, b1, b2 = _layer(x, 9, amps[0]), _layer(x, 21, amps[1]), _layer(x, 31, amps[2])
        for y in range(N):
            # whole steps (shift() rounds): the middle layer a step lighter,
            # so the layer crossing the cell's own top and bottom is one layer
            d = 1 if b0 <= y < b1 else 0
            if d:
                shift(img, x, y, d)
        for i, b in enumerate((b0, b1)):                     # the layer's bed, in runs: a dark
            if wave(x, seed + i * 17, period=N) < -0.15:     # seam, the next layer's lit top
                continue
            y = int(round(b))
            put(img, x, y - 1, "dirt", 1.0)
            put(img, x, y, "dirt", 2.4)
    _pellets(img, rnd, "dirt", 2.0, 22)
    for _ in range(3):                                       # grit stones, bedded
        blob(img, "stone", rnd.uniform(0, N), rnd.uniform(0, N), rnd.uniform(1.4, 2.4),
             rnd.uniform(1.1, 1.8), 1.6, lit=1.2, dark=0.8, shadow=1.0)
    _grit(img, rnd, 6, 1.6)
    _fibres(img, rnd, 4, lvl=2.6)
    if rnd.random() < 0.67:
        _gallery(img, rnd, rnd.uniform(8, 24), rnd.uniform(12, 20), rnd.uniform(2.6, 3.6),
                 rnd.uniform(1.8, 2.4))
    crack(img, "dirt", rnd.randrange(N), rnd.randrange(4, 24), 8, 1.8, rnd)
    return img


def t_deep_crust_hd(seed):
    """The ledge you stand on: packed spoil capped with a chitin crust, the
    plates overlapping the way a carapace does -- each lapping the next from
    the left, lit on its upper face, ridged, with an amber lip where it thins
    and a shadow under its lap. The crust is wood 1-4 with one amber texel a
    plate, which keeps it under luma 90."""
    rnd = random.Random(seed)
    img = t_deep_earth_hd(seed + 100)
    x = 0
    plates = []
    while x < N:
        w = rnd.randrange(7, 12)
        if N - (x + w) < 6:
            w = N - x
        plates.append((x, x + w, rnd.uniform(5.6, 7.4)))
        x += w
    for (x0, x1, h) in reversed(plates):                     # right first: each laps the next
        _plate(img, x0, x1, 0, h, rnd, overlap=2 if x1 < N else 0)
    for _ in range(3):                                       # crumbs off the edge
        px = rnd.randrange(N)
        for k in range(rnd.randrange(1, 4)):
            put_c(img, px, 9 + k, "wood", 1.4 - k * 0.3)
    return img


def _lumps(seed, n=3, jit=3.2, salt=2630):
    """The lumps of a mound wall: a jittered lattice of points, `pitch` texels
    apart, wrapped on the cell. The points within a pitch of the cell edge
    are hashed from their place alone, so every variant meets its neighbour
    on the same lumps; only the inner ones move with the seed."""
    fixed = random.Random(salt)
    own = random.Random(seed)
    pitch = N / float(n)
    pts = []
    for j in range(n):
        for i in range(n):
            edge = i in (0, n - 1) or j in (0, n - 1)
            r = fixed if edge else own
            a, b = r.uniform(-jit, jit), r.uniform(-jit, jit)
            if not edge:
                fixed.uniform(0, 1), fixed.uniform(0, 1)
            pts.append((pitch * (i + 0.5) + a, pitch * (j + 0.5) + b))
    return pts


def _voronoi(pts):
    """Per texel: (index of the nearest point, distance to the cell's border
    in texels), on a wrapped cell."""
    out = {}
    for y in range(N):
        for x in range(N):
            best = []
            for k, (px, py) in enumerate(pts):
                dx = (x + 0.5 - px + N / 2) % N - N / 2
                dy = (y + 0.5 - py + N / 2) % N - N / 2
                best.append((dx * dx + dy * dy, k, dx, dy))
            best.sort()
            d1, k1, dx, dy = best[0]
            d2 = best[1][0]
            out[(x, y)] = (k1, (math.sqrt(d2) - math.sqrt(d1)) * 0.5, dx, dy)
    return out


def t_deep_chitin_hd(seed):
    """The mound's wall: the fill under every cap, laid by the thousand. 1x
    drew it as ribs, which across a wall became ruled stripes.

    At 2x it is what a mound wall is made of, packed lump against lump with
    no courses at all: mud boluses pressed out of pellets, plates of shed
    chitin bedded among them (growth arcs across each, amber where it is
    thin), and now and then a lump bored through into a gallery or worked
    into comb cells. Every lump is lit on its upper left and sits in the dark
    of its own joint, which is what still reads when a pool of light is all
    there is. The lumps on the cell edge are shared with the neighbour, so
    their shape and material are fixed; what a seed changes is everything
    worked into them away from the edge."""
    rnd = random.Random(seed)
    pts = _lumps(seed)
    vor = _voronoi(pts)
    kinds, lvl_of, focus = [], [], []
    for k, (px, py) in enumerate(pts):
        edge = not (8 < px < N - 8 and 8 < py < N - 8)
        r = random.Random(2631 + k) if edge else rnd
        kinds.append("plate" if r.random() < 0.4 else "mud")
        lvl_of.append(1.9 + r.uniform(-0.35, 0.35))
        focus.append((px + r.uniform(-6, -3), py + r.uniform(-7, -4)))
    img = new(255)
    for (x, y), (k, edge, dx, dy) in vor.items():
        plate = kinds[k] == "plate"
        f = (dx + dy) / 8.0                              # + toward the lower right
        lvl = lvl_of[k] - f * 0.6
        if edge < 0.6:
            lvl = 0.0                                    # the joint
        elif edge < 1.6:
            lvl += 1.4 if f < -0.2 else (-1.0 if f > 0.3 else 0.3)
        elif edge < 2.6 and f < -0.3:
            lvl += 0.6
        elif plate:
            # growth arcs round a point off the plate's upper left, as on a
            # scale: every fourth ring a step down, the ring above it lit
            fx, fy = focus[k]
            ring = math.hypot(x + 0.5 - fx, (y + 0.5 - fy) * 1.3) % 4.0
            if ring < 1.0:
                lvl -= 0.9
            elif ring < 2.0:
                lvl += 0.5
        put(img, x, y, "wood" if plate else "dirt", lvl)

    def inner(x, y, m=3):
        return m <= x < N - m and m <= y < N - m

    for k, (px, py) in enumerate(pts):                   # worked into the lumps, per seed
        r = random.Random(seed * 31 + k)
        if kinds[k] == "plate":
            if r.random() < 0.6:                         # amber where it is thin
                ax, ay = px + r.uniform(1, 3), py + r.uniform(0, 3)
                if inner(ax, ay):
                    put(img, ax, ay, "gold", 2.6)
                    put(img, ax + 1, ay, "gold", 1.8)
                    put(img, ax, ay - 1, "gold", 3.4)
            continue
        for _ in range(r.randrange(2, 5)):               # its pellets
            cx, cy = px + r.uniform(-3, 3), py + r.uniform(-3, 3)
            if inner(cx, cy, 4):
                blob(img, "dirt", cx, cy, r.uniform(1.0, 1.6), r.uniform(0.8, 1.2),
                     lvl_of[k] + 0.2, lit=1.0, dark=0.9)
        if r.random() < 0.3 and inner(px, py, 6):        # comb worked into it
            for (ox, oy) in ((-1.8, -1.0), (1.6, 1.4), (2.2, -2.0)):
                pit(img, "dirt", px + ox, py + oy, 1.3, 1.1, 0.1)
    for _ in range(rnd.choice((0, 1, 1))):               # a gallery bored through
        _gallery(img, rnd, rnd.uniform(11, 21), rnd.uniform(10, 22), rnd.uniform(2.4, 3.2),
                 rnd.uniform(1.7, 2.2), lvl=0.1)
    crack(img, "dirt", rnd.randrange(6, 22), rnd.randrange(6, 20), 7, 1.6, rnd, wrap=False)
    _grit(img, rnd, 3, 1.2, box=(3, 3, N - 4, N - 4))
    return img


def t_deep_packed_hd(seed):
    """The secondary solid: earth rammed into blocks, the way the mound's
    structural walls are built. Squarer and darker than the spoil, so a level
    can say "architecture, not dirt": long blocks in two courses a cell, half
    offset, each with a lit top and left arris and a dark joint, the lifts it
    was rammed in showing as faint broken lines, a round putlog hole where the
    formwork was tied, and its pellets."""
    rnd = random.Random(seed)
    img = fill(new(255), "dirt", 1.2, rnd, grain=0.22)
    _pellets(img, rnd, "dirt", 0.9, 14, rmin=1.0, rmax=1.8)
    for c, by in enumerate((0, 16)):
        ox = 0 if c == 0 else 16
        s0 = rnd.randrange(1 << 20)
        for ly in (5, 10):                                    # the lifts, broken
            for lx in range(2, 31):
                if wave(lx, s0 + ly, period=N) > -0.2:
                    shift(img, ox + lx, by + ly, -1, wrap=True)
        for lx in range(N):
            put(img, ox + lx, by, "dirt", 0.2)                # the bed joint
            put(img, ox + lx, by + 1, "dirt", 2.8 if lx < 26 else 2.2)
            put(img, ox + lx, by + 2, "dirt", 2.0 if lx < 20 else 1.6)
            put(img, ox + lx, by + 15, "dirt", 0.6)
        for ly in range(16):                                  # the head joint
            put(img, ox, by + ly, "dirt", 0.2)
            if ly > 1:
                put(img, ox + 1, by + ly, "dirt", 2.4 if ly < 12 else 2.0)
            put(img, ox + 31, by + ly, "dirt", 0.7)
        if rnd.random() < 0.7:                                # the putlog hole
            hx, hy = ox + rnd.randrange(8, 24), by + rnd.randrange(6, 10)
            pit(img, "dirt", hx, hy, 1.6, 1.4, 0.0)
        for _ in range(2):                                    # a knock on the arris
            x = ox + rnd.randrange(4, 28)
            put(img, x, by + 1, "dirt", 0.8)
            put(img, x + 1, by + 1, "dirt", 1.0)
            put(img, x, by + 2, "dirt", 2.8)
    for _ in range(2):                                        # chewed wood in the mix
        blob(img, "wood", rnd.uniform(0, N), rnd.uniform(0, N), rnd.uniform(1.0, 1.8),
             rnd.uniform(0.8, 1.2), 1.6, lit=1.0, dark=0.8)
    _grit(img, rnd, 3, 1.2)
    return img


# ============================================================ background
#: The comb lattice, the same for every seed: (cx, cy, rx, ry) per cell.
def _comb_cells():
    r = random.Random(2620)
    out = []
    for j in range(4):
        for i in range(4):
            cx = 4 + 8 * i + (4 if j % 2 else 0) + r.uniform(-0.8, 0.8)
            cy = 4 + 8 * j + r.uniform(-0.6, 0.6)
            out.append((cx, cy, r.uniform(2.6, 3.3), r.uniform(2.1, 2.7)))
    return out


_COMB = _comb_cells()


def _comb_cell(img, cx, cy, rx, ry, kind, rnd):
    """One cell of the comb: a rounded opening in the septum. Its upper-left
    lip catches the light, its inner wall under that lip is in shadow, and
    its floor on the lower right is lit again: a hollow, not a ring.
    `kind`: "open", "deep" (bored on through, black), "sealed" (capped with
    mud, a dome instead of a hole), "lit" (something living in it glows)."""
    for y in range(int(cy - ry - 2), int(cy + ry + 3)):
        for x in range(int(cx - rx - 2), int(cx + rx + 3)):
            nx, ny = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
            d = nx * nx + ny * ny
            f = nx + ny
            if d <= 1.0:
                if kind == "sealed":
                    v = 1.1 + (0.8 if f < -0.4 else (-0.6 if f > 0.5 else 0.0))
                    put(img, x, y, "dirt", v)
                elif kind == "deep":
                    put(img, x, y, "dirt", 0 if d < 0.7 or f < 0.5 else 0.6)
                else:
                    v = 0.0 if f < 0.2 else (0.9 if f < 0.9 else 1.4)
                    put(img, x, y, "dirt", v)
            elif d <= 1.7:
                if f < -0.5:
                    put(img, x, y, "wood", 2.0 if d < 1.35 else 1.4)   # lit lip
                elif f > 0.6:
                    put(img, x, y, "dirt", 0.3)                        # lip's shadow
                else:
                    put(img, x, y, "wood", 1.0)                        # the septum
    if kind == "lit":
        ellipse(img, "purple", cx + 0.3, cy + 0.4, rx * 0.55, ry * 0.5, 2.2)
        put(img, cx - 0.5, cy - 0.3, "purple", 3.6)
        put(img, cx + 0.5, cy - 0.3, "purple", 2.8)
        put(img, cx - 0.5, cy + 0.7, "purple", 2.8)


def t_deep_comb_hd(seed):
    """Background comb, the termites' own masonry, held dark: one lattice of
    rounded cells (the same in every variant, so a wall of them is one comb),
    each a hollow with a lit lip and a lit floor. The seed only decides which
    cells are bored on through, which are capped with mud, and which still
    have something glowing in them."""
    rnd = random.Random(seed)
    img = fill(new(255), "dirt", 0.4, rnd, grain=0.22)
    for (cx, cy, rx, ry) in _COMB:
        inner = 5 <= cx <= N - 5 and 5 <= cy <= N - 5
        roll = rnd.random()
        kind = "open"
        if inner:
            kind = "deep" if roll < 0.18 else ("sealed" if roll < 0.32 else
                                               ("lit" if roll < 0.40 else "open"))
        _comb_cell(img, cx, cy, rx, ry, kind, rnd)
    for _ in range(6):                                       # grit on the septa
        x, y = rnd.randrange(N), rnd.randrange(N)
        if level_of(get(img, x, y)) and level_of(get(img, x, y))[0] == "wood":
            put(img, x, y, "wood", 1.6)
    return img


def t_deep_root_hd(seed):
    """A great root coming down through the nest, as background: a trunk that
    wanders and swells, its bark in long furrows (dark grooves with a lit
    ridge beside each), lit on the left shoulder, its own cast shadow on the
    right, and rootlets off the side. It passes the top and the bottom of the
    cell at the same place in every variant, so a column of them is one root."""
    rnd = random.Random(seed)
    img = fill(new(255), "dirt", 0.5, rnd, grain=0.2)
    sway = rnd.uniform(-3.0, 3.0)
    swell = rnd.uniform(-1.6, 1.6)
    furrows = [rnd.uniform(0.18, 0.32), rnd.uniform(0.42, 0.58), rnd.uniform(0.66, 0.8)]
    edges = []
    for y in range(N):
        s = math.sin(math.pi * y / N)
        cx = 16 + sway * s
        half = 8.0 + swell * s + 0.6 * math.sin(2 * math.pi * y / N * 2)
        lo, hi = int(round(cx - half)), int(round(cx + half))
        edges.append((lo, hi))
        for x in range(lo, hi + 1):
            t = (x - lo) / float(max(1, hi - lo))
            lvl = 2.0
            if t < 0.12:
                lvl = 3.2
            elif t < 0.22:
                lvl = 2.6
            elif t > 0.88:
                lvl = 0.8
            elif t > 0.74:
                lvl = 1.4
            for f in furrows:
                if abs(t - (f + 0.03 * math.sin(y / 3.0 + f * 9))) < 0.035:
                    lvl -= 1.4
                elif abs(t - (f + 0.03 * math.sin(y / 3.0 + f * 9)) + 0.07) < 0.035:
                    lvl += 0.6
            put(img, x, y, "wood", lvl + rnd.uniform(-0.2, 0.2))
        put(img, hi + 1, y, "dirt", 0)                       # its cast shadow
        put(img, hi + 2, y, "dirt", 0)
        put(img, hi + 3, y, "dirt", 0.3)
        put(img, lo - 1, y, "dirt", 1.0)
    for _ in range(2):                                       # rootlets off the side
        y = rnd.randrange(4, N - 8)
        side = rnd.choice((-1, 1))
        lo, hi = edges[y]
        x = lo - 1 if side < 0 else hi + 1
        for k in range(rnd.randrange(4, 8)):
            put(img, x + side * k, y + k // 2, "wood", 2.0)
            put(img, x + side * k, y + k // 2 + 1, "wood", 0.8)
    for _ in range(3):                                       # bark scales, lit edge up
        y = rnd.randrange(N)
        lo, hi = edges[y]
        x = rnd.randrange(lo + 3, max(lo + 4, hi - 4))
        for k in range(3):
            put(img, x + k, y, "wood", 2.8)
            put(img, x + k, y + 1, "wood", 1.0)
    return img


def t_deep_fungus_hd(seed):
    """Background fungus, the luminous accent as a mat rather than a lamp:
    shelf caps stepped up the wall, each with a lit crown, a dark gill line
    under the brim and a glow spilling onto the earth below it, threads of
    mycelium between them. Bright for this world, still under luma 130, and
    violet, which no form is."""
    rnd = random.Random(seed)
    img = fill(new(255), "dirt", 0.5, rnd, grain=0.2)
    for _ in range(10):                                      # mycelium, under everything
        x, y = rnd.randrange(N), rnd.randrange(N)
        dx = rnd.choice((-1, 1))
        for k in range(rnd.randrange(5, 11)):
            put(img, x, y, "purple", 1.6)
            x += dx
            if rnd.random() < 0.4:
                y += rnd.choice((-1, 1))
    caps = []
    for _ in range(6):
        caps.append((rnd.uniform(0, N), rnd.uniform(0, N), rnd.uniform(3.0, 5.2),
                     rnd.uniform(1.6, 2.4)))
    caps.sort(key=lambda c: c[1])
    for (cx, cy, rx, ry) in caps:
        ellipse(img, "purple", cx + 0.5, cy + ry + 1.5, rx * 0.9, 1.6, 1.0)   # its glow below
        for y in range(int(cy - ry - 1), int(cy + 2)):       # the cap: upper half-ellipse
            for x in range(int(cx - rx - 1), int(cx + rx + 2)):
                nx, ny = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
                d = nx * nx + ny * ny
                if d > 1.0 or ny > 0.25:
                    continue
                v = 2.4 + (1.0 - d) * 0.8
                if -nx - ny > 0.7:
                    v += 1.6
                elif nx > 0.55:
                    v -= 0.9
                put(img, x, y, "purple", v)
        for x in range(int(cx - rx + 1), int(cx + rx)):      # the gills under the brim
            put(img, x, cy + 1, "purple", 1.0)
            if (x + int(cy)) % 2 == 0:
                put(img, x, cy + 2, "purple", 1.8)
        put(img, cx - rx * 0.4, cy - ry * 0.6, "purple", 5)  # its crown
    for _ in range(8):                                       # spores hanging in the glow
        put(img, rnd.randrange(N), rnd.randrange(N), "purple", rnd.choice((3, 4)))
    return img


# ============================================================ interactive (inked)
def t_deep_shelf_hd(seed):
    """One-way shelf: a row of chitin plates, cantilevered, each lapping the
    next with an amber lip where it thins, a hard shadow under its lap and
    nothing holding it from below but a few hair-roots. Inked by the kit."""
    rnd = random.Random(seed)
    img = new(0)
    x = 0
    bounds = []
    while x < N:
        w = rnd.randrange(9, 13)
        if N - (x + w) < 7:
            w = N - x
        bounds.append((x, x + w))
        x += w
    for (x0, x1) in reversed(bounds):
        top = 0
        for i in range(x1 - x0 + (2 if x1 < N else 0)):
            px = x0 + i
            if px >= N:
                break
            t = (i + 0.5) / (x1 - x0)
            for k, lvl in enumerate((4.2, 3.4, 2.8, 2.4, 1.8)):
                put_c(img, px, top + k, "wood", lvl - t * 0.8 + (rnd.uniform(-0.2, 0.2) if k > 1 else 0))
            put_c(img, px, top + 5, "wood", 0.9)
        put_c(img, x1 - 1, 0, "gold", 3.6)
        put_c(img, x1 - 2, 0, "gold", 2.8)
        if x1 < N:
            for k in range(1, 5):                            # the lap's shadow
                put_c(img, x1 + 2, k, "wood", 1.2)
    for _ in range(2):                                       # a growth ridge
        x = rnd.randrange(2, N - 8)
        for k in range(rnd.randrange(4, 8)):
            put_c(img, x + k, 2, "wood", 2.0)
    for _ in range(rnd.randrange(2, 4)):                     # hair-roots under it
        x = rnd.randrange(2, N - 2)
        for k in range(rnd.randrange(2, 5)):
            put_c(img, x, 6 + k, "wood", 2.0 - k * 0.3)
    return img


def t_deep_spore_hd(seed):
    """The hazard: spore vents. A low chimney of chewed earth per vent, its
    mouth lit violet from inside, and spores rising out of it in a widening
    plume, brightest nearest the mouth. Violet, like everything luminous down
    here: the one warm thing on screen is never the thing that hurts you."""
    rnd = random.Random(seed)
    img = new(0)
    for x in range(N):                                       # the bed it grows from
        put_c(img, x, 26, "wood", 2.4 + rnd.uniform(-0.3, 0.3))
        put_c(img, x, 27, "wood", 1.8)
        put_c(img, x, 28, "dirt", 1.4)
        put_c(img, x, 29, "dirt", 0.8)
    for cx in (5.5, 16.0, 26.5):
        cx += rnd.uniform(-0.8, 0.8)
        hgt = rnd.uniform(6.0, 8.0)
        for y in range(int(26 - hgt), 27):                   # the chimney, tapering,
            u = (26 - y) / hgt                               # built of pellets
            half = 4.4 - u * 2.0 + (0.6 if (y % 3 == 0) else 0)
            for x in range(int(round(cx - half)), int(round(cx + half)) + 1):
                t = (x + 0.5 - (cx - half)) / (2 * half)
                lvl = 2.0 + (1.4 if t < 0.28 else (-0.9 if t > 0.75 else 0))
                if y % 3 == 2:
                    lvl -= 0.7
                put_c(img, x, y, "wood", lvl)
        my = int(26 - hgt)
        for dx in (-2, -1, 0, 1, 2):                         # the mouth, lit from inside
            put_c(img, cx + dx, my, "purple", 4.6 - abs(dx) * 0.9)
            put_c(img, cx + dx, my + 1, "purple", 3.0 - abs(dx) * 0.6)
        put_c(img, cx - 2, my - 1, "wood", 3.4)
        # the plume: puffs rising off the mouth, each a lit ball of spores
        # with its dark side down-right, widening and cooling as they go, and
        # one or two loose spores beside it
        y, x = my - 3.0, cx
        for k in range(3):
            r = 1.8 - k * 0.3
            if y - r < 0:
                break
            blob(img, "purple", x, y, r, r * 0.85, 4.4 - k * 0.6, lit=1.0, dark=1.2,
                 wrap=False)
            if rnd.random() < 0.6:
                put_c(img, x + rnd.choice((-1, 1)) * (r + 2), y + rnd.uniform(-1, 1),
                      "purple", 4.0 - k * 0.4)
            y -= r * 2 + rnd.uniform(2.6, 4.0)
            x += rnd.uniform(-2.0, 2.0)
    return img


def _ladder_x(y, a, b):
    return 13 + a * math.sin(2 * math.pi * y / N) + b * math.sin(4 * math.pi * y / N)


def t_deep_ladder_hd(seed):
    """The climbable: a hanging root, two strands twisted round each other
    (a lit one in front, a darker one crossing behind), rootlets off it in
    turn, and an amber knot every half tile where a hand closes. Passes the
    top and bottom of the cell at the same x in every variant."""
    rnd = random.Random(seed)
    img = new(0)
    a, b = rnd.uniform(-1.6, 1.6), rnd.uniform(-0.8, 0.8)
    for y in range(N):
        x = int(round(_ladder_x(y, a, b)))
        tw = math.sin(2 * math.pi * y / 12.0)
        for k, lvl in enumerate((4.2, 3.4, 2.8, 2.2, 1.6, 1.0)):
            put_c(img, x + k, y, "wood", lvl)
        bx = x + 2 + int(round(tw * 2.0))                    # the strand crossing behind
        if tw < 0:
            put_c(img, bx, y, "wood", 1.0)
            put_c(img, bx + 1, y, "wood", 0.4)
        else:
            put_c(img, bx, y, "wood", 4.6)
            put_c(img, bx + 1, y, "wood", 3.6)
    for i, y in enumerate(range(3, N, 7)):                   # rootlets, in turn
        x = _ladder_x(y, a, b)
        side = -1 if i % 2 == 0 else 1
        px = int(round(x)) + (-1 if side < 0 else 6)
        for k in range(rnd.randrange(3, 6)):
            put_c(img, px + side * k, y + k // 2, "wood", 3.6 - k * 0.4)
            put_c(img, px + side * k, y + k // 2 + 1, "wood", 1.2)
    for y in (7, 23):                                        # the grip knots, in amber
        x = int(round(_ladder_x(y, a, b)))
        for dx, dy, lvl in ((1, 0, 4.2), (2, 0, 3.6), (3, 0, 3.0), (1, 1, 3.2), (2, 1, 2.8),
                            (3, 1, 2.2), (2, -1, 3.0)):
            put_c(img, x + dx, y + dy, "gold", lvl)
    return img


def t_deep_glowwall_hd(seed):
    """Breakable, and the world's verb: the luminous wall the Brood Queen
    fight is about. A block of mound earth with the light already breaking
    through it: a star of fractures lit violet from inside (bright at the
    heart, cooling along each arm, a dark lip on one side so it reads as a
    split and not a painted line), glowing pellets in the cracks, and the
    block's own bevel round it."""
    rnd = random.Random(seed)
    img = fill(new(255), "dirt", 1.0, rnd, grain=0.22)
    _pellets(img, rnd, "dirt", 0.9, 12, rmin=1.2, rmax=2.0)
    for _ in range(4):
        blob(img, "wood", rnd.uniform(0, N), rnd.uniform(0, N), rnd.uniform(2.0, 3.6),
             rnd.uniform(1.6, 2.6), 1.2, lit=1.0, dark=0.6)
    for i in range(N):                                       # the block's bevel
        put_c(img, i, 0, "dirt", 2.6)
        put_c(img, i, 1, "dirt", 2.0)
        put_c(img, 0, i, "dirt", 2.4)
        put_c(img, N - 1, i, "dirt", 0.2)
        put_c(img, i, N - 1, "dirt", 0.1)
        put_c(img, N - 2, i, "dirt", 0.6)
        put_c(img, i, N - 2, "dirt", 0.6)
    cx, cy = 15 + rnd.randrange(-2, 3), 15 + rnd.randrange(-2, 3)
    for ang in range(0, 360, 60):                            # the fracture, lit from inside
        a = math.radians(ang + rnd.randrange(-16, 17))
        x, y = float(cx), float(cy)
        ln = rnd.randrange(11, 16)
        for k in range(ln):
            x += math.cos(a)
            y += math.sin(a)
            a += rnd.uniform(-0.18, 0.18)
            lvl = 5.4 - k * 0.28
            put_c(img, round(x), round(y), "purple", lvl)
            if k < ln * 0.6:
                put_c(img, round(x + 1), round(y), "purple", lvl - 1.6)
            put_c(img, round(x), round(y) - 1, "dirt", 0)      # the split's dark lip
            put_c(img, round(x), round(y) + 1, "purple", 1.4)  # glow spilling under it
            if k == ln // 2 and rnd.random() < 0.7:            # a branch
                bx, by = x, y
                b = a + rnd.choice((-0.9, 0.9))
                for j in range(rnd.randrange(3, 6)):
                    bx += math.cos(b)
                    by += math.sin(b)
                    put_c(img, round(bx), round(by), "purple", 3.4 - j * 0.3)
                    put_c(img, round(bx), round(by) - 1, "dirt", 0.2)
    blob(img, "purple", cx, cy, 3.0, 2.6, 4.4, lit=1.2, dark=0.6, wrap=False)
    put_c(img, cx - 1, cy - 1, "purple", 6)
    return img


# ============================================================ dressers
@dresser("dress_deeps")
def dress_deeps_hd(img, mask, rnd):
    """Chewed earth: a face the termites have worked is scalloped -- rounded
    bites out of it, dark inside, the far side of each catching the light --
    the odd gallery opens in a side face, an amber fleck of chitin shows in
    the crust where a plate was pulled out, and the underside hangs with
    hair-roots and crumbs."""
    for side, bit in (("top", BIT_N), ("bottom", BIT_S), ("left", BIT_W), ("right", BIT_E)):
        if mask & bit:
            continue
        for _ in range(2):
            i = rnd.randrange(3, N - 9)
            w = rnd.randrange(4, 8)
            dmax = rnd.randrange(2, 4)
            for j in range(w):
                d = max(1, int(round(dmax * math.sin(math.pi * (j + 0.5) / w))))
                for k in range(d):
                    x, y = side_xy(side, k, i + j)
                    put_c(img, x, y, "dirt", 0.6 if k < d - 1 else 1.0)
                x, y = side_xy(side, d, i + j)
                put_c(img, x, y, "dirt", 3.0 if side in ("top", "left") else 1.6)
    for side, bit in (("left", BIT_W), ("right", BIT_E)):
        if mask & bit or rnd.random() < 0.5:
            continue
        y = rnd.uniform(9, 24)
        x = 4.0 if side == "left" else N - 5.0
        pit(img, "dirt", x, y, 2.0, 1.8, 0.2)
    if not mask & BIT_N:
        for _ in range(3):
            x, y = rnd.randrange(2, N - 3), rnd.randrange(2, 5)
            put_c(img, x, y, "gold", 3)
            put_c(img, x + 1, y, "gold", 2)
            put_c(img, x, y + 1, "dirt", 0.6)
    if not mask & BIT_S:
        for x in range(N):
            if rnd.random() < 0.22:
                put_c(img, x, N - 1, "wood", 1.4)
        for _ in range(3):
            x = rnd.randrange(2, N - 2)
            for k in range(rnd.randrange(2, 6)):
                put_c(img, x, N - 1 - k, "wood", 1.6 + k * 0.25)


@dresser("dress_deeps_crust")
def dress_deeps_crust_hd(img, mask, rnd):
    """The capped tile: as above, and the carapace wraps whichever shoulder is
    exposed, plate under plate down the side, each lapping the one below."""
    dress_deeps_hd(img, mask, rnd)
    for side, bit in (("left", BIT_W), ("right", BIT_E)):
        if mask & bit:
            continue
        y = 0
        depth = rnd.randrange(8, 14)
        while y < depth:
            h = rnd.randrange(3, 5)
            for j in range(h):
                w = 4 - (j * 3) // h
                for k in range(w):
                    x, py = side_xy(side, k, y + j)
                    lvl = (3.4 if side == "left" else 2.4) - j * 0.5 - k * 0.3
                    put_c(img, x, py, "wood", lvl)
                x, py = side_xy(side, w, y + j)
                put_c(img, x, py, "wood", 0.6)
            gx, gy = side_xy(side, 0, y)
            put_c(img, gx, gy, "gold", 3.4)
            y += h


@dresser("dress_deeps_bg")
def dress_deeps_bg_hd(img, mask, rnd):
    """The comb's exposed lip: short runs of it catch the light, held at the
    septum's own step so it stays background."""
    if not mask & BIT_N:
        x = 0
        while x < N:
            if rnd.random() < 0.3:
                for k in range(rnd.randrange(2, 6)):
                    put_c(img, x + k, 0, "wood", 2.0)
                    put_c(img, x + k, 1, "wood", 1.2)
                x += 6
            else:
                x += 1


# ============================================================ accents
def root_nub(img, rnd, y0=0):
    """A root breaking the surface: a lit hump with bark lines and a cut end,
    sitting in its own shadow."""
    x = rnd.randrange(5, N - 16)
    w = rnd.randrange(9, 13)
    for k in range(w):
        t = (k + 0.5) / w
        top = y0 + int(round(2.4 * (1 - math.sin(math.pi * t))))
        for j in range(top, y0 + 5):
            lvl = 4.6 if j == top else (3.4 if j == top + 1 else 2.4)
            put_c(img, x + k, j, "wood", lvl - t * 0.8)
        put_c(img, x + k, y0 + 5, "wood", 0.4)
        if k % 3 == 1:
            put_c(img, x + k, top + 2, "wood", 1.6)
    put_c(img, x + w, y0 + 3, "wood", 3.6)                  # the cut end: a ring
    put_c(img, x + w, y0 + 4, "wood", 1.4)
    put_c(img, x + w + 1, y0 + 4, "wood", 0.4)


ACCENTS["deeps"] = [root_nub, lambda i, r: pebble(i, r, "dirt", 3)]
CAP_ACCENTS[261] = [lambda i, r: root_nub(i, r, y0=3),
                    lambda i, r: pebble(i, r, "dirt", 3, y0=4)]


# ============================================================ decoration
@decoration("d_glow_spots")
def d_glow_spots_hd(img, rnd):
    """A few fungal caps, violet, small: a stalk, a cap lit on its crown with
    a gill shadow under the brim, and a faint glow on whatever is under it.
    The luminous accent is allowed here because a background cell is behind
    the player rather than around them."""
    for _ in range(rnd.randrange(2, 5)):
        cx, cy = rnd.uniform(4, N - 5), rnd.uniform(5, N - 4)
        rx = rnd.uniform(2.0, 3.4)
        for k in range(1, 4):                                # the stalk
            put_c(img, cx, cy + k, "purple", 2.0)
        ellipse(img, "purple", cx, cy + 4, rx * 0.8, 1.0, 1.2, wrap=False)
        for x in range(int(cx - rx), int(cx + rx) + 1):      # the cap
            t = (x + 0.5 - cx) / rx
            h = int(round(2.2 * math.sqrt(max(0.0, 1 - t * t))))
            for y in range(int(cy) - h, int(cy) + 1):
                put_c(img, x, y, "purple", 3.4 - t * 1.0 + (0.8 if y == int(cy) - h else 0))
            put_c(img, x, int(cy) + 1, "purple", 1.2)
        put_c(img, cx - rx * 0.4, cy - 2, "purple", 5)
    return img


# ============================================================ registrations
# id, the seed its T_AT() line in tiles.py uses, painter. 264 (the void) is
# see-through and stays unregistered.
tile(260, 2601)(t_deep_earth_hd)
tile(261, 2611)(t_deep_crust_hd)
tile(262, 2621)(t_deep_comb_hd)
tile(263, 2631)(t_deep_chitin_hd)
tile(265, 2651)(t_deep_root_hd)
tile(266, 2661)(t_deep_shelf_hd)
tile(267, 2671)(t_deep_spore_hd)
tile(268, 2681)(t_deep_ladder_hd)
tile(269, 2691)(t_deep_fungus_hd)
tile(270, 2701)(t_deep_glowwall_hd)
tile(271, 2711)(t_deep_packed_hd)
