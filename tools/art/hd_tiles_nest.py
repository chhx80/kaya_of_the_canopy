"""5. THE OBSIDIAN NEST (ids 280-291), drawn natively at 2x.

The world's rule from tiles.py still holds at 2x -- "a world must not swallow
the player": the bulk of every mass is `purple` 0-1 and `stone` 0 (luma 22-40),
near black with a violet cast. What is brighter is a texel or two wide: a lit
arris between two flake scars, a short glare on the glass, a live seam. Ember
4-6 is the bird and the fish, so it never fills; it runs in cracks, seams and
on the hazard's hot points, with a dark ember halo (steps 1-2, still in band)
round it so it reads as heat rather than as paint.

Knapped glass is the material. At 1x it was lit blobs and a few scratched
lines; here it is a height field: every flake scar is a shallow concave scoop
(`_Scars`), the surface is the deepest cut at each texel, and it is lit from
its own normal. So a scar's far wall catches the light, its near wall falls
into shade, and wherever two scars meet there is a hard arris with a lit side
and a dark side -- which is what knapping looks like. Faint concentric ripples
on each scoop are the conchoidal rings.

Sections: the glass and everything built from it (280, 281, 282, 289, 291),
the made things (283 basalt, 290 plate, 285 flue), the inked tiles (286 ledge,
287 shards, 288 chain), the dressers, accents, decorations, registrations.
284 is the see-through void and is left empty, as in every world.
"""
import math
import random

from .hd_tilekit import (BIT_E, BIT_N, BIT_S, BIT_W, N, WU, blob, clear, decoration,
                         dresser, ellipse, fill, get, ink, level_of, new, put, put_c,
                         shift, side_xy, step, tile, wave)
from .hd_tilekit import ACCENTS, CAP_ACCENTS

_LIGHT = (-0.55, -0.62, 0.56)        # upper left, and toward the viewer


# ============================================================ the glass
class _Scars:
    """A periodic field of flake scars. Each is a shallow concave scoop on a
    tilted plane -- h = k * |p - c|^2 + tilt . p + o, with faint concentric
    ripples, the conchoidal rings -- and the surface is the lowest of them,
    so neighbouring scars meet on a ridge (an arris), curved where their
    depths differ. Each scar's tilt gives it its own tone, which is what
    makes a knapped face read as facets. Wrapped, so a fill tiles.

    One scar per cell of a jittered 2x2 grid (random centres cluster, and a
    scar with no neighbour on one side meets its own wrapped copy on a dead
    straight line), drawn from `shared`, one stream per material; then one
    scar of the painting's own, struck at one of the places inside the cell
    where four meet. The texels along a cell edge belong to the shared scars in
    every variant, so two different paintings side by side meet without a
    seam, and the variants still differ inside."""

    def __init__(self, rnd, shared, kmin=0.012, kmax=0.024, tilt=0.6, ripple=0.12):
        self.scars = []
        for c in range(5):
            r = shared if c < 4 else rnd
            a = r.uniform(0, 2 * math.pi)
            t = r.uniform(0.2, 1.0) * tilt
            if c < 4:
                # centred ON the cell's edges and corners, so a cell edge cuts
                # through the middle of a facet rather than running along a
                # ridge (which would draw the tile grid on the wall)
                gx, gy = (c % 2) * N / 2.0 + r.uniform(-4, 4), \
                         (c // 2) * N / 2.0 + r.uniform(-4, 4)
            else:
                # at one of the four junctions inside the cell
                gx = r.choice((0.25, 0.75)) * N + r.uniform(-3, 3)
                gy = r.choice((0.25, 0.75)) * N + r.uniform(-3, 3)
            self.scars.append((gx, gy,
                               r.uniform(kmin, kmax),
                               r.uniform(-0.35, 0.35) if c < 4 else r.uniform(0.2, 0.6),
                               r.uniform(1.6, 2.6), r.uniform(0, 2 * math.pi),
                               t * math.cos(a), t * math.sin(a)))
        self.ripple = ripple

    def at(self, x, y):
        """(normal shade, which scar image) at texel centre (x, y). The image,
        not just the scar: where a scar meets its own wrapped copy that is a
        ridge too, and must be drawn as one rather than as a jump in shade."""
        px, py = x + 0.5, y + 0.5
        best = None
        for i, (cx, cy, k, o, wl, ph, tx, ty) in enumerate(self.scars):
            for ox in (-N, 0, N):
                for oy in (-N, 0, N):
                    dx, dy = px - cx - ox, py - cy - oy
                    r = math.hypot(dx, dy)
                    # the tilt is measured from the scar's own centre, so the
                    # field stays periodic; it only decides who wins nearby
                    h = k * r * r + o + self.ripple * math.sin(r / wl + ph)
                    if best is None or h < best[0]:
                        best = (h, (i, round(cx + ox), round(cy + oy)), dx, dy, r, k,
                                wl, ph, tx, ty)
        h, i, dx, dy, r, k, wl, ph, tx, ty = best
        dr = self.ripple * math.cos(r / wl + ph) / wl / max(r, 0.5)
        gx, gy = 2 * k * dx + dr * dx + tx, 2 * k * dy + dr * dy + ty
        nz = 1.0 / math.sqrt(gx * gx + gy * gy + 1.0)
        shade = (-gx * _LIGHT[0] - gy * _LIGHT[1] + _LIGHT[2]) * nz
        return shade, i


#: Obsidian's own scale: a violet-black body that turns, as it catches the
#: light, into a cold grey sheen and then a white glare. Bulk sits on 0-1.
GLASS = (("purple", 0), ("purple", 1), ("purple", 2), ("stone", 2), ("stone", 3),
         ("stone", 4), ("metal", 5), ("metal", 6))
#: The background's: the same body, its sheen held two steps down.
GLASS_BG = (("stone", 0), ("purple", 0), ("purple", 1), ("stone", 1), ("purple", 2))


def gput(img, x, y, lvl, scale=GLASS, wrap=True):
    ramp, st = scale[max(0, min(len(scale) - 1, int(round(lvl))))]
    (put if wrap else put_c)(img, x, y, ramp, st)


def _knap(img, rnd, scars, base, gain, cap, scale=GLASS, glare=0):
    """Paint knapped glass on `scale`: each texel's step from its scar's
    normal; the ridge between two scars an arris -- a texel a step and more
    above its own wall on the ridge's upper-left side (most where the ridge
    runs square to the light), a crease a step down on its lower-right -- so
    every arris is a hard edge without outlining every facet alike; and
    `glare` short specular runs along the brightest arrises. Returns
    {texel: tone} for the arris texels."""
    sh = {}
    for y in range(-1, N + 1):                           # unwrapped, one texel round
        for x in range(-1, N + 1):
            sh[x, y] = scars.at(x, y)
    def tone(x, y):
        return min(cap, base + (sh[x, y][0] - 0.62) * gain)

    arris = {}
    for y in range(N):
        for x in range(N):
            i = sh[x, y][1]
            t = tone(x, y)
            fwd = [(x + dx, y + dy) for dx, dy in ((1, 0), (0, 1), (1, 1))
                   if sh[x + dx, y + dy][1] != i]
            back = [(x - dx, y - dy) for dx, dy in ((1, 0), (0, 1))
                    if sh[x - dx, y - dy][1] != i]
            # how hard the edge is: two facets turned alike barely show theirs
            hard = max([abs(t - tone(*q)) for q in fwd + back] + [0.0])
            if fwd and (x + 1, y) in fwd or (x, y + 1) in fwd:
                lift = 0.45 + (0.75 if (x + 1, y + 1) in fwd and len(fwd) > 1 else 0.0)
                t += lift if hard > 0.45 else lift * 0.5
                arris[x, y] = t
            elif back:
                t -= 1.1 if hard > 0.45 else 0.5
            gput(img, x, y, t, scale)
    if glare:
        done = []
        for (x, y) in sorted(arris, key=lambda q: -arris[q]):
            if len(done) >= glare:
                break
            if any(abs(x - a) < 10 and abs(y - b) < 10 for (a, b) in done):
                continue
            done.append((x, y))
            run = [(x, y)]
            for _ in range(rnd.randrange(2, 4)):          # walk on along the arris
                cx, cy = run[-1]
                nxt = [((cx + dx) % N, (cy + dy) % N) for dx, dy in
                       ((1, -1), (-1, 1), (1, 0), (0, 1), (-1, 0), (0, -1))
                       if ((cx + dx) % N, (cy + dy) % N) in arris
                       and ((cx + dx) % N, (cy + dy) % N) not in run
                       and ((cx + dx) % N, (cy + dy) % N) not in [
                           ((rx + 1) % N, ry) for rx, ry in run] + [
                           (rx, (ry + 1) % N) for rx, ry in run]]
                if not nxt:
                    break
                run.append(nxt[0])
            for k, (gx, gy) in enumerate(run):
                gput(img, gx, gy, len(scale) - (1 if k == 1 or len(run) == 1 else 2), scale)
    return arris


def _chip_scoop(img, cx, cy, r, lvl, scale=GLASS, wrap=True):
    """A small conchoidal chip, in tones of `scale`: a scoop bitten into the
    face -- its upper-left wall in shadow, its far wall and rim catching the
    light -- with a ring or two in its floor."""
    for y in range(int(cy - r - 1), int(cy + r + 2)):
        for x in range(int(cx - r - 1), int(cx + r + 2)):
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            d = math.hypot(dx, dy)
            if d > r:
                continue
            f = (dx + dy) / max(d, 0.5)
            if d > r - 1.0:
                t = lvl + (1.6 if f > 0.35 else (-1.0 if f < -0.35 else 0.2))
            else:
                t = lvl - 0.5 + (0.5 if int(d * 0.8) % 2 else 0) + f * 0.5
            gput(img, x, y, t, scale, wrap)


def _seam(img, rnd, x, y, ang, length, core=5.6, wrap=True, turn=0.28, halo=True):
    """A live ember seam a texel wide: a hot core (its brightest knots a step
    up), a dark-ember halo either side that warms the glass without filling
    it. Returns the texels it passed through."""
    p = put if wrap else put_c
    fx, fy = float(x), float(y)
    path = []
    for k in range(length):
        fx += math.cos(ang)
        fy += math.sin(ang)
        ang += rnd.uniform(-turn, turn)
        path.append((int(round(fx)), int(round(fy))))
    if halo:
        for (px, py) in path:
            for (dx, dy) in ((0, -1), (-1, 0), (1, 0), (0, 1)):
                q = (px + dx, py + dy)
                if q in path:
                    continue
                m = level_of(get(img, *q)) if wrap else (
                    level_of(img.getpixel(q)) if 0 <= q[0] < N and 0 <= q[1] < N else None)
                if m is not None and m[0] != "ember":
                    p(img, q[0], q[1], "ember", 1.2 if dy >= 0 else 1.0)
    for k, (px, py) in enumerate(path):
        hot = core + (0.6 if k % 5 == 2 else 0) - (1.2 if k in (0, length - 1) else 0)
        p(img, px, py, "ember", hot)
    return path


def t_nest_glass_hd(seed, hot=False):
    """Obsidian: a face knapped into flake scars. Every scar is a shallow
    scoop lit from its own normal, the arrises between them are a lit texel
    with a crease on their shadow side, a few of them carry a short glare
    (the glare is the material: black rock with no highlight reads as a
    hole), and a couple of small conchoidal chips. The bulk stays purple 0-1."""
    rnd = random.Random(seed)
    img = new(255)
    scars = _Scars(rnd, random.Random(2803))
    _knap(img, rnd, scars, 1.5, 3.4, 3.2, glare=3)
    for _ in range(2):
        _chip_scoop(img, rnd.uniform(0, N), rnd.uniform(0, N), rnd.uniform(2.6, 3.6), 0.8)
    for _ in range(5):                                   # vesicles: a dark pore, lit lip
        x, y = rnd.randrange(N), rnd.randrange(N)
        put(img, x, y, "stone", 0)
        put(img, x + 1, y + 1, "purple", 2)
    if hot:
        _hot_crust(img, rnd)
    return img


def _hot_crust(img, rnd):
    """The crust of a flow that has not finished cooling (281): a skin of
    grey glass on top, and under it the seam that is still running -- a band
    two texels deep, white-hot in knots, with its glow bleeding a step into
    the glass round it -- and heat running down the cracks from it."""
    s = rnd.randrange(1 << 20)
    ys = []
    for x in range(N):
        # the course is the material's (so every variant meets its neighbour
        # at the same height), the wobble the painting's, and nil at the edges
        y0 = 3 + int(round((wave(x, 2811) * 0.5 + 0.5) * 4
                           + (wave(x, s) * 0.5 + 0.5) * 3 * math.sin(math.pi * x / N)))
        ys.append(y0)
        for y in range(y0):
            lvl = (3.2 if y == 0 else 2.2 if y == 1 else 1.4) + (0.6 if (x * 7 + y) % 11 == 0 else 0)
            put(img, x, y, "stone", lvl if y < y0 - 1 else 0.6)
        put(img, x, y0, "ember", 6 if (x + s) % 11 in (0, 1) else 5)
        put(img, x, y0 + 1, "ember", 3.2)
        put(img, x, y0 + 2, "ember", 1.4)
        if (x + s) % 11 == 0:
            put(img, x, y0, "gold", 6)
    for _ in range(rnd.randrange(1, 3)):                 # heat running down a crack
        x = rnd.randrange(N)
        y = ys[x] + 2
        dx = rnd.choice((-1, 1))
        for k in range(rnd.randrange(6, 13)):
            put(img, x, y + k, "ember", 3.8 - k * 0.25)
            put(img, x + 1, y + k, "ember", 1.0)
            if rnd.random() < 0.55:
                x += dx


def t_nest_wall_hd(seed):
    """Background glass: the same knapped face at the dark end -- the scars
    still there, the arrises a single step lit, no glare at all. What is
    behind you in the Nest is a wall you can barely read."""
    rnd = random.Random(seed)
    img = new(255)
    scars = _Scars(rnd, random.Random(2820), ripple=0.06)
    _knap(img, rnd, scars, 1.0, 1.6, 1.8, scale=GLASS_BG)
    for _ in range(10):
        x, y = rnd.randrange(N), rnd.randrange(N)
        put(img, x, y, "stone", 0)
    return img


def t_nest_vein_hd(seed):
    """Background flow: dead glass, flatter than the wall, with live veins
    still running through it -- a texel wide, a dark-ember halo, brightest
    where they knot."""
    rnd = random.Random(seed)
    img = new(255)
    scars = _Scars(rnd, random.Random(2890), ripple=0.05)
    _knap(img, rnd, scars, 1.0, 1.2, 1.6, scale=GLASS_BG)
    # inside the cell, tapering at both ends: 289 is scattered as an accent
    # among plain wall, so a vein that ran off the edge would stop dead there
    for _ in range(3):
        x, y, ang = rnd.uniform(9, 23), rnd.uniform(9, 23), rnd.uniform(0, math.pi)
        core = 3.0 + rnd.uniform(0, 0.6)
        _seam(img, rnd, x, y, ang, rnd.randrange(5, 11), core=core, wrap=False)
        _seam(img, rnd, x, y, ang + math.pi, rnd.randrange(5, 11), core=core, wrap=False)
    return img


def t_nest_crust_hd(seed):
    """Breakable: a bubble in the flow, a skin thin enough to put a boot
    through. A domed lid lit on its upper left, a dark sag at its centre where
    it has already given, and the tell: a ring of hot cracks round it with
    cracks running off it to the edge of the block."""
    rnd = random.Random(seed)
    img = t_nest_glass_hd(seed + 700)
    cx, cy = 15.5 + rnd.uniform(-2, 2), 15.5 + rnd.uniform(-2, 2)
    rx, ry = 9.0, 8.0
    for y in range(N):
        for x in range(N):
            nx, ny = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
            d = nx * nx + ny * ny
            if d > 1.0:
                continue
            facing = -nx - ny
            lvl = 1.0 + facing * 0.9 - (1.0 - d) * 1.4
            put(img, x, y, "purple", lvl)
            if d < 0.12:
                put(img, x, y, "stone", 0)               # where it has given
    for (dx, dy) in ((0, 0), (1, 0), (0, 1)):
        put(img, cx - 4 + dx, cy - 4 + dy, "purple", 5)   # the lid's sheen
    ring = []
    for i in range(72):
        a = 2 * math.pi * i / 72
        ring.append((int(round(cx + math.cos(a) * rx)), int(round(cy + math.sin(a) * ry))))
    for (px, py) in ring:
        put(img, px, py + 1, "ember", 1.6)
    for i, (px, py) in enumerate(ring):
        put(img, px, py, "ember", 6 if i % 9 == 4 else 4.6)
    for ang in (35, 125, 215, 305):                      # cracks off it to the edge
        a = math.radians(ang + rnd.randrange(-20, 21))
        _seam(img, rnd, cx + math.cos(a) * rx, cy + math.sin(a) * ry, a,
              rnd.randrange(6, 10), core=4.2, turn=0.35)
    for ang in range(0, 360, 60):                        # and inward, into the lid
        a = math.radians(ang + rnd.randrange(-12, 13))
        fx, fy = cx + math.cos(a) * rx, cy + math.sin(a) * ry
        for k in range(rnd.randrange(3, 6)):
            fx -= math.cos(a)
            fy -= math.sin(a)
            put(img, fx, fy, "stone", 0)
            put(img, fx + 1, fy, "purple", 2)
    return img


# ============================================================ made things
def t_nest_block_hd(seed):
    """Cut basalt, the only square thing in the Nest: half-offset courses
    sixteen texels high, as the ruins, but the joints glow. Each block is
    dressed -- a lit top arris and left edge, an occluded foot and right side,
    pecked with vesicles (a dark pore with a lit lower lip) and the odd chip
    off a corner. Most joints are a dull ember; a few runs are still live."""
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
                put(img, x, y, "ember", 1.0 + (0.6 if (x * 5 + y * 3) % 13 == 0 else 0))
                continue
            k = (lx // 2, ly // 2, course)
            if k not in jit:
                jit[k] = rnd.uniform(-0.45, 0.45)
            lvl = 1.5 + jit[k] - (lx / 32.0 + ly / 16.0) * 0.4
            if ly == 1:
                lvl += 1.4
            elif ly == 2:
                lvl += 0.6
            elif ly == 15:
                lvl -= 1.0
            elif ly == 14:
                lvl -= 0.5
            if lx == 1:
                lvl += 0.8
            elif lx == 31:
                lvl -= 0.9
            put(img, x, y, "stone", lvl)
    for _ in range(14):                                  # vesicles
        x, y = rnd.randrange(3, 30), rnd.randrange(N)
        if y % 16 < 4 or y % 16 > 13:
            continue
        put(img, x, y, "stone", 0)
        put(img, x, y + 1, "stone", 2.6)
    for _ in range(3):                                   # glassy inclusions, violet
        blob(img, "purple", rnd.uniform(4, 28), rnd.choice((rnd.uniform(5, 11), rnd.uniform(21, 27))),
             rnd.uniform(1.6, 2.8), rnd.uniform(1.2, 2.0), 1.2, lit=1.0, dark=0.6)
    for (bx, by, sx, sy) in ((1, 1, 1, 1), (30, 14, -1, -1), (17, 17, 1, 1)):
        if rnd.random() < 0.7:                           # chipped arrises
            for dy in range(3):
                for dx in range(3 - dy):
                    put(img, bx + dx * sx, by + dy * sy, "stone", 0.6)
            put(img, bx + 3 * sx, by, "stone", 3.2)
    for _ in range(2):                                   # one live run of joint
        y = rnd.choice((0, 16))
        x = rnd.randrange(N)
        run = rnd.randrange(5, 11)
        for k in range(run):
            put(img, x + k, y, "ember", 5 if 0 < k < run - 1 else 3.6)
            shift(img, x + k, y + 1, +1)                 # its glow on the block under it
            if k % 4 == 1:
                put(img, x + k, y, "ember", 6)
    return img


def t_nest_plate_hd(seed):
    """Riveted plate, as the Nest builds it: iron that has been in a furnace
    long enough to scale. A bevelled panel (lit top and left, occluded foot
    and right), two lapped seams across it -- each the upper plate's lit lip
    over its own shadow -- domed rivets at the corners and along the seams,
    heat scale blooming in ember, and the temper colour the furnace left at
    the plate's foot. The one bright face in the world, and a bounded one."""
    rnd = random.Random(seed)
    img = fill(new(255), "metal", 2.0, rnd, grain=0.32)
    for y in range(N):
        for x in range(N):
            if y < 2 or x < 2:
                shift(img, x, y, +1 if (y == 0 or x == 0) else +1)
            if y == 0 or x == 0:
                shift(img, x, y, +1)
            if y >= N - 2 or x >= N - 2:
                shift(img, x, y, -1)
            if y == N - 1 or x == N - 1:
                put(img, x, y, "metal", 0)
    for sy in (11, 21):                                  # lapped seams
        for x in range(1, N - 1):
            put(img, x, sy - 1, "metal", 3.6)
            put(img, x, sy, "metal", 0.6)
            put(img, x, sy + 1, "metal", 1.4)
    for _ in range(4):                                   # mill scale, flaking: rust brown
        cx, cy = rnd.uniform(4, N - 4), rnd.uniform(4, N - 4)
        for _k in range(3):
            ellipse(img, "gold", cx + rnd.uniform(-2.5, 2.5), cy + rnd.uniform(-1.2, 1.2),
                    rnd.uniform(1.2, 2.4), rnd.uniform(0.8, 1.4), 1, wrap=False)
        put_c(img, int(cx) - 1, int(cy) - 1, "gold", 2)          # a flake's lit edge
        put_c(img, int(cx) + 1, int(cy) + 1, "metal", 1)         # bare iron under it
    for x in range(2, N - 2):                            # temper at the foot
        if (x * 3) % 7 < 4:
            put(img, x, N - 3, "purple", 2)
    for (rx, ry) in ((4, 4), (27, 4), (4, 27), (27, 27), (15, 15), (15, 25)):
        for (dx, dy, lvl) in ((-1, -1, 5), (0, -1, 5), (-1, 0, 5), (0, 0, 4),
                              (1, 0, 3), (0, 1, 3), (1, 1, 1), (1, -1, 4), (-1, 1, 3)):
            put_c(img, rx + dx, ry + dy, "metal", lvl)
        put_c(img, rx - 1, ry - 1, "metal", 6)
        put_c(img, rx + 2, ry + 1, "metal", 1)
        put_c(img, rx + 1, ry + 2, "metal", 1)
    return img


def t_nest_flue_hd(seed):
    """A flue standing behind the play field: a column of glass, round --
    lit on its left, a barrel falloff, a dark flank and the shadow it casts --
    with collars of seam where it was built up in courses, and the heat still
    running up its inside: a wandering ember thread with a dark-ember glow,
    seen through the glass. Tiles vertically."""
    rnd = random.Random(seed)
    img = fill(new(255), "purple", 0.25, rnd, grain=0.2)
    x0, wdt = 4, 24
    for x in range(x0, x0 + wdt):
        t = (x - x0 + 0.5) / float(wdt)
        bar = math.sin(math.pi * t)
        for y in range(N):
            lvl = 0.3 + bar * 1.1 + (0.9 if t < 0.25 else 0) - (0.8 if t > 0.82 else 0)
            put(img, x, y, "stone", lvl + rnd.uniform(-0.18, 0.18))
    for y in range(N):
        put(img, x0, y, "stone", 0.4)
        put(img, x0 + 1, y, "stone", 2.6)
        put(img, x0 + wdt - 1, y, "stone", 0)
        put(img, x0 + wdt, y, "purple", 0)
        put(img, x0 + wdt + 1, y, "purple", 0)
    for cy in (9, 25):                                   # collars
        for x in range(x0, x0 + wdt):
            put(img, x, cy, "stone", 0)
            put(img, x, cy + 1, "stone", 2.2 if x < x0 + wdt * 0.7 else 1.2)
    ph = rnd.uniform(0, 2 * math.pi)
    cx0 = x0 + wdt / 2.0
    for y in range(N):                                   # the heat inside it
        cx = cx0 + 2.4 * math.sin(2 * math.pi * y / N + ph) + 0.8 * math.sin(4 * math.pi * y / N)
        xi = int(round(cx))
        if (y + int(ph * 5)) % 7 == 3:
            continue                                     # the thread breaks
        for dx in (-1, 1):
            if level_of(get(img, xi + dx, y))[0] == "stone":
                put(img, xi + dx, y, "ember", 0.8)
        put(img, xi, y, "ember", 2.6 + (1 if (y + int(ph * 5)) % 7 == 0 else 0))
    for _ in range(4):                                   # glare down the lit side
        y = rnd.randrange(N)
        for k in range(rnd.randrange(2, 5)):
            put(img, x0 + 3, y + k, "stone", 3.4)
    return img


# ============================================================ inked tiles
def t_nest_ledge_hd(seed):
    """One-way ledge: a slab of cooled flow eight texels thick. Its top is a
    glass arris catching the light with glare in short runs, the face is two
    flake scars deep, and its underside is still hot -- a glow along the foot
    with drips of it hanging. Inked by the kit."""
    rnd = random.Random(seed)
    img = new(0)
    for x in range(N):
        for y, lvl in enumerate((3.4, 2.4, 1.6, 1.2, 1.0, 0.8, 0.6)):
            ramp = "stone" if y < 2 else "purple"
            put_c(img, x, y, ramp, lvl + (rnd.uniform(-0.3, 0.3) if y > 1 else 0))
    for sx in (10, 22):                                  # where the slab cracked
        for y in range(7):
            put_c(img, sx, y, "stone", 0)
            put_c(img, sx + 1, y, "purple", 2.2 if y > 1 else 3)
    s = rnd.randrange(1 << 20)
    for x in range(N):                                   # the scars along its face
        d = 3 + int(round((wave(x, s, period=16) * 0.5 + 0.5) * 2))
        put_c(img, x, d, "purple", 2.0)
        put_c(img, x, d + 1, "purple", 0.4)
    x = 0
    while x < N:                                         # glare along the top
        if rnd.random() < 0.2:
            for k in range(rnd.randrange(2, 5)):
                put_c(img, x + k, 0, "purple", 6 if k == 1 else 5)
            x += 7
        else:
            x += 1
    for x in range(N):                                   # the heat underneath
        w = wave(x, s + 1)
        if w > -0.35:
            put_c(img, x, 6, "ember", 3.4 + (1.2 if w > 0.6 else 0))
            put_c(img, x, 5, "ember", 1.4)
    for dx in rnd.sample(range(3, N - 4), 2):            # a drip of it gathering
        put_c(img, dx, 7, "ember", 4.4)
    return img


def t_nest_shard_hd(seed):
    """The hazard: obsidian shards standing point-up out of a live flow.
    Each shard is two flat faces meeting on a lit central arris -- the left
    face catching the light, the right in shadow -- with a glare down the
    arris and heat glowing up from its root to a white-hot point. The flow
    they stand in is molten: a crusted skin with the lava showing through it
    in a seam, so the whole strip says "burns" before it says "rock"."""
    rnd = random.Random(seed)
    img = new(0)
    s = rnd.randrange(1 << 20)
    for x in range(N):                                   # the flow
        put_c(img, x, 25, "ember", 3.6 if (x + s) % 6 else 4.6)
        put_c(img, x, 26, "ember", 5 if (x + s) % 7 else 6)
        put_c(img, x, 27, "ember", 4.6)
        put_c(img, x, 28, "ember", 3.4)
        put_c(img, x, 29, "ember", 2.2)
        put_c(img, x, 30, "purple", 0.6)
    for _ in range(4):                                   # crust plates floating on it
        x0 = rnd.randrange(N)
        for k in range(rnd.randrange(3, 6)):
            put_c(img, (x0 + k) % N, 27, "stone", 1.6 if k == 0 else 0.8)
            put_c(img, (x0 + k) % N, 28, "stone", 0.4)
    for (cx, w) in ((5.5, 5.0), (15.5, 6.0), (25.5, 5.2)):
        top = 4 + rnd.randrange(3)
        for y in range(top, 27):
            t = (y - top) / float(26 - top)
            half = max(0.6, t * w)
            for x in range(int(math.floor(cx - half)), int(math.ceil(cx + half)) + 1):
                u = (x + 0.5 - cx) / half
                if abs(u) > 1.0:
                    continue
                if u < -0.08:
                    lvl = 2.2 + (1 - t) * 0.8 + (0.7 if u < -0.7 else 0)
                    ramp = "purple"
                elif u < 0.12:
                    lvl = 4.6                            # the arris
                    ramp = "purple"
                else:
                    lvl = 0.8 - u * 0.6
                    ramp = "purple"
                put_c(img, x, y, ramp, lvl)
            if y > 19:                                   # heat up from the root
                put_c(img, int(cx) - 1, y, "ember", 2.4 + (y - 19) * 0.3)
        for k, lvl in enumerate((6.0, 6.0, 5.4, 4.6, 3.8)):   # the hot point
            put_c(img, int(cx), top + k, "ember", lvl)
            if k:
                put_c(img, int(cx) - 1, top + k, "ember", lvl - 1.2)
        put_c(img, int(cx), top, "gold", 6)
        for k in range(5, 10):                           # glare down the arris
            put_c(img, int(cx) - 1, top + k, "purple", 5.4 if k % 2 else 4.6)
    return img


def t_nest_chain_hd(seed):
    """The climbable: a chain of the Nest's own iron. Links alternate face-on
    (an oval ring, lit on its upper left, its hole showing what is behind)
    and edge-on (a bar), eight texels apart, so a column of tiles is one
    chain. Hot where it has hung in the updraught: a few links glow."""
    rnd = random.Random(seed)
    img = new(0)
    cx = 16.0
    hot = {rnd.randrange(4), rnd.randrange(4)}
    for j, cy in enumerate((0, 16, 32)):                 # face-on rings (wrapping)
        for y in range(int(cy - 6), int(cy + 6)):
            for x in range(int(cx - 5), int(cx + 5)):
                nx, ny = (x + 0.5 - cx) / 4.6, (y + 0.5 - cy) / 5.8
                d = nx * nx + ny * ny
                if d > 1.0 or d < 0.28:
                    continue
                facing = -nx - ny
                lvl = 2.3 + facing * 1.3 + (0.5 if d > 0.75 else 0)
                if 0 <= y < N:
                    put_c(img, x, y, "metal", lvl)
    for cy in (8, 24):                                   # edge-on bars through them
        for y in range(cy - 7, cy + 7):
            put_c(img, 15, y, "metal", 3.6)
            put_c(img, 16, y, "metal", 2.4)
            put_c(img, 17, y, "metal", 1.0)
        put_c(img, 15, cy - 7, "metal", 5)
        put_c(img, 16, cy + 6, "metal", 0.6)
    for k in hot:                                        # bars that hold the heat
        cy = 8 + 16 * (k % 2) + (k // 2) * 3 - 3
        for y in range(cy, cy + 3):
            put_c(img, 16, y, "ember", 3.4 if y == cy + 1 else 2.6)
            put_c(img, 17, y, "ember", 1.4)
    return img


# ============================================================ edge dressers
@dresser("dress_nest")
def dress_nest_hd(img, mask, rnd):
    """Glass: an exposed edge is a fracture. It is knapped -- a few scallops
    bitten out of the arris, each with a lit far lip -- and it glares in short
    runs rather than glowing; the heat is trapped under the overhang, a glow
    along the underside with drips hanging off it."""
    for side, bit in (("top", BIT_N), ("left", BIT_W), ("right", BIT_E)):
        if mask & bit:
            continue
        for _ in range(2):                               # scallops off the arris
            i = rnd.randrange(3, N - 8)
            w = rnd.randrange(4, 7)
            for j in range(w):
                d = max(1, int(round(2.4 * math.sin(math.pi * (j + 0.5) / w))))
                for k in range(d):
                    x, y = side_xy(side, k, i + j)
                    put_c(img, x, y, "purple", 0.4 if k < d - 1 else 1.2)
                x, y = side_xy(side, d, i + j)
                put_c(img, x, y, "purple", 3.2 if side in ("top", "left") else 1.8)
        for _ in range(2):                               # glare in short runs
            i = rnd.randrange(2, N - 5)
            for j in range(rnd.randrange(2, 4)):
                x, y = side_xy(side, 0, i + j)
                put_c(img, x, y, "purple", 5 if side != "right" else 4)
    if not mask & BIT_S:                                 # heat under the lip
        # just above the underside: the refit rim owns the last four rows
        # and sets them to the lip's dark step, which is the overhang itself
        s = rnd.randrange(1 << 20)
        for x in range(N):
            w = wave(x, s)
            if w > -0.3:
                put_c(img, x, N - 5, "ember", 3.6 + (1.2 if w > 0.55 else 0))
                put_c(img, x, N - 6, "ember", 1.4)
        for _ in range(2):                               # a crack the heat comes up
            x = rnd.randrange(3, N - 3)
            for k in range(rnd.randrange(3, 7)):
                put_c(img, x, N - 6 - k, "ember", 3.2 - k * 0.35)


@dresser("dress_nest_hot")
def dress_nest_hot_hd(img, mask, rnd):
    """The cooling-crust tile: as above, and wherever a side is exposed the
    seam runs out of it and down the face."""
    dress_nest_hd(img, mask, rnd)
    for side, bit in (("left", BIT_W), ("right", BIT_E)):
        if mask & bit:
            continue
        run = rnd.randrange(5, 12)
        for y in range(3, 3 + run):
            x, py = side_xy(side, 2, y)
            put_c(img, x, py, "ember", 5.2 - (y - 3) * 0.3)
            x, py = side_xy(side, 3, y)
            put_c(img, x, py, "ember", 1.6)
            x, py = side_xy(side, 1, y)
            put_c(img, x, py, "ember", 2.2)


@dresser("dress_nest_bg")
def dress_nest_bg_hd(img, mask, rnd):
    """Background glass catches only a little light on an exposed lip."""
    if not mask & BIT_N:
        x = 0
        while x < N:
            if rnd.random() < 0.28:
                for k in range(rnd.randrange(2, 6)):
                    put_c(img, x + k, 0, "stone", 1.6)
                    put_c(img, x + k, 1, "purple", 1)
                x += 6
            else:
                x += 1


# ============================================================ accents
def glass_flake(img, rnd):
    """A conchoidal flake taken off the lip: the scoop in shadow with its
    rings, a bright edge where it broke, a sliver of glare."""
    x = rnd.uniform(6, N - 10)
    _chip_scoop(img, x, 2.5, 4.2, 0.8, wrap=False)
    for k in range(5):
        put_c(img, int(x) - 2 + k, 0, "purple", 6 if k < 2 else 5)
        put_c(img, int(x) - 2 + k, 1, "stone", 0)


def ember_seam(img, rnd):
    """A seam broken out at the top of the block: a short hot run, a crack
    of it leading down, and its glow."""
    x = rnd.randrange(5, N - 14)
    for k in range(9):
        y = 2 + (1 if 2 < k < 6 else 0)
        put_c(img, x + k, y + 1, "ember", 1.8)
        put_c(img, x + k, y, "ember", 6 if k == 4 else 5)
        put_c(img, x + k, y - 1, "stone", 0)
    for k in range(5):
        put_c(img, x + 4 + (k // 2), 4 + k, "ember", 4.2 - k * 0.4)


ACCENTS["nest"] = [glass_flake, ember_seam]
CAP_ACCENTS[281] = [ember_seam, glass_flake]


# ============================================================ decorations
@decoration("d_ember_seam")
def d_ember_seam_hd(img, rnd):
    """One live seam crossing the cell: a texel wide with its dark-ember halo,
    a hot knot every few texels, and a short branch."""
    # started near the middle and run both ways, so it crosses the cell
    # rather than clipping to a stub at an edge
    x, y, ang = rnd.uniform(10, 22), rnd.uniform(10, 22), rnd.uniform(0, math.pi)
    path = _seam(img, rnd, x, y, ang, rnd.randrange(10, 17), core=4.4, wrap=False)
    path += _seam(img, rnd, x, y, ang + math.pi, rnd.randrange(8, 15), core=4.4, wrap=False)
    if len(path) > 8 and rnd.random() < 0.7:
        bx, by = path[len(path) // 2]
        _seam(img, rnd, bx, by, rnd.uniform(0, math.pi), rnd.randrange(5, 10), core=3.4,
              wrap=False)
    return img


@decoration("d_chain_hang")
def d_chain_hang_hd(img, rnd):
    """A length of chain left hanging: links alternating face-on and edge-on,
    lit on the left, ending in a loose link."""
    x = rnd.randrange(5, N - 6)
    run = rnd.randrange(14, N + 1)
    for y in range(0, run, 6):
        if (y // 6) % 2 == 0:                            # face-on
            for (dx, dy, lvl) in ((-1, 0, 3.6), (-1, 1, 3.4), (-1, 2, 3.2), (-1, 3, 3.0),
                                  (2, 0, 2.0), (2, 1, 1.8), (2, 2, 1.6), (2, 3, 1.4),
                                  (0, -1, 3.8), (1, -1, 3.0), (0, 4, 2.0), (1, 4, 1.4)):
                put_c(img, x + dx, y + dy + 1, "metal", lvl)
        else:                                            # edge-on
            for k in range(-1, 6):
                put_c(img, x, y + k, "metal", 3.8)
                put_c(img, x + 1, y + k, "metal", 1.8)
            put_c(img, x, y - 1, "metal", 5)
    return img


# ============================================================ registrations
# id, the seed its T_AT line in tiles.py uses (also its V spec's seeds[0]).
tile(280, 2801)(t_nest_glass_hd)
tile(281, 2811)(lambda s: t_nest_glass_hd(s, hot=True))
tile(282, 2821)(t_nest_wall_hd)
tile(283, 2831)(t_nest_block_hd)
# 284: the see-through void, painted empty at both scales; nothing to register.
tile(285, 2851)(t_nest_flue_hd)
tile(286, 2861)(t_nest_ledge_hd)
tile(287, 2871)(t_nest_shard_hd)
tile(288, 2881)(t_nest_chain_hd)
tile(289, 2891)(t_nest_vein_hd)
tile(290, 2901)(t_nest_plate_hd)
tile(291, 2911)(t_nest_crust_hd)
