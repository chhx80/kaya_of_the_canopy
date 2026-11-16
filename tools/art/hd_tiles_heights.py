"""3. THERMAL HEIGHTS (ids 240-251), drawn natively at 2x.

The world's rule from tiles.py still holds at 2x -- "a world must not swallow
the player": the rock bulk sits on dirt 2-4 / stone 2-3 (luma 58-100), the
background cliff and the basalt stacks are held at the dark end, and the only
bright things are a texel or two wide: the bleached crest, a lip, a glint.

What 1x could not hold and 2x spends its texels on:

  * the rock is a cliff of STRATA -- beds of different stone, each with a lit
    ledge on top, an undercut shadow under it, its own grain (laminated,
    massive or pebbly) and vertical joints that stop at the bed;
  * scree is a heap of angular FRAGMENTS, each lit facet by facet from the
    upper left and casting its own shadow, instead of a speckle;
  * basalt shows its columns as prisms (a lit face and a shaded face);
  * the chain is real links, alternately face-on and edge-on.

Strata and columns must line up across a cell edge whatever variant sits on
the other side, so their positions AT THE EDGES are fixed per tile and only
wander inside the cell (`_bed_tops`: a seeded wave under a sin(pi x / N)
envelope, zero at both edges). Everything else is seeded and wrapped.
"""
import math
import random

from .hd_tilekit import (BIT_E, BIT_N, BIT_S, BIT_W, N, WU, blob, clear, crack, decoration,
                         dresser, ellipse, fill, get, ink, level_of, new, pit, put, put_c,
                         shift, side_xy, step, tile, wave)
from .hd_tilekit import ACCENTS, CAP_ACCENTS
from .hd_tiles_jungle import chip, pebble

#: Light comes from the upper left; this is the unit vector TOWARD it.
_LX, _LY = -0.6, -0.8


# ============================================================ helpers
def _envelope(x):
    """0 at both cell edges, 1 in the middle: what lets a feature wander
    inside the cell and still meet any neighbour at the same height."""
    return math.sin(math.pi * x / N)


def _bed_tops(tops, amp, seed):
    """Per bed, its top row at every column: the fixed edge height plus a
    seeded wander inside the cell."""
    out = []
    for k, y0 in enumerate(tops):
        a = amp[k] if isinstance(amp, (list, tuple)) else amp
        out.append([y0 + int(round(a * _envelope(x) * wave(x, seed * 31 + k)))
                    for x in range(N)])
    return out


def _bed_at(tops, x, y):
    """(bed index, rows below its top, rows above its bottom) at (x, y)."""
    t0 = tops[0][x]
    yy = y if y >= t0 else y + N
    if yy >= t0 + N:                                       # the first bed wandered up
        yy -= N
    nb = len(tops)
    for k in range(nb):
        top = tops[k][x]
        bot = tops[k + 1][x] if k + 1 < nb else tops[0][x] + N
        if top <= yy < bot:
            return k, yy - top, bot - 1 - yy
    return nb - 1, 0, 0


def _hull(pts):
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


def shard(img, rnd, cx, cy, rx, ry, ramp, lvl, shadow=1.0, wrap=True, flat=0.45):
    """An angular rock fragment: a convex polygon, shaded as a low pyramid
    whose facets each take the light by their own slope (the facet over an
    edge that faces up-left is lit, down-right in shade), with a flat crown,
    a bright arris on its sunward edges, a dark one on the others, and a
    shadow cast down-right onto whatever it lies on."""
    p = put if wrap else put_c
    n = rnd.randrange(5, 8)
    rot = rnd.uniform(0, 2 * math.pi)
    pts = []
    for i in range(n):
        a = rot + 2 * math.pi * (i + rnd.uniform(-0.3, 0.3)) / n
        r = rnd.uniform(0.7, 1.0)
        pts.append((cx + rx * r * math.cos(a), cy + ry * r * math.sin(a)))
    hull = _hull(pts)
    edges = []
    for i in range(len(hull)):
        ax, ay = hull[i]
        bx, by = hull[(i + 1) % len(hull)]
        ex, ey = bx - ax, by - ay
        ln = math.hypot(ex, ey) or 1.0
        # hull is counter-clockwise in y-down coords -> outward normal:
        nx, ny = ey / ln, -ex / ln
        edges.append((ax, ay, nx, ny))
    inr = min(rx, ry)

    def dists(x, y):
        return [((x - ax) * -nx + (y - ay) * -ny, nx, ny) for ax, ay, nx, ny in edges]

    sx, sy = 1.3, 1.7
    for y in range(int(cy - ry - 3), int(cy + ry + 4)):
        for x in range(int(cx - rx - 3), int(cx + rx + 4)):
            if not wrap and not (0 <= x < N and 0 <= y < N):
                continue
            ds = dists(x + 0.5, y + 0.5)
            d, nx, ny = min(ds)
            if d < 0:
                if shadow and min(dists(x + 0.5 - sx, y + 0.5 - sy))[0] >= 0:
                    shift(img, x, y, -shadow, wrap=wrap)
                continue
            face = nx * _LX + ny * _LY
            if d > inr * flat:
                v = lvl + 0.4                               # the crown
            else:
                v = lvl + face * 1.3
            if d < 1.0:                                     # the arris
                v += 1.0 if face > 0.25 else (-1.2 if face < -0.25 else 0)
            p(img, x, y, ramp, v)
    return hull


def _lichen(img, rnd, x, y, ramp="gold", lvl=2, size=3):
    """A crust of lichen: a ragged rosette on one step, its heart a step up,
    a texel of shadow under its lower rim."""
    cells = {(0, 0)}
    for _ in range(size * 2):
        cx, cy = rnd.choice(sorted(cells))
        cells.add((cx + rnd.choice((-1, 0, 1)), cy + rnd.choice((-1, 0, 0, 1))))
    for (dx, dy) in cells:
        put(img, x + dx, y + dy, ramp, lvl)
    for (dx, dy) in cells:
        if (dx, dy + 1) not in cells:
            shift(img, x + dx, y + dy + 1, -1, wrap=True)
    put(img, x, y, ramp, lvl + 1)


# ============================================================ the rock
def _noise(seed, cells=4):
    """Smooth periodic value noise in [-1, 1] on a `cells` lattice, so a
    mottle wraps with its own cell."""
    r = random.Random(seed)
    g = [[r.uniform(-1, 1) for _ in range(cells)] for _ in range(cells)]
    step_ = N / float(cells)

    def at(x, y):
        fx, fy = x / step_, y / step_
        ix, iy = int(math.floor(fx)), int(math.floor(fy))
        tx, ty = fx - ix, fy - iy
        tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
        a = g[iy % cells][ix % cells]
        b = g[iy % cells][(ix + 1) % cells]
        c = g[(iy + 1) % cells][ix % cells]
        d = g[(iy + 1) % cells][(ix + 1) % cells]
        return (a + (b - a) * tx) * (1 - ty) + (c + (d - c) * tx) * ty
    return at


def _strata(img, rnd, seed, tops, amp, beds, joints, k_lit=1.0, mottle=0.6,
            bleach=0.45):
    """A cliff face of bedded rock, broken into slabs.

    `beds` is per bed (ramp, base step); `joints` per bed (min, max) slab
    width in texels. Each bed is cracked by slightly slanted joints into
    short slabs, and each slab is shaded as a weathered block: a sunlit
    ledge along its top, a lit left edge beside the joint, the right edge
    and the undercut foot in shade, the corners rounded off. Inside, a
    mineral mottle, and patches where the brown bed is bleached grey. Slab
    tone jitter fades to nothing at the cell edges, so any variant meets
    any other on the bed's own base step. `k_lit` scales every light/shade
    delta (a background wall is the same drawing, flattened)."""
    tb = _bed_tops(tops, amp, seed)
    nb = len(tops)
    jl = []
    for k in range(nb):
        js = []
        x = rnd.uniform(0, N)
        lo, hi = joints[k]
        start = x
        while True:
            js.append((int(x) % N, rnd.choice((-1, 0, 0, 1)), rnd.uniform(-0.5, 0.5)))
            x += rnd.uniform(lo, hi)
            if x - start > N - lo * 0.7:
                break
        jl.append(js)
    mot = _noise(seed * 7 + 1, 4)
    fine = _noise(seed * 7 + 2, 8)
    grey = _noise(seed * 7 + 3, 4)
    for y in range(N):
        for x in range(N):
            k, t, u = _bed_at(tb, x, y)
            ramp, base = beds[k][0], beds[k][1]
            lam = len(beds[k]) > 2 and beds[k][2] == "laminated"
            thick = t + u + 1
            best_l, best_r, tone = N, N, 0.0
            for (jx, slant, tn) in jl[k]:
                # the joint leans by one texel over the bed's height
                j = jx + (slant if t > thick // 2 else 0)
                dl = (x - j) % N
                dr = (j - x) % N
                if dl < best_l:
                    best_l, tone = dl, tn
                best_r = min(best_r, dr)
            if best_l == 0:
                put(img, x, y, ramp, base - 2.2 * k_lit)       # the joint
                continue
            v = base + tone * _envelope(x) + mottle * mot(x, y) + 0.35 * fine(x, y)
            if lam and 1 < t and u > 1 and (t + int(round(fine(x, 3) * 1.2))) % 2 == 0:
                v -= 0.6                                        # fine bedding planes
            d = 0.0
            if t == 0:
                d += 1.6
            elif t == 1:
                d += 0.8
            if best_l == 1:
                d += 0.9
            elif best_l == 2:
                d += 0.3
            if best_r == 1:
                d -= 0.9
            if u == 0:
                d = min(d, 0) - 1.9
            elif u == 1:
                d -= 0.7
            # rounded corners: the joint eats the slab's corners
            if (t == 0 or u == 0) and (best_l == 1 or best_r == 1):
                d = -1.6
            v += d * k_lit
            r = ramp
            if ramp == "dirt" and grey(x, y) > 1.0 - bleach and 1 < t and u > 1:
                r = "stone"                                     # bleached grey
            put(img, x, y, r, v)
    return tb


#: Bed tops at the cell edge (texels), their ramps and base steps, and the
#: slab width range of each. Thicknesses 6, 5, 8, 6, 7: uneven.
ROCK_TOPS = (0, 6, 11, 19, 25)
ROCK_BEDS = (("dirt", 3.0), ("stone", 2.9, "laminated"), ("dirt", 3.2), ("stone", 2.6),
             ("dirt", 2.8, "laminated"))
#: Long slabs: a joint every 14-30 texels, not every bed-height or two, which
#: is the rhythm that makes bedded rock read as a brick wall.
ROCK_JOINTS = ((16, 28), (22, 34), (14, 26), (13, 24), (18, 30))


def t_heights_rock_hd(seed, sun=False):
    """Weathered highland rock: a cliff of strata, each bed broken into
    weathered slabs (`_strata`), grey beds and warm ones in turn -- which is
    what "sun-bleached" means here -- with pebbles in the coarse bed, a few
    weathering pits, and lichen on the ledges where the water runs off."""
    rnd = random.Random(seed)
    img = new(255)
    tb = _strata(img, rnd, seed, ROCK_TOPS, (1.8, 2.6, 2.2, 3.2, 2.0), ROCK_BEDS, ROCK_JOINTS)
    for _ in range(3):                                      # pebbles in the coarse bed
        x = rnd.uniform(0, N)
        y = ROCK_TOPS[2] + rnd.uniform(3.5, 5.5)
        blob(img, "stone", x, y, rnd.uniform(1.3, 2.0), rnd.uniform(1.0, 1.4), 2.8,
             lit=1.2, dark=1.0, shadow=1.0)
    for _ in range(3):                                      # weathering pits
        k = rnd.randrange(len(ROCK_TOPS))
        x = rnd.uniform(3, N - 3)
        thick = (ROCK_TOPS + (N,))[k + 1] - ROCK_TOPS[k]
        if thick < 6:
            continue
        pit(img, ROCK_BEDS[k][0], x, ROCK_TOPS[k] + thick / 2.0, rnd.uniform(1.0, 1.5),
            rnd.uniform(0.8, 1.1), ROCK_BEDS[k][1] - 1.0)
    for _ in range(rnd.randrange(2, 4)):                    # lichen on the ledges
        k = rnd.randrange(1, len(ROCK_TOPS))
        x = rnd.randrange(N)
        _lichen(img, rnd, x, tb[k][x] + 2, *rnd.choice((("gold", 2, 3), ("gold", 2, 2),
                                                        ("stone", 4, 2))))
    if sun:
        _sun_crust(img, rnd)
    return img


def _sun_crust(img, rnd):
    """The bleached crust on a capped top. A world unit of it is bright --
    an arris of `metal` 5 and a face of `stone` 5 -- and then it fades over
    another unit and a half, because `metal` 5-6 is the fish's own highlight
    and may be a line, never a face. Crazed, and flaking away in places so
    the rock shows through."""
    s = rnd.randrange(1 << 20)
    for x in range(N):
        d = 5 + int(round(1.2 * wave(x, s))) + (1 if rnd.random() < 0.2 else 0)
        put_c(img, x, 0, "metal", 5)
        put_c(img, x, 1, "stone", 5)
        for y in range(2, d):
            put_c(img, x, y, "stone", 4 if y < 4 else 3)
        put_c(img, x, d, "stone", 1)                       # the crust's own edge
        shift(img, x, d + 1, -1)
    for _ in range(rnd.randrange(3, 6)):                   # crazing
        x = rnd.randrange(N)
        for y in range(2, 2 + rnd.randrange(2, 4)):
            put_c(img, x, y, "stone", 2)
        put_c(img, x + 1, 2, "stone", 5)
    for _ in range(rnd.randrange(2, 4)):                   # flakes gone
        x = rnd.randrange(N - 4)
        w = rnd.randrange(2, 5)
        for k in range(w):
            put_c(img, x + k, 0, "dirt", 3)
            put_c(img, x + k, 1, "dirt", 2)
        put_c(img, x + w, 0, "metal", 4)


def t_heights_wall_hd(seed):
    """Background cliff: the same strata (`_strata`), but far away -- two
    steps down, thicker beds, longer slabs, every light and shade flattened
    to half, a whisper of grey bleach. The air between you and it is what
    you are meant to read, so it is calm."""
    rnd = random.Random(seed)
    img = new(255)
    _strata(img, rnd, seed, (2, 12, 23), (1.6, 2.4, 2.2),
            (("dirt", 0.9), ("dirt", 0.6), ("dirt", 0.8)),
            ((10, 18), (8, 15), (11, 20)), k_lit=0.5, mottle=0.4, bleach=0.3)
    for _ in range(5):
        x, y = rnd.randrange(N), rnd.randrange(N)
        put(img, x, y, "dirt", 1.6)
        put(img, x + 1, y + 1, "dirt", 0)
    return img


def t_heights_shell_hd(seed):
    """Breakable: sun-cracked crust over a void. The rock, with a star of
    fractures from one impact point -- each a dark crack with a lit lower
    lip, widening toward the centre -- and the crust spalling round it."""
    rnd = random.Random(seed)
    img = t_heights_rock_hd(seed + 700)
    cx, cy = 14 + rnd.randrange(-3, 4), 14 + rnd.randrange(-3, 4)
    for _ in range(3):                                      # spalled flakes
        a = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(4, 8)
        ellipse(img, "dirt", cx + r * math.cos(a), cy + r * math.sin(a),
                rnd.uniform(1.5, 2.5), rnd.uniform(1.0, 1.6), 1, wrap=False)
    for ang in range(0, 360, 45):
        a = math.radians(ang + rnd.randrange(-14, 15))
        x, y = cx + 0.5, cy + 0.5
        ln = rnd.randrange(11, 17)
        for i in range(ln):
            x += math.cos(a)
            y += math.sin(a)
            a += rnd.uniform(-0.18, 0.18)
            ix, iy = int(math.floor(x)), int(math.floor(y))
            ink(img, ix, iy)
            if i < ln // 3:
                ink(img, ix + 1, iy)
            if 0 <= ix < N and 0 <= iy + 1 < N and get(img, ix, iy + 1)[:3] != (0, 0, 0):
                m = level_of(get(img, ix, iy + 1))
                if m is not None:
                    put_c(img, ix, iy + 1, m[0], min(5, m[1] + 2))
    for (dx, dy) in ((0, 0), (1, 0), (0, 1), (1, 1), (-1, 0), (0, -1)):
        ink(img, cx + dx, cy + dy)                         # the impact pit
    return img


# ============================================================ scree
def t_heights_scree_hd(seed):
    """Loose slope: a heap of broken stone. Angular fragments, each a low
    pyramid lit facet by facet, grey and warm mixed, packed so a fragment
    rests on the ones behind it (later ones overlap and shadow earlier ones),
    in a dark matrix of grit. No bevel -- scree tiles in a mass."""
    rnd = random.Random(seed)
    img = fill(new(255), "dirt", 1.8, rnd, grain=0.3, cell=2)
    for _ in range(26):                                     # grit in the gaps
        x, y = rnd.randrange(N), rnd.randrange(N)
        put(img, x, y, "dirt", 2.6)
        put(img, x + 1, y + 1, "dirt", 0.6)
    pieces = []
    for _ in range(8):                                      # the big stones
        pieces.append((rnd.uniform(5.5, 8.0), rnd.uniform(4.0, 5.6)))
    for _ in range(5):                                      # the small ones
        pieces.append((rnd.uniform(2.6, 3.8), rnd.uniform(2.0, 3.0)))
    rnd.shuffle(pieces)
    for rx, ry in pieces:
        ramp, lvl = rnd.choice((("stone", 2.9), ("stone", 2.6), ("dirt", 3.1),
                                ("dirt", 2.8), ("stone", 3.2)))
        shard(img, rnd, rnd.uniform(0, N), rnd.uniform(0, N), rx, ry, ramp, lvl,
              shadow=1.2)
    return img


# ============================================================ basalt
STACK_EDGES = (0, 9, 17, 24)


def t_heights_stack_hd(seed):
    """A basalt stack behind the play field: columnar jointing drawn as
    prisms -- each column a lit left facet, a broad face and a shaded right
    facet -- with curved cooling fractures across them and a little ochre
    lichen. Held dark: the cleft between columns is a shadow, not sky (the
    1x first pass's bright cleft was the frog's own band)."""
    rnd = random.Random(seed)
    img = new(255)
    edges = list(STACK_EDGES) + [N]
    for i in range(len(edges) - 1):
        x0, x1 = edges[i], edges[i + 1]
        w = x1 - x0
        for x in range(x0, x1):
            lx = x - x0
            if lx == 0:
                lvl = 0.2                                   # the joint
            elif lx == 1:
                lvl = 2.6                                   # the lit arris
            elif lx <= 3:
                lvl = 2.0                                   # left facet
            elif lx >= w - 2:
                lvl = 0.8                                   # right facet
            else:
                lvl = 1.4
            for y in range(N):
                g = 0.3 * math.sin((y + i * 7) * 2 * math.pi / N * 2 + i)
                put(img, x, y, "stone", lvl + (g if 1 < lx < w - 2 else 0))
        for _ in range(rnd.choice((1, 2, 2))):               # cooling fractures
            y0 = rnd.randrange(N)
            for x in range(x0 + 1, x1):
                t = (x - x0 - w / 2.0) / (w / 2.0)
                y = y0 + int(round(1.4 * t * t))
                put(img, x, y, "stone", 0.2)
                put(img, x, y + 1, "stone", 2.3 if x - x0 < w - 2 else 1.4)
    for _ in range(rnd.randrange(1, 3)):                     # ochre lichen
        _lichen(img, rnd, rnd.randrange(N), rnd.randrange(N), "dirt", 1, 2)
    for _ in range(5):                                       # wind dust on the arrises
        i = rnd.randrange(len(STACK_EDGES))
        put(img, STACK_EDGES[i] + 1, rnd.randrange(N), "dirt", 2)
    return img


def t_heights_basalt_hd(seed):
    """The hard, dark block of the world: cut columnar basalt. A dressed
    block with a two-texel bevel (lit top and left, occluded foot and right),
    three column faces inside it each lit on its left, chisel tooling, and
    iron staining weeping out of the joints. The floor of the luma band, so
    a level has a wall that is unmistakably not the sky."""
    rnd = random.Random(seed)
    img = new(255)
    cols = (2, 12, 21, N - 2)
    mot = _noise(seed * 5 + 1, 8)
    breaks = {}
    for i in range(3):                                       # a cooling crack per column
        breaks[i] = rnd.randrange(6, N - 6)
    for y in range(N):
        for x in range(N):
            if y == 0 or x == 0:
                v = 3.4
            elif y == 1 or x == 1:
                v = 2.8
            elif y == N - 1 or x == N - 1:
                v = 0.0
            elif y == N - 2 or x == N - 2:
                v = 0.7
            else:
                i = max(j for j in range(3) if cols[j] <= x)
                lx = x - cols[i]
                w = cols[i + 1] - cols[i]
                # a prism: lit facet, broad face, shaded facet, in bands
                f = lx / float(w)
                v = 2.3 if f < 0.3 else (1.5 if f < 0.72 else 0.8)
                if lx == 0:
                    v = 0.2 if i else 1.2
                elif lx == 1:
                    v = 2.9
                v += 0.55 * mot(x, y) - y / 90.0
                t = (lx - w / 2.0) / (w / 2.0)
                by = breaks[i] + int(round(1.2 * t * t))
                if y == by and lx > 0:
                    v = 0.2
                elif y == by + 1 and lx > 0:
                    v += 0.9
            put(img, x, y, "stone", v)
    for (x, y) in ((N - 1, 0), (0, N - 1), (N - 1, N - 1)):  # the block's corners knocked off
        put(img, x, y, "stone", 0)
    for _ in range(rnd.randrange(4, 7)):                     # vesicles: gas bubbles in the lava
        x, y = rnd.randrange(4, N - 4), rnd.randrange(4, N - 4)
        put(img, x, y, "stone", 0.2)
        put(img, x + 1, y + 1, "stone", 2.4)
    for _ in range(rnd.randrange(2, 4)):                     # iron weeping from a joint
        x = rnd.choice(cols[1:3]) + rnd.choice((1, 2))
        y = rnd.randrange(3, 16)
        for k in range(rnd.randrange(4, 11)):
            put(img, x, y + k, "dirt", 2 if k < 3 else 1.4)
    put(img, 0, 0, "stone", 4)                               # the arris catches the sun
    put(img, 1, 0, "stone", 4)
    return img


# ============================================================ objects
def t_heights_plank_hd(seed):
    """One-way walkway: sun-dried timber gone silver, eight texels thick in
    all (four world units, as at 1x). A bleached arris, two boards butted
    together with a split along one, end grain checks, two pegs, and a rope
    lashing round each end. Painted a step low: the ink pass lifts it."""
    rnd = random.Random(seed)
    img = new(0)
    for x in range(N):
        put_c(img, x, 0, "metal", 4)
        put_c(img, x, 1, "metal", 3)
        for y, lv in ((2, 3.0), (3, 2.8), (4, 2.4), (5, 2.0)):
            put_c(img, x, y, "wood", lv + rnd.uniform(-0.25, 0.25))
        put_c(img, x, 6, "wood", 1.0)
    s = rnd.randrange(1 << 20)
    for x in range(N):                                     # weathered grain
        if wave(x, s, period=N) > 0.35:
            put_c(img, x, 3, "wood", 1.8)
        if wave(x, s + 1, period=N) > 0.55:
            put_c(img, x, 2, "metal", 3)
    bx = 15 + rnd.randrange(-2, 3)                         # the butt joint
    for y in range(1, 7):
        put_c(img, bx, y, "wood", 0.6)
        put_c(img, bx + 1, y, "wood", 3.6)
    sx = rnd.randrange(18, 24)                             # a split along the board
    for k in range(rnd.randrange(4, 8)):
        put_c(img, sx + k, 4, "wood", 0.8)
        put_c(img, sx + k, 5, "wood", 3.0)
    for px in (bx - 6, bx + 7):                            # pegs
        put_c(img, px, 3, "wood", 0.8)
        put_c(img, px + 1, 3, "wood", 1.4)
        put_c(img, px, 2, "wood", 4.4)
    for lx in (2, N - 5):                                  # lashings
        for y in range(0, 7):
            for k in range(3):
                if (y + k) % 3 != 2:
                    put_c(img, lx + k, y, "straw", (3 if k == 0 else 2) - (0.5 if y > 4 else 0))
                else:
                    put_c(img, lx + k, y, "straw", 1)
    return img


def t_heights_vent_hd(seed):
    """The hazard: a fumarole. A cracked iron-brown plate, three throats
    glowing in it with a lit lip and a dark mouth, ember cracks running
    between them, and heat coming off each as a rising ribbon that narrows
    and cools. The heat is the only ember in the world's tiles, which is
    what makes it read as the thing that hurts."""
    rnd = random.Random(seed)
    img = new(0)
    for x in range(N):                                     # the plate
        for y, lv in ((24, 3.4), (25, 2.8), (26, 2.2), (27, 1.8), (28, 1.4), (29, 1.0), (30, 0.6)):
            put_c(img, x, y, "dirt", lv + rnd.uniform(-0.2, 0.2))
        ink(img, x, 31)
    throats = (5, 16, 27)
    for cx in throats:
        for dx in range(-3, 4):                            # a raised lip
            put_c(img, cx + dx, 24, "dirt", 4 - (1 if dx > 0 else 0))
        for y in range(25, 29):                            # the glowing mouth
            half = 3 - (y - 25) // 2
            for dx in range(-half, half + 1):
                put_c(img, cx + dx, y, "ember", 5.6 - abs(dx) * 0.9 - (y - 25) * 0.3)
        put_c(img, cx - 1, 25, "gold", 5)
        put_c(img, cx, 25, "gold", 6)
    for i in range(len(throats) - 1):                      # ember cracks between
        x, y = throats[i] + 3, 27
        while x < throats[i + 1] - 3:
            put_c(img, x, y, "ember", 4)
            put_c(img, x, y + 1, "ember", 1)
            x += 1
            y = max(26, min(29, y + rnd.choice((-1, 0, 0, 1))))
    for cx in throats:                                     # the plumes
        ph = rnd.uniform(0, 2 * math.pi)
        top = rnd.randrange(6, 12)
        for y in range(23, top - 1, -1):
            k = 23 - y
            off = 1.1 * math.sin(k * 0.4 + ph) * min(1.0, k / 6.0)
            half = max(0.6, 2.6 - k * 0.11)
            lv = 5.2 - k * 0.2
            for x in range(int(math.floor(cx + off - half)), int(math.ceil(cx + off + half)) + 1):
                d = abs(x + 0.5 - (cx + off + 0.5)) / half
                if d > 1.0:
                    continue
                put_c(img, x, y, "ember", lv + (0.8 if d < 0.4 else 0) - (1 if d > 0.8 else 0))
        for _ in range(3):                                 # sparks breaking off
            put_c(img, cx + rnd.randrange(-5, 6), rnd.randrange(top, 18), "ember", 5)
    return img


def _link_face(img, cx, cy):
    """A chain link seen face-on: an oval ring with a hole, lit up-left."""
    rx, ry = 3.6, 5.6
    hx, hy = 1.5, 3.4
    for y in range(int(cy - ry - 1), int(cy + ry + 2)):
        for x in range(int(cx - rx - 1), int(cx + rx + 2)):
            nx, ny = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
            hnx, hny = (x + 0.5 - cx) / hx, (y + 0.5 - cy) / hy
            if nx * nx + ny * ny > 1.0 or hnx * hnx + hny * hny <= 1.0:
                continue
            # the ring's own normal: outer half faces out, inner half faces in
            outer = nx * nx + ny * ny > 0.55
            f = -(nx * _LX + ny * _LY) if not outer else (nx * _LX + ny * _LY)
            lv = 3.0 + f * 1.6
            put(img, x, y, "metal", lv)


def _link_edge(img, cx, cy, wrap=True):
    """A chain link seen edge-on: a bar three texels wide, rounded at its
    ends, lit on its left."""
    p = put if wrap else put_c
    for y in range(int(cy - 6), int(cy + 7)):
        for x, lv in ((cx - 1, 4), (cx, 3), (cx + 1, 1.6)):
            if abs(y + 0.5 - cy) > 6 or (abs(y + 0.5 - cy) > 5 and x != cx):
                continue
            p(img, x, y, "metal", lv)


def t_heights_chain_hd(seed):
    """The climbable: an anchored chain. Metal, so it cannot be confused with
    anything growing; links, alternately face-on and edge-on, one every four
    world units, so a run of it tiles; the edge-on links show through the
    holes of the face-on ones they pass through. Inked by the ink pass."""
    rnd = random.Random(seed)
    img = new(0)
    cx = 16
    for cy in (8, 24):
        _link_edge(img, cx, cy)
    for cy in (0, 16):
        _link_face(img, cx - 0.5 + 0.5, cy)
    for cy in (0, 16):                                    # through the hole
        for y in range(cy - 3, cy + 4):
            if abs(y - cy) >= 2:
                put(img, cx, y, "metal", 2)
    for cy in (0, 16, 32):                                 # wear glints on the faces
        put(img, cx - 3, cy - 2, "metal", 5)
        put(img, cx - 3, cy - 1, "metal", 4)
    if rnd.random() < 0.7:                                 # a fleck of rust
        y = rnd.randrange(N)
        put(img, cx + 2, y, "ember", 1)
    return img


# ============================================================ sky
def _cloud(img, rnd, cx, cy, w):
    """A cumulus on a flat base, drawn billow by billow back to front: each
    billow a `stone` 5 body with a 6 rim on its sunward side and a 4 rim on
    its far side, so where one overlaps the next its lit rim draws the
    crease. The base is cut flat and shaded to 3 -- never white."""
    puffs = []
    n = rnd.randrange(4, 6)
    for i in range(n):
        t = (i + 0.5) / n - 0.5                             # -0.5 .. 0.5 across
        r = rnd.uniform(0.17, 0.24) * w * (1.25 - abs(t) * 1.1)
        px = cx + t * w + rnd.uniform(-1, 1)
        py = cy - r * 0.6 - (1.0 - abs(t) * 2) * 2.5
        puffs.append((px, py, r))
    # back first: the tall middle billows, then the low ones in front
    puffs.sort(key=lambda p: p[1])
    base = cy + 1.0
    for (px, py, r) in puffs:
        for y in range(int(py - r - 1), int(py + r + 2)):
            if y + 0.5 > base:
                continue
            for x in range(int(px - r - 1), int(px + r + 2)):
                nx, ny = (x + 0.5 - px) / r, (y + 0.5 - py) / r
                d = nx * nx + ny * ny
                if d > 1.0:
                    continue
                f = nx * _LX + ny * _LY
                lv = 5
                if d > 0.55 and f > 0.35:
                    lv = 6
                elif d > 0.7 and f < -0.35:
                    lv = 4
                put(img, x, y, "stone", lv)
    for x in range(int(cx - w / 2 - 6), int(cx + w / 2 + 7)):
        y = int(base) - 1
        m = level_of(get(img, x, y))
        if m is not None and m[1] >= 5:
            put(img, x, y, "stone", 3)


def t_heights_cloud_hd(seed):
    """The cloud deck, as a tile: what a level lays down where the floor
    gives out and there is nothing below but weather. tiles_p3's re-valued
    air (`stone` 4, cool, under the straw hat's value), its wind streaks as
    long thin lenses, and one or two cumulus on it."""
    rnd = random.Random(seed)
    img = fill(new(255), "stone", 4, rnd, grain=0.0)
    for _ in range(2):                                     # wind streaks
        ellipse(img, "stone", rnd.uniform(0, N), rnd.uniform(0, N),
                rnd.uniform(3.5, 6.0), 0.8, 5)
    for _ in range(3):
        put(img, rnd.randrange(N), rnd.randrange(N), "stone", 3)
    # Kept inside the cell (a cloud cut by a neighbour's edge reads as a
    # seam), and varied in size and place per painting, with some paintings
    # clear air, so a gallery of them does not read as wallpaper.
    if rnd.random() < 0.8:
        w = rnd.uniform(10, 22)
        _cloud(img, rnd, rnd.uniform(4 + w / 2, N - 4 - w / 2), rnd.uniform(12, 28), w)
    return img


# ============================================================ edge dressers
@dresser("dress_heights")
def dress_heights_hd(img, mask, rnd):
    """Wind-cut rock: an exposed top is bleached in streaks running down
    from the lip, an exposed underside sheds (ragged, with a flake about to
    go), and an exposed side shows the strata as ledges -- each bed's lip
    stands proud on the lit left face and is notched in on the shaded right."""
    if not mask & BIT_N:
        for _ in range(rnd.randrange(2, 5)):
            x = rnd.randrange(N)
            for k in range(rnd.randrange(3, 7)):
                m = level_of(get(img, x, 3 + k))
                if m is not None:
                    put_c(img, x, 3 + k, "stone", max(m[1], 4 - k // 2))
    if not mask & BIT_S:
        s = rnd.randrange(1 << 20)
        for x in range(N):
            if wave(x, s) > 0.55:
                clear(img, x, N - 1)
                shift(img, x, N - 2, -1)
        for _ in range(rnd.randrange(1, 3)):                # a flake about to fall
            x = rnd.randrange(3, N - 6)
            for k in range(rnd.randrange(3, 5)):
                put_c(img, x + k, N - 3, "dirt", 3)
                put_c(img, x + k, N - 2, "dirt", 1)
    for side, bit in (("left", BIT_W), ("right", BIT_E)):
        if mask & bit:
            continue
        lit = side == "left"
        for y0 in ROCK_TOPS[1:]:
            for k in range(3):
                x, y = side_xy(side, k, y0)
                put_c(img, x, y, "dirt", 4 if lit else 1)
                x, y = side_xy(side, k, y0 - 1)
                put_c(img, x, y, "dirt", 1 if lit else 0)


@dresser("dress_heights_bg")
def dress_heights_bg_hd(img, mask, rnd):
    """The far cliff's exposed top: short runs of its lip catch the light,
    held two steps down so it stays behind."""
    if not mask & BIT_N:
        x = 0
        while x < N:
            if rnd.random() < 0.35:
                for k in range(rnd.randrange(2, 7)):
                    put_c(img, x + k, 0, "dirt", 2)
                    put_c(img, x + k, 1, "dirt", 1.4)
                x += 7
            else:
                x += 1


# ============================================================ accents
ACCENTS["heights"] = [lambda i, r: pebble(i, r, "stone", 4),
                      lambda i, r: chip(i, r, "dirt", 5)]
CAP_ACCENTS[241] = [lambda i, r: pebble(i, r, "stone", 4, y0=2),
                    lambda i, r: chip(i, r, "metal", 5)]


# ============================================================ decorations
@decoration("d_chain_hang")
def d_chain_hang_hd(img, rnd):
    """A length of chain left hanging from whatever is above: small links
    alternately face-on and edge-on, its shadow on the wall to the right,
    and a broken link at the end."""
    x = rnd.randrange(5, N - 6)
    ln = rnd.randrange(14, N + 1)
    for y in range(ln):
        k = y % 6
        if k in (0, 1, 2, 3):                              # face-on: a ring
            if k in (0, 3):
                put_c(img, x, y, "metal", 3)
                put_c(img, x + 1, y, "metal", 2)
            else:
                put_c(img, x - 1, y, "metal", 3)
                put_c(img, x + 2, y, "metal", 1)
        else:                                               # edge-on: a bar
            put_c(img, x, y, "metal", 3)
            put_c(img, x + 1, y, "metal", 1)
        shift(img, x + 3, y + 1, -1)
    put_c(img, x - 1, ln, "metal", 2)                      # the broken link
    put_c(img, x - 1, ln + 1, "metal", 1)
    return img


# ============================================================ registrations
# id, the seed its T_AT line uses, painter. 244 (the sky gallery) is a
# see-through void: nothing is registered for it.
tile(240, 2401)(t_heights_rock_hd)
tile(241, 2411)(lambda s: t_heights_rock_hd(s, sun=True))
tile(242, 2421)(t_heights_wall_hd)
tile(243, 2431)(t_heights_scree_hd)
tile(245, 2451)(t_heights_stack_hd)
tile(246, 2461)(t_heights_plank_hd)
tile(247, 2471)(t_heights_vent_hd)
tile(248, 2481)(t_heights_chain_hd)
tile(249, 2491)(t_heights_basalt_hd)
tile(250, 2501)(t_heights_cloud_hd)
tile(251, 2511)(t_heights_shell_hd)
