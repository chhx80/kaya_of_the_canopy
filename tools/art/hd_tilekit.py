"""The tileset's native 2x machinery (docs/plan-hd.md, phase H1).

`tiles.py` draws every tile at 16x16 and its autotile machinery -- rim bands,
corner pockets, the phase C edge course, the refit rim, accents, ink, contact
shadows -- is written in 16 px constants. This module is the same machinery
written for a cell of `N = 16 * ART_SCALE` texels, so an edge, a corner or a
variant of a redrawn material is DRAWN at 32x32 rather than upscaled.

What changes hands with whom:

  * A world's tile painters live in their own module (`hd_tiles_<world>.py`)
    and register with the decorators below. Nothing in here names a world.
  * `tiles.py` asks `is_native(tid)` per gameplay id. A native id is built from
    its registered painter, its variants are edged here, and everything else in
    the atlas is today's 1x cell through `palette.upscale()` -- so a world that
    has not been redrawn yet ships exactly as it did.
  * The registries are keyed by plain values (a tile id, the 1x dresser's or
    decoration's function name, a group name), never by importing tiles.py, so
    a world module can import this one without a cycle.

Coordinates are texels unless a name says otherwise; WU is one world unit in
texels. Shading is whole ramp steps (no Bayer), as the approved look sample
decided: a fractional level at 2x resolves to a checkerboard over four times the
texels. Light is from the upper left, as everywhere in tools/art.

How to redraw a world with this: docs/hd-tiles-howto.md.
"""
import math
import random

from PIL import Image

from .palette import ART_SCALE, INK, RAMPS

TS = 16                    # a tile, in world units (never changes)
WU = ART_SCALE             # texels per world unit
N = TS * WU                # a tile, in texels
TOP = len(RAMPS["stone"]) - 1

BIT_N, BIT_NE, BIT_E, BIT_SE = 1, 2, 4, 8
BIT_S, BIT_SW, BIT_W, BIT_NW = 16, 32, 64, 128
CLEAR = (0, 0, 0, 0)


# ================================================================ registries
#: tid -> (painter(seed) -> N x N image, the seed the gameplay cell uses)
TILES = {}
#: name of a 1x `decorate=` dresser in tiles.py -> its 2x twin(img, mask, rnd)
DRESSERS = {}
#: name of a 1x decoration in tiles.py's DECOR -> its 2x twin(img, rnd)
DECOR = {}
#: group -> 2x accent painters(img, rnd), cycled like tiles_p3.ACCENTS
ACCENTS = {}
#: capped tile id -> 2x accent painters, like tiles_p3.CAP_ACCENTS
CAP_ACCENTS = {}
#: group -> overrides for the rim dict at 2x (any key of a tiles.RIM_* dict,
#: plus `top_hd` etc.: an explicit texel profile instead of the interpolated one)
RIM_HD = {}


def tile(tid, seed):
    """Register the 2x painter of gameplay tile `tid`; `seed` is the one its
    T() line uses (and, for a variant spec, its seeds[0])."""
    def wrap(fn):
        assert tid not in TILES, "tile %d registered twice" % tid
        TILES[tid] = (fn, seed)
        return fn
    return wrap


def dresser(name):
    def wrap(fn):
        DRESSERS[name] = fn
        return fn
    return wrap


def decoration(name):
    def wrap(fn):
        DECOR[name] = fn
        return fn
    return wrap


def is_native(tid):
    return tid in TILES


def base(tid):
    fn, seed = TILES[tid]
    img = fn(seed)
    assert img.size == (N, N), "tile %d painted at %s, not %dx%d" % (tid, img.size, N, N)
    return img


def build(tid, seed):
    img = TILES[tid][0](seed)
    assert img.size == (N, N), "tile %d painted at %s" % (tid, img.size)
    return img


# ================================================================ primitives
def new(alpha=0):
    return Image.new("RGBA", (N, N), (0, 0, 0, alpha))


def _rgb(ramp, level):
    return RAMPS[ramp][max(0, min(TOP, int(round(level))))]


def put(img, x, y, ramp, level, alpha=255):
    """Whole-step texel, WRAPPED onto the tile: a structure that crosses one
    edge comes back in at the other, so fills tile."""
    img.putpixel((int(x) % N, int(y) % N), _rgb(ramp, level) + (alpha,))


def put_c(img, x, y, ramp, level, alpha=255):
    """Whole-step texel, CLIPPED: for edges and objects that must not wrap."""
    if 0 <= x < N and 0 <= y < N:
        img.putpixel((int(x), int(y)), _rgb(ramp, level) + (alpha,))


def ink(img, x, y):
    if 0 <= x < N and 0 <= y < N:
        img.putpixel((int(x), int(y)), INK + (255,))


def clear(img, x, y):
    if 0 <= x < N and 0 <= y < N:
        img.putpixel((int(x), int(y)), CLEAR)


def get(img, x, y):
    return img.getpixel((int(x) % N, int(y) % N))


_LOOKUP = {tuple(c): (n, i) for n, steps in RAMPS.items() for i, c in enumerate(steps)}


def level_of(p):
    """(ramp, step) of a pixel, or None for transparent, ink or off-ramp."""
    if p[3] == 0:
        return None
    return _LOOKUP.get(tuple(p[:3]))


def shift(img, x, y, by, wrap=False, floor=0, ceil=TOP):
    """Move a texel `by` whole steps along whatever ramp it is already on.
    The edge machinery works this way rather than overdrawing a flat band, so
    the pebbles, roots and joints a painter put near an edge survive its
    lighting -- at 2x those are the detail, and a flat band would wipe them."""
    if not wrap and not (0 <= x < N and 0 <= y < N):
        return
    p = get(img, x, y)
    m = level_of(p)
    if m is None:
        return
    s = m[1] + int(round(by))
    s = max(min(floor, m[1]), min(max(ceil, m[1]), s))
    img.putpixel((int(x) % N, int(y) % N), tuple(RAMPS[m[0]][max(0, min(TOP, s))]) + (p[3],))


def step(img, x, y):
    m = level_of(get(img, x, y))
    return None if m is None else m[1]


def fill(img, ramp, lvl, rnd, grain=0.3, cell=2):
    """Flat material with grain in `cell`-texel squares: per-texel grain at 2x
    is a finer noise than 1x ever showed and reads as static, not material."""
    g = {}
    for y in range(N):
        for x in range(N):
            k = (x // cell, y // cell)
            if k not in g:
                g[k] = rnd.uniform(-grain, grain)
            put(img, x, y, ramp, lvl + g[k])
    return img


def blob(img, ramp, cx, cy, rx, ry, lvl, lit=1.4, dark=1.3, shadow=None, wrap=True):
    """A lit lump in whole steps. `shadow` darkens a crescent of whatever is
    under it below-right by that many steps, so it sits IN the material."""
    p = put if wrap else put_c
    for y in range(int(cy - ry - 3), int(cy + ry + 4)):
        for x in range(int(cx - rx - 3), int(cx + rx + 4)):
            if not wrap and not (0 <= x < N and 0 <= y < N):
                continue
            nx, ny = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
            d = nx * nx + ny * ny
            if d > 1.0:
                if shadow is not None:
                    sx, sy = (x + 0.5 - cx - 1.2) / rx, (y + 0.5 - cy - 1.4) / ry
                    if sx * sx + sy * sy <= 1.0:
                        shift(img, x, y, -shadow, wrap=wrap)
                continue
            v = lvl + (1.0 - d) * 1.1
            facing = -nx - ny
            if facing > 0.55:
                v += lit
            elif facing < -0.6:
                v -= dark
            if d > 0.72 and facing < -0.2:
                v -= 0.6
            p(img, x, y, ramp, v)


def ellipse(img, ramp, cx, cy, rx, ry, lvl, wrap=True, alpha=255):
    """A flat patch on one step (no lighting): leaves, spots, the moss mat."""
    p = put if wrap else put_c
    for y in range(int(cy - ry - 1), int(cy + ry + 2)):
        for x in range(int(cx - rx - 1), int(cx + rx + 2)):
            nx, ny = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
            if nx * nx + ny * ny <= 1.0:
                p(img, x, y, ramp, lvl, alpha)


def crack(img, ramp, x, y, length, lvl, rnd, drift=(0, 1, 1), wrap=True):
    """A fissure: a dark line one texel wide with a lit lip under it -- at 1x
    the same thing was a whole world unit wide and read as a gouge."""
    p = put if wrap else put_c
    for _ in range(length):
        p(img, x, y, ramp, lvl - 2.2)
        p(img, x, y + 1, ramp, lvl + 0.9)
        x += rnd.choice(drift)
        y += rnd.choice((-1, 0, 0, 1))


def root(img, rnd, x, y, length, lvl=3.0, ramp="dirt", wrap=True):
    """A root fibre: a wandering dark line with a lit lip below it, that may
    fork once."""
    p = put if wrap else put_c
    dx = rnd.choice((-1, 1))
    for i in range(length):
        p(img, x, y, ramp, lvl - 1.9)
        p(img, x, y + 1, ramp, lvl + 0.9)
        x += dx
        if rnd.random() < 0.35:
            y += rnd.choice((-1, 1))
        if i == length // 2 and rnd.random() < 0.6:
            root(img, rnd, x, y + 1, length // 3, lvl, ramp, wrap)


def grit(img, rnd, ramp, count, lit, dark, box=None):
    """Loose grains: a lit texel with its own shadow down-right of it."""
    x0, y0, x1, y1 = box or (0, 0, N, N)
    for _ in range(count):
        x, y = rnd.randrange(x0, x1), rnd.randrange(y0, y1)
        put(img, x, y, ramp, lit)
        put(img, x + 1, y + 1, ramp, dark)


def wave(i, seed, period=N, octaves=((1, 1.0), (2, 0.5), (3, 0.3))):
    """A smooth periodic 1D signal in [-1, 1]: ragged edges that wander rather
    than flicker column by column, and still meet themselves across a tile."""
    r = random.Random(seed)
    v = 0.0
    tot = 0.0
    for f, a in octaves:
        v += a * math.sin(2 * math.pi * f * i / period + r.uniform(0, 2 * math.pi))
        tot += a
    return v / tot


def leaf(img, cx, cy, ang, ln, wd, ramp, lvl, rib=1.0, rim=-1.0, wrap=True, alpha=255):
    """A pointed leaf along angle `ang`: lit upper half, a midrib, a shaded
    rim on the side away from the light."""
    p = put if wrap else put_c
    ca, sa = math.cos(ang), math.sin(ang)
    r = int(ln + 3)
    for y in range(int(cy - r), int(cy + r + 1)):
        for x in range(int(cx - r), int(cx + r + 1)):
            u = (x + 0.5 - cx) * ca + (y + 0.5 - cy) * sa
            v = -(x + 0.5 - cx) * sa + (y + 0.5 - cy) * ca
            t = u / ln
            if not 0 <= t <= 1:
                continue
            half = wd * math.sin(math.pi * t) ** 0.8
            if abs(v) > half:
                continue
            # the half whose normal points up-left, toward the light
            up = (v > 0) if (sa - ca) > 0 else (v < 0)
            l = lvl + (0.6 if up else -0.4)
            if abs(v) < 0.55 and 0.1 < t < 0.9:
                l = lvl + rib
            elif abs(v) > half - 0.9 and not up:
                l = lvl + rim
            p(img, x, y, ramp, l, alpha)


# ================================================================ edges
def _profile(deltas):
    """A 1x rim's per-pixel deltas resampled to texels: the same light falloff
    in world units, but as a gradient twice as fine, and fading out over its
    last texel instead of stopping on a hard line."""
    if not deltas:
        return []
    out = []
    n = len(deltas) * WU
    for t in range(n):
        u = (t + 0.5) / WU - 0.5
        i = int(math.floor(u))
        f = u - i
        a = deltas[max(0, min(len(deltas) - 1, i))]
        b = deltas[i + 1] if i + 1 < len(deltas) else deltas[-1] * 0.4
        out.append(a + (b - a) * f if u > 0 else deltas[0])
    return out


def side_xy(side, k, i):
    """Texel `k` deep into the tile from `side`, at position `i` along it."""
    if side == "top":
        return i, k
    if side == "bottom":
        return i, N - 1 - k
    if side == "left":
        return k, i
    return N - 1 - k, i


def rim_band(img, rnd, side, prof, ragged, broken, seed):
    """Light (or occlude) an exposed side, as a RELATIVE shift that fades into
    the tile. Its depth wanders on a smooth periodic wave rather than per
    column, and `broken` skips runs of several texels, so the edge reads as a
    weathered face instead of a ruled line or a comb."""
    depth = len(prof)
    gap = 0
    for i in range(N):
        if gap > 0:
            gap -= 1
            continue
        if broken and rnd.random() < broken / 3.0:
            gap = rnd.randrange(2, 5)
            continue
        d = depth
        if ragged:
            d -= int(round((wave(i, seed) * 0.5 + 0.5) * ragged * WU * 1.5))
            d -= 1 if rnd.random() < ragged * 0.4 else 0
        for k in range(max(0, d)):
            x, y = side_xy(side, k, i)
            shift(img, x, y, prof[k])


CORNERS = (("nw", BIT_NW, BIT_N, BIT_W), ("ne", BIT_NE, BIT_N, BIT_E),
           ("sw", BIT_SW, BIT_S, BIT_W), ("se", BIT_SE, BIT_S, BIT_E))


def corner_xy(corner, x, y):
    px = x if corner in ("nw", "sw") else N - 1 - x
    py = y if corner in ("nw", "ne") else N - 1 - y
    return px, py


def corner_pocket(img, rnd, corner, occ, radius=5):
    """Ambient occlusion in an inside corner: concentric whole-step rings
    (radius in world units), relative so the material shows through it."""
    r = radius * WU
    for y in range(r):
        for x in range(r):
            d = math.hypot(x + 0.5, y + 0.5)
            if d > r:
                continue
            k = 1.0 - d / r
            px, py = corner_xy(corner, x, y)
            shift(img, px, py, -occ * k * 1.15 + rnd.uniform(-0.15, 0.15))


def convex_corner(img, rnd, corner, lift, radius=3.2, cut=False):
    """The outer corner where two exposed faces meet. Rounded on a radius:
    the texels along the curve take the corner's light (lifted on the sunward
    nw, dropped on the se), and with `cut` the texels outside it are cleared,
    with the darkest step of the material on the stair-steps so the curve is
    smooth rather than a notch."""
    sun = corner == "nw"
    away = corner == "se"
    d_lvl = lift if sun else (-lift if away else (lift * 0.4 if corner == "ne" else -lift * 0.4))
    r = radius * WU / 2.0 + 1.0
    for y in range(int(r) + 2):
        for x in range(int(r) + 2):
            dx, dy = r - (x + 0.5), r - (y + 0.5)
            d = math.hypot(max(0.0, dx), max(0.0, dy))
            px, py = corner_xy(corner, x, y)
            if dx <= 0 and dy <= 0:
                continue
            if cut and d > r:
                clear(img, px, py)
            elif d > r - 1.6:
                shift(img, px, py, d_lvl)
                if cut and d > r - 0.7 and not sun:
                    shift(img, px, py, -1)


def edge_course(img, mask, rim, group, standable):
    """Phase C's course at 2x: one whole step up along an exposed top and one
    down along an exposed underside, a world unit (two texels) deep."""
    if group not in standable:
        return
    if not mask & BIT_N and rim.get("top") is not None:
        for x in range(N):
            for k in range(WU):
                shift(img, x, k, +1)
    if not mask & BIT_S:
        for x in range(N):
            for k in range(WU):
                shift(img, x, N - 1 - k, -1)


# ------------------------------------------------------------- refit rim
def refit_rim(img, mask, spec, cap, rnd):
    """tiles_p3.refit_rim at 2x. The lip is an absolute step, as at 1x, but a
    world unit of it is now two texels: a bright arris texel, a face texel
    that keeps a trace of the material under it, and a shadow under the face.
    Glints are short runs on the arris alone. Chips are a rounded bite."""
    if spec is None:
        return
    ramp = spec["ramp"]
    open_n = not mask & BIT_N
    open_s = not mask & BIT_S
    open_w = not mask & BIT_W
    open_e = not mask & BIT_E
    lip = spec["lip"]
    if open_n:
        if cap is not None:
            gramp, gstep, chance = cap
            x = 0
            while x < N:
                if rnd.random() < chance * 0.6:
                    for k in range(rnd.randrange(1, 3)):
                        if get(img, x + k, 0)[3] and x + k < N:
                            put_c(img, x + k, 0, gramp, gstep)
                    x += 3
                else:
                    x += 1
        else:
            for x in range(N):
                put_c(img, x, 0, ramp, lip)
                s = step(img, x, 1)
                put_c(img, x, 1, ramp, lip - 1 if (s is None or s < lip) else lip)
                put_c(img, x, 2, ramp, lip - 1 if rnd.random() < 0.7 else lip - 2)
                for k in (3, 4):
                    s = step(img, x, k)
                    if s is not None and s >= lip - 1:
                        put_c(img, x, k, ramp, lip - 2)
            gramp = spec.get("glint_ramp", ramp)
            gstep = spec.get("glint_step", min(TOP, lip + 1))
            x = 0
            while x < N:
                if rnd.random() < spec["glint"]:
                    run = rnd.randrange(2, 7)
                    for k in range(run):
                        put_c(img, x + k, 0, gramp, gstep)
                    if x + run < N:
                        put_c(img, x + run, 1, ramp, lip - 2)   # the glint's end bevel
                    x += run + 2
                else:
                    x += 2
    if open_s:
        for x in range(N):
            put_c(img, x, N - 1, ramp, spec["under"])
            put_c(img, x, N - 2, ramp, spec["under"] + (1 if rnd.random() < 0.35 else 0))
            for k in (3, 4):
                s = step(img, x, N - k)
                if s is not None and s > spec["under"] + 1:
                    put_c(img, x, N - k, ramp, s - 1)
    if open_e:
        for y in range(N):
            for k in range(WU):
                shift(img, N - 1 - k, y, -1, floor=0)
    if open_w:
        for y in range(WU * 2 if open_n else 0, N):
            for k in range(WU):
                s = step(img, k, y)
                if s is not None and s < lip:
                    shift(img, k, y, +1)
    if spec["chip"]:
        for corner, on in (("nw", open_n and open_w), ("ne", open_n and open_e),
                           ("sw", open_s and open_w), ("se", open_s and open_e)):
            if on:
                _chip_corner(img, corner)


def _chip_corner(img, corner):
    """A rounded chip off a convex corner, two texels in: the outer texels
    cleared, the next ones darkened so the curve reads against any backdrop."""
    for (x, y) in ((0, 0), (1, 0), (0, 1)):
        clear(img, *corner_xy(corner, x, y))
    for (x, y) in ((2, 0), (1, 1), (0, 2)):
        px, py = corner_xy(corner, x, y)
        shift(img, px, py, -1 if corner != "nw" else 0)


def paint_edges(img, mask, rim, rnd, group, tid, p3_spec, cap, standable, dress):
    """Turn an interior painting into blob case `mask`, at 2x. The same steps
    as tiles.paint_edges, in the same order: side bands, corners, the
    material's dresser, the phase C course, the refit rim."""
    hd = dict(rim)
    hd.update(RIM_HD.get(group, {}))
    seed = rnd.randrange(1 << 30)
    for side, bit in (("top", BIT_N), ("bottom", BIT_S), ("left", BIT_W), ("right", BIT_E)):
        if mask & bit:
            continue
        prof = hd.get(side + "_hd")
        if prof is None:
            prof = _profile(hd.get(side))
        if prof:
            rim_band(img, rnd, side, prof, hd.get("ragged", 0.0), hd.get("broken", 0.0),
                     seed + bit)
    for corner, dbit, c1, c2 in CORNERS:
        open1 = not mask & c1
        open2 = not mask & c2
        if open1 and open2:
            convex_corner(img, rnd, corner, hd.get("convex", 1.2))
        elif not open1 and not open2 and not mask & dbit:
            corner_pocket(img, rnd, corner, hd.get("occlusion", 1.7))
    if dress is not None:
        dress(img, mask, rnd)
    edge_course(img, mask, hd, group, standable)
    refit_rim(img, mask, p3_spec, cap, random.Random(rnd.random()))


# ================================================================ ink
def ink_interactive(img):
    """tiles_p3.ink_interactive at 2x: lift every ramp texel one step, then
    ink the silhouette with the hero's own weighted line -- one texel where
    the light falls, a second texel on the shadow side (below and right), the
    way the 2x Kaya is outlined. One texel alone is half a world unit and read
    as pencil next to her."""
    px = img.load()
    for y in range(N):
        for x in range(N):
            p = px[x, y]
            if p[3] == 0:
                continue
            m = _LOOKUP.get(p[:3])
            if m is not None and m[1] < TOP:
                px[x, y] = tuple(RAMPS[m[0]][m[1] + 1]) + (p[3],)

    def solid(x, y):
        return 0 <= x < N and 0 <= y < N and px[x, y][3] != 0

    def body(x, y):
        return solid(x, y) and px[x, y][:3] != INK

    ring = set()
    for y in range(N):
        for x in range(N):
            if px[x, y][3] != 0:
                continue
            if any(body(x + dx, y + dy) for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0))):
                ring.add((x, y))
    for x, y in ring:
        px[x, y] = INK + (255,)
    heavy = set()
    for y in range(N):
        for x in range(N):
            if px[x, y][3] != 0:
                continue
            # shadow side: the texel below or right of a ring texel that
            # itself sits below or right of the body
            if (x, y - 1) in ring and body(x, y - 2):
                heavy.add((x, y))
            elif (x - 1, y) in ring and body(x - 2, y):
                heavy.add((x, y))
    for x, y in heavy:
        px[x, y] = INK + (255,)
    return img


# ================================================================ shadows
def contact_shadow_sheet(cells, depth, corner):
    """tiles_p3's contact shadows, drawn per texel: the alpha table is in
    world units, sampled at each texel's centre and interpolated, so the
    falloff is a gradient twice as fine instead of the same steps doubled."""
    img = Image.new("RGBA", (N * len(cells), N), (0, 0, 0, 0))

    def at(table, u):
        u = u - 0.5
        if u < 0:
            return table[0]
        i = int(math.floor(u))
        if i + 1 >= len(table):
            return table[-1] * max(0.0, 1.0 - (u - (len(table) - 1)) * 1.6) if i < len(table) else 0.0
        f = u - i
        return table[i] + (table[i + 1] - table[i]) * f

    for c, name in enumerate(cells):
        ox = c * N
        for y in range(N):
            for x in range(N):
                ux, uy = (x + 0.5) / WU, (y + 0.5) / WU
                a = 0.0
                if name == "n":
                    a = at(depth["n"], uy)
                elif name == "w":
                    a = at(depth["w"], ux)
                elif name == "s":
                    a = at(depth["s"], TS - uy)
                elif name == "e":
                    a = at(depth["e"], TS - ux)
                elif name == "nw":
                    a = at(corner, ux + uy - 0.5)
                if a > 0.004:
                    img.putpixel((ox + x, y), INK + (int(round(a * 255)),))
    return img
