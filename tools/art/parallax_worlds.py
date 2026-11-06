"""The parallax backdrops, Kaya Refit phase 3: three depth planes per world
(sky = far, far = mid, near = near) plus the near-foreground strip, painted
with slack in both directions for the scrolling camera.

What changed from the phase-3 art-direction planes, and why:

* **Size.** Every strip used to be exactly one screen, which was right for the
  screen flip and wrong for a follow camera: vertically it had to be locked to
  the view, and a near plane scrolling at 0.58 repeated its 400 px every two
  thirds of a screen. data/parallax.json now sizes each strip -- wider than one
  level's worth of its own travel, and taller by its factor times one screen of
  vertical travel -- and src/world/parallax_bg.gd maps the vertical slack
  across the level. So a strip is composed for *every* 240-row window down its
  height: the top rows are what you see from the top of a level, the bottom
  rows (the horizon, the ground) what you see from its floor.
* **Detail.** The 40 px Kaya is drawn a pixel at a time; blobs of crown behind
  her read as an older game. Foliage here is built from individual leaves,
  trunks have bark and buttress roots, clouds have lit tops and flat bases,
  stone is laid in courses. The detail is in *shape*, not in contrast: each
  plane still renders through a narrow window of its ramp (backdrops.Plane), so
  more drawing cannot buy a plane more contrast than its depth allows.
* **Depth by value and saturation.** No new ramps -- the palette test pins the
  ramp count, and four agents adding ramps would collide on it. Distance is
  carried by which ramp a plane is painted on instead: the furthest plane of a
  daylight world sits on the cool, grey `stone`/`water`/`metal` ramps, the
  middle plane on the material's own ramp high in its window, the near plane
  low and dark on it. The dark worlds run the other way: the far plane is the
  darkest, and the near plane carries the (still dim) colour.

Every brush wraps in x through Plane.set, so every strip tiles seamlessly.
"""
import json
import math
import os
import random

from .backdrops import (Plane, cloud, glow, grain, horizon_haze, mist, ridge,
                        shafts, sky_path, spires, vband)
from .palette import ROOT, bayer_on

_SPEC = json.load(open(os.path.join(ROOT, "data", "parallax.json")))
VIEW_W, VIEW_H = _SPEC["view"]
DESIGN_H = _SPEC["design_level_h"]


def size(plane):
    """(w, h) of a plane's strip, from data/parallax.json."""
    s = _SPEC["planes"][plane]
    return int(s["width"]), VIEW_H + int(round(s["vertical"] * (DESIGN_H - VIEW_H)))


def plane(name, ramp, window, **kw):
    w, h = size(name)
    return Plane(ramp, window, w=w, h=h, **kw)


# ---------------------------------------------------------------- brushes
def _clamp(v):
    return max(0.0, min(1.0, v))


def leaf(p, x, y, ang, length, half, v, ramp=None, rib=True):
    """One pointed leaf from (x, y) along `ang` (degrees, 0 = right, 90 =
    down). Lit on whichever half faces the upper-left light; a darker midrib
    when it is wide enough to have one. At 1x a leaf is 4-12 px: this is the
    unit the foliage is drawn in, so a crown reads as leaves rather than as a
    blob."""
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    # the leaf's normal on its "left" side, and whether that side faces the light
    nx, ny = sa, -ca
    left_lit = (nx * -1 + ny * -1) > 0
    r = int(length + half + 2)
    for yy in range(int(y) - r, int(y) + r + 1):
        for xx in range(int(x) - r, int(x) + r + 1):
            dx, dy = xx + 0.5 - x, yy + 0.5 - y
            u = dx * ca + dy * sa
            w = dx * nx + dy * ny
            if u < 0 or u > length:
                continue
            hw = half * math.sin(math.pi * u / length) ** 0.75
            if abs(w) > hw:
                continue
            if rib and half >= 1.6 and abs(w) < 0.5 and 1 < u < length - 1:
                s = -0.16
            elif (w > 0) == left_lit:
                s = 0.20 if abs(w) > hw * 0.35 else 0.10
            else:
                s = -0.14
            p.set(xx, yy, _clamp(v + s), ramp)


def leaf_cluster(p, cx, cy, r, v, seed, ramp=None, n=None, size_=(5, 9),
                 droop=35.0):
    """A spray of leaves radiating from a hidden stem: the back ones darker,
    the front ones lighter, so a cluster has volume without an outline."""
    rnd = random.Random(seed)
    n = n or max(6, int(r * 1.6))
    items = []
    for i in range(n):
        a = rnd.uniform(0, 360)
        d = rnd.uniform(0.0, r * 0.7)
        x = cx + math.cos(math.radians(a)) * d
        y = cy + math.sin(math.radians(a)) * d * 0.7
        ang = a + rnd.uniform(-25, 25)
        ang += droop * math.cos(math.radians(ang)) ** 2 * (1 if 90 < ang % 360 < 270 else 1)
        items.append((y, x, ang, rnd.uniform(*size_), rnd.uniform(1.4, 2.4)))
    items.sort()                                   # top first: lower leaves overlap
    for k, (y, x, ang, L, hw) in enumerate(items):
        depth = (k / float(max(1, n - 1)))         # 0 back .. 1 front
        facing = -(x - cx) - (y - cy)              # upper-left of the cluster is lit
        lift = 0.22 * max(-1.0, min(1.0, facing / max(1.0, r)))
        leaf(p, x, y, ang, L, hw, _clamp(v - 0.12 + 0.18 * depth + lift), ramp)


def crown_of_leaves(p, cx, cy, rx, ry, v, seed, ramp=None, size_=(5, 9), density=1.0):
    """A tree crown as a dome of leaf clusters: a dark core first (the shade
    inside the crown, which is what stops it reading as a cut-out), then
    clusters over it, lit toward the upper left."""
    rnd = random.Random(seed)
    for y in range(int(cy - ry), int(cy + ry) + 1):
        for x in range(int(cx - rx), int(cx + rx) + 1):
            dx, dy = (x - cx) / float(rx), (y - cy) / float(ry)
            if dx * dx + dy * dy <= 0.62:
                p.set(x, y, _clamp(v - 0.24), ramp)
    count = int((rx * ry) / 26.0 * density) + 4
    for i in range(count):
        a = rnd.uniform(0, 2 * math.pi)
        d = math.sqrt(rnd.random()) * 0.85
        x = cx + math.cos(a) * rx * d
        y = cy + math.sin(a) * ry * d
        facing = (-(x - cx) / rx - (y - cy) / ry) * 0.5
        leaf_cluster(p, x, y, rnd.uniform(4, 8), _clamp(v + 0.10 * facing), seed * 31 + i,
                     ramp, size_=size_)


def bark_trunk(p, x, top, bottom, w, v, seed, ramp=None, lean=0.0, wobble=0.0,
               roots=0, moss=None, moss_v=0.4, taper=1.0):
    """A trunk with a round body: lit shoulder, core, shadow side, a dark rim;
    bark grooves that wander down it; knots; and, if `roots` > 0, buttress roots
    flaring out over the last `roots` rows -- the shape that says rainforest.
    `taper` is the trunk's width at `top` as a fraction of `w` at `bottom`."""
    rnd = random.Random(seed)
    grooves = [(rnd.uniform(0.15, 0.9), rnd.uniform(0, 6.3), rnd.uniform(18, 46))
               for _ in range(max(2, w // 3))]
    knots = [(rnd.randrange(max(top, 0), bottom), rnd.uniform(0.3, 0.7))
             for _ in range(max(1, (bottom - top) // 90))]
    mosses = [(rnd.randrange(max(top, 0), bottom), rnd.randrange(6, 20))
              for _ in range(max(1, (bottom - top) // 70))] if moss else []
    for y in range(max(0, top), min(p.h, bottom)):
        cx = x + lean * (y - top) + wobble * math.sin(y / 37.0 + seed)
        extra = 0.0
        if roots and y > bottom - roots:
            t = (y - (bottom - roots)) / float(roots)
            extra = (t ** 2.2) * w * 1.3
        wy = w * (taper + (1.0 - taper) * (y - top) / float(max(1, bottom - top)))
        left, right = cx - extra * 0.8, cx + max(1.0, wy) + extra
        span = right - left
        for xx in range(int(math.floor(left)), int(math.ceil(right))):
            t = (xx + 0.5 - left) / span
            if t < 0.0 or t > 1.0:
                continue
            if t < 0.07 or t > 0.93:
                s = -0.36
            elif t < 0.24:
                s = 0.30
            elif t < 0.42:
                s = 0.12
            elif t < 0.70:
                s = 0.0
            else:
                s = -0.20
            # buttress: the fins are separated by dark folds
            if extra > 2:
                fold = math.sin((t * span) / 5.0 + seed)
                if fold > 0.82:
                    s -= 0.26
            else:
                for (gx, ph, per) in grooves:
                    g = gx + 0.05 * math.sin(y / per + ph)
                    if abs(t - g) < 0.5 / span + 0.02:
                        s -= 0.20
                    elif 0 < g - t < 1.5 / span + 0.02 and t < 0.6:
                        s += 0.06
            for (ky, kt) in knots:
                if abs(y - ky) <= 1 and abs(t - kt) < 1.5 / span:
                    s = -0.32
                elif abs(y - ky - 1.5) <= 0.5 and abs(t - kt) < 1.0 / span:
                    s = 0.22
            p.set(xx, y, _clamp(v + s), ramp)
            if moss:
                for (my, ml) in mosses:
                    if my <= y < my + ml and t < 0.45 and bayer_on(xx, y, 0.6 - t):
                        p.set(xx, y, _clamp(moss_v + (0.18 if t < 0.25 else 0.0)), moss)


def vine(p, x, y0, length, v, seed, ramp=None, leaf_ramp=None, leaf_v=None,
         every=7, curl=True):
    """A hanging liana: a two-pixel stem swinging gently as it falls, small
    leaves off it in pairs, and a curl at the bottom."""
    rnd = random.Random(seed)
    lv = v + 0.15 if leaf_v is None else leaf_v
    xx = float(x)
    amp = rnd.uniform(0.5, 1.4)
    last = (x, y0)
    for i in range(length):
        y = y0 + i
        if y >= p.h:
            return
        xx = x + amp * 4 * math.sin(i / 23.0 + seed) + 1.6 * math.sin(i / 7.0 + seed * 2)
        p.set(int(xx), y, _clamp(v + 0.12), ramp)
        p.set(int(xx) + 1, y, _clamp(v - 0.14), ramp)
        last = (xx, y)
        if i > 4 and i % every == every // 2:
            side = 1 if (i // every) % 2 else -1
            leaf(p, xx + (2 if side > 0 else -0.5), y, 40 if side > 0 else 140,
                 rnd.uniform(4, 7), rnd.uniform(1.3, 2.0), _clamp(lv), leaf_ramp or ramp,
                 rib=False)
    if curl:
        cx, cy = last
        for a in range(0, 300, 20):
            r = 2.6 - a / 200.0
            p.set(int(cx + 1 + math.cos(math.radians(a)) * r),
                  int(cy + 2 + math.sin(math.radians(a)) * r), _clamp(v), ramp)


def frond(p, x, y, ang, length, v, seed, ramp=None, leaflet=6.0, droop=0.9):
    """A fern or palm frond: a curving rachis with leaflets either side,
    shrinking toward the tip."""
    rnd = random.Random(seed)
    a = math.radians(ang)
    px, py = float(x), float(y)
    n = int(length)
    for i in range(n):
        t = i / float(n)
        a += droop * 0.035 * (1 if math.cos(a) >= 0 else -1)
        px += math.cos(a)
        py += math.sin(a)
        p.set(int(px), int(py), _clamp(v - 0.06), ramp)
        if i % 3 == 1 and t > 0.05:
            L = leaflet * (1.0 - t * 0.8) + rnd.uniform(-0.5, 0.5)
            for side in (-1, 1):
                la = math.degrees(a) + side * (62 - 20 * t) + 18
                leaf(p, px, py, la, max(2.0, L), max(1.0, 1.6 - t), _clamp(v + 0.04 * side),
                     ramp, rib=False)


def cumulus(p, cx, cy, rx, ry, v, seed, ramp=None, base_dark=0.26):
    """A cumulus: round lumps along a flat base, lit on top-left, the base in
    shade. Unlike backdrops.cloud, which is a smear, this is an object with a
    top and a bottom."""
    rnd = random.Random(seed)
    lumps = []
    for i in range(int(rx / 6) + 3):
        ox = rnd.uniform(-rx, rx)
        k = 1.0 - (ox / rx) ** 2
        r = ry * (0.45 + 0.6 * k) * rnd.uniform(0.7, 1.05)
        lumps.append((cx + ox, cy - r * 0.35, r))
    for (lx, ly, r) in lumps:
        for y in range(int(ly - r), int(min(cy + 2, ly + r)) + 1):
            for x in range(int(lx - r), int(lx + r) + 1):
                dx, dy = (x + 0.5 - lx) / r, (y + 0.5 - ly) / r
                d = dx * dx + dy * dy
                if d > 1.0:
                    continue
                facing = -dx * 0.6 - dy
                s = 0.24 if facing > 0.55 else (0.08 if facing > 0.0 else -0.08)
                if y > cy - 2:
                    s = -base_dark * 0.6
                if d > 0.86 and facing > 0.4:
                    s = 0.32                          # silver rim on the lit edge
                p.set(x, y, _clamp(v + s), ramp)


def masonry(p, x0, y0, w, h, v, seed, ramp=None, course=7, block=(10, 18),
            chip=0.12):
    """Dressed stone laid in courses: lit top edge per course, a dark mortar
    line under it, staggered joints, and a few chipped blocks."""
    rnd = random.Random(seed)
    y = y0
    row = 0
    while y < y0 + h:
        ch = min(course, y0 + h - y)
        x = x0 - (rnd.randrange(block[0]) if row % 2 else 0)
        while x < x0 + w:
            bw = rnd.randint(*block)
            tone = v + rnd.uniform(-0.06, 0.06)
            broken = rnd.random() < chip
            for yy in range(y, y + ch):
                for xx in range(max(x, x0), min(x + bw, x0 + w)):
                    if yy == y + ch - 1 or xx == x + bw - 1:
                        s = -0.28                      # mortar
                    elif yy == y or xx == x:
                        s = 0.18                       # arris
                    else:
                        s = 0.0
                    if broken and xx > x + bw - 5 and yy < y + 3:
                        continue
                    p.set(xx, yy, _clamp(tone + s), ramp)
            x += bw
        y += ch
        row += 1


def peak(p, cx, base, h, half, v, seed, ramp=None, snow=None, snow_v=0.8,
         snow_from=0.78):
    """A mountain with structure: a lit west face and a shadowed east face
    split along a ridge that wanders, gullies cut down both, and a snow cap
    that follows the gullies down rather than ending on a ruled line."""
    rnd = random.Random(seed)
    ridge_x = [0.0]
    for i in range(h):
        ridge_x.append(ridge_x[-1] + rnd.uniform(-0.6, 0.6))
    gullies = [rnd.uniform(-0.8, 0.8) for _ in range(5)]
    for y in range(max(0, base - h), min(p.h, base)):
        t = (base - y) / float(h)                       # 0 foot .. 1 summit
        k = base - y
        rx = cx + ridge_x[min(k, h)] * 0.6
        wl = half * (1.0 - t) * (1.0 + 0.08 * math.sin(y / 5.0 + seed))
        wr = half * (1.0 - t) * (1.0 + 0.08 * math.sin(y / 6.0 + seed * 2))
        for x in range(int(rx - wl), int(rx + wr) + 1):
            u = (x - rx) / max(1.0, (wl if x < rx else wr))
            s = 0.20 if u < 0 else -0.18
            if u < -0.85 or (u < 0 and abs(u) < 0.08):
                s += 0.08
            for g in gullies:
                gx = g + 0.08 * math.sin(y / 9.0 + g * 10)
                if abs(u - gx) < 0.05 + 0.03 * (1 - t):
                    s -= 0.16
            if snow and (t > snow_from + 0.05 * math.sin(x / 3.0 + seed)
                         or (t > snow_from - 0.18 and any(abs(u - g) < 0.06 for g in gullies))):
                p.set(x, y, _clamp(snow_v + (0.14 if u < 0 else -0.12)), snow)
            else:
                p.set(x, y, _clamp(v + s), ramp)


def bubbles(p, n, seed, v, ramp=None, y_range=None):
    rnd = random.Random(seed)
    lo, hi = y_range or (0, p.h)
    for _ in range(n):
        x, y = rnd.randrange(p.w), rnd.randrange(lo, hi)
        r = rnd.choice((0, 0, 1, 1, 2))
        if r == 0:
            p.set(x, y, v, ramp)
            continue
        for a in range(0, 360, 30):
            p.set(int(x + math.cos(math.radians(a)) * r), int(y + math.sin(math.radians(a)) * r),
                  _clamp(v - 0.1), ramp)
        p.set(x - 1, y - 1, _clamp(v + 0.2), ramp)


def treeline(p, base_y, v, seed, ramp=None, bump=(5, 12), depth=60, spacing=7,
             crest=0.16, fade=0.22, amp=10):
    """A far forest edge seen as one mass: the crest is many small crowns
    (bumps of 5-12 px), each lit on its upper left with a shadow notch where
    it meets the next, and the body darkens with depth into the band. At a
    distance a forest has no leaves, only crowns -- this is the brush for
    that, where leaf_cluster is the brush for near."""
    rnd = random.Random(seed)
    bumps = []
    x = 0
    while x < p.w:
        r = rnd.randint(*bump)
        bumps.append((x, base_y + rnd.randint(-amp, amp // 2) + int(amp * 0.6 * math.sin(x / 47.0 + seed)), r))
        x += rnd.randint(spacing - 2, spacing + 4)
    top = [p.h] * p.w
    owner = [None] * p.w
    for (cx, cy, r) in bumps:
        for dx in range(-r, r + 1):
            px = (cx + dx) % p.w
            t = cy - int((r * r - dx * dx) ** 0.5)
            if t < top[px]:
                top[px] = t
                owner[px] = (cx, cy, r, dx)
    for px in range(p.w):
        if top[px] >= p.h:
            continue
        cx, cy, r, dx = owner[px]
        for py in range(max(0, top[px]), min(p.h, base_y + depth)):
            d = py - top[px]
            dy = py - cy
            s = 0.0
            if d < r:                                       # on the crown's dome
                facing = (-dx - dy) / float(r)
                s = crest if facing > 0.5 else (-0.06 if facing < -0.4 else 0.04)
                if d < 1:
                    s += 0.06
            s -= fade * max(0.0, py - base_y) / float(max(1, depth))
            p.set(px, py, _clamp(v + s), ramp)


def forest_rank(p, horizon, v, seed, ramp=None, count=12, crown=(10, 22),
                rise=(8, 60), trunk_w=1, body=40, body_fade=0.2):
    """One rank of distant forest: separate trees whose crowns stand at very
    different heights over a continuous understorey. Each crown is a knot of
    round lumps lit on the upper left; each trunk is a line down into the
    body. The body starts at `horizon` and darkens over `body` rows."""
    rnd = random.Random(seed)
    trees = []
    for i in range(count):
        x = int(i * p.w / float(count) + rnd.uniform(-0.4, 0.4) * p.w / count)
        r = rnd.randint(*crown)
        cy = horizon - rnd.randint(*rise)
        trees.append((cy, x, r))
    trees.sort(reverse=True)            # the tallest last? no: tallest first
    trees.sort()
    for (cy, x, r) in trees:
        for y in range(cy, p.h):
            for k in range(trunk_w):
                p.set(x + k, y, _clamp(v - 0.14 + (0.08 if k == 0 and trunk_w > 1 else 0)), ramp)
    for (cy, x, r) in trees:
        lumps = [(x + rnd.uniform(-r * 0.7, r * 0.7), cy + rnd.uniform(-r * 0.3, r * 0.35),
                  r * rnd.uniform(0.45, 0.7)) for _ in range(rnd.randint(4, 7))]
        lumps.append((x, cy - r * 0.15, r * 0.6))
        lumps.sort(key=lambda l: -l[1])         # lower lumps first, upper over them
        for (lx, ly, lr) in lumps:
            for yy in range(int(ly - lr), int(ly + lr) + 1):
                for xx in range(int(lx - lr), int(lx + lr) + 1):
                    dx, dy = (xx + 0.5 - lx) / lr, (yy + 0.5 - ly) / lr
                    d = dx * dx + dy * dy
                    if d > 1.0:
                        continue
                    f = -dx - dy
                    s = 0.16 if f > 0.75 else (0.05 if f > 0.0 else -0.07)
                    p.set(xx, yy, _clamp(v + s), ramp)
    for y in range(max(0, horizon), p.h):
        d = (y - horizon) / float(max(1, body))
        for x in range(p.w):
            if bayer_on(x, y, min(1.0, 0.35 + d)):
                p.set(x, y, _clamp(v - 0.06 - body_fade * min(1.0, d)), ramp)
    # the ragged top of the understorey
    rnd2 = random.Random(seed + 1)
    x = 0
    while x < p.w:
        r = rnd2.randint(3, 8)
        cy = horizon + rnd2.randint(-2, 3)
        for yy in range(cy - r, cy + 1):
            for xx in range(x - r, x + r + 1):
                if (xx - x) ** 2 + (yy - cy) ** 2 <= r * r:
                    f = -(xx - x) - (yy - cy)
                    p.set(xx, yy, _clamp(v - 0.02 + (0.08 if f > r * 0.8 else 0.0)), ramp)
        x += rnd2.randint(4, 9)


# ---------------------------------------------------------------- 1. THE CANOPY
def _jungle():
    """CANOPY TRAIL and the grove. The composition is the approved phase-3
    one -- dusk-blue air, a far stand of trees, dark trunks framing the view
    -- redrawn at the new strip sizes with leaves, bark and roots in place of
    blobs. Two rules carried over from it: the backdrop's trunks are teal, on
    `foliage`, never the warm `wood` the level's own climbable trunks are
    built from, so nothing behind Kaya looks like something she can climb; and
    the strip bottoms (`oy` below) are where the old one-screen composition
    sits, so a level's floor still looks the way it did."""
    # Sky: the air itself, blue-grey rather than green, brightest high up where
    # the canopy opens, with the furthest forest as a band of crowns low down.
    sky = plane("sky", "water", (2.3, 4.4), opaque=True, windows={"foliage": (1.2, 2.4)})
    H, oy = sky.h, sky.h - VIEW_H
    vband(sky, 0, oy + 150, 1.0, 0.30, curve=0.8)
    vband(sky, oy + 150, H, 0.30, 0.12)
    shafts(sky, 5, 1130, dv=0.18, slope=4, width=(16, 40), reach=0.8)
    forest_rank(sky, oy + 174, 0.40, 1110, "foliage", count=16, crown=(10, 20),
                rise=(4, 34), trunk_w=1, body=50, body_fade=0.3)
    mist(sky, oy + 140, 34, 0.62)
    mist(sky, oy + 196, 30, 0.5, dv=0.14)
    grain(sky, 1140, 1500, dv=0.06)

    # Far: a receding stand of trees out of an understorey mass. A narrow
    # window high on `foliage`: these are drawn in leaves, but they cannot
    # shout.
    far = plane("far", "foliage", (1.5, 2.8))
    H, oy = far.h, far.h - VIEW_H
    rnd = random.Random(1201)
    trees = []
    for i in range(10):
        x = (i * far.w // 10 + rnd.randrange(24)) % far.w
        base = oy + rnd.randrange(170, 206)
        top = base - rnd.randrange(110, 190)
        w = rnd.randrange(4, 8)
        trees.append((x, base, top, w))
        bark_trunk(far, x, top + 10, base, w, 0.40, 1210 + i, taper=0.7,
                   roots=rnd.choice((0, 16, 22)))
        if rnd.random() < 0.6:                          # a bough off the trunk
            by = rnd.randrange(top + 40, base - 40)
            side = rnd.choice((-1, 1))
            span = rnd.randrange(12, 24)
            for k in range(span):
                far.set(x + w // 2 + side * (w // 2 + k), by - k // 2, 0.44)
                far.set(x + w // 2 + side * (w // 2 + k), by - k // 2 + 1, 0.28)
            crown_of_leaves(far, x + w // 2 + side * (w // 2 + span), by - span // 2 - 3,
                            rnd.randrange(10, 15), rnd.randrange(6, 9), 0.58,
                            1260 + i, size_=(4, 6))
    for i, (x, base, top, w) in enumerate(trees):
        # an umbrella, not a lollipop: two lower lobes either side of a wide,
        # flat top, the way a rainforest emergent spreads above the stand
        rx = rnd.randrange(26, 40)
        for k, (dx, dy, sx, sy) in enumerate(((-0.55, 9, 0.5, 0.75), (0.6, 7, 0.5, 0.7),
                                              (0.0, 0, 1.0, 1.0))):
            crown_of_leaves(far, x + w // 2 + int(dx * rx), top + 4 + dy, int(rx * sx),
                            int(rnd.randrange(10, 14) * sy), 0.58 + 0.04 * k,
                            1230 + i * 3 + k, size_=(4, 7))
    for i in range(8):                                  # lianas
        vine(far, rnd.randrange(far.w), rnd.randrange(0, oy + 60), rnd.randrange(50, 140),
             0.36, 1270 + i, leaf_v=0.62)
    treeline(far, oy + 198, 0.44, 1240, bump=(8, 16), depth=46, spacing=9, amp=10,
             crest=0.2, fade=0.34)
    for i in range(12):                                 # understorey palms
        fx = rnd.randrange(far.w)
        fy = H - rnd.randrange(14, 40)
        for k, a in enumerate((-155, -125, -98, -72, -45)):
            frond(far, fx, fy, a + rnd.uniform(-8, 8), rnd.randrange(14, 22),
                  0.56, 1280 + i * 7 + k, leaflet=4.5)
    mist(far, oy + 150, 34, 0.45)
    shafts(far, 4, 1290, dv=0.18, slope=4, width=(12, 30), reach=0.9)

    # Near: the frame. Great trunks with buttress roots, the canopy's underside
    # across the top, lianas off it. The widest window of the three but kept at
    # the dark end of the ramp: a silhouette with just enough drawing inside it
    # to be a tree.
    near = plane("near", "foliage", (0.0, 2.2))
    H = near.h
    rnd = random.Random(1301)
    for i, x in enumerate((30, 250, 470)):
        x += rnd.randrange(-20, 20)
        w = rnd.randrange(16, 23)
        bark_trunk(near, x, -4, H, w, 0.52, 1310 + i, wobble=2.0, taper=0.8,
                   roots=rnd.randrange(50, 76), moss="grass", moss_v=0.36)
        for _ in range(3):                              # limbs and their leaves
            by = rnd.randrange(40, H - 120)
            side = rnd.choice((-1, 1))
            span = rnd.randrange(18, 36)
            for k in range(span):
                for t in range(max(1, 4 - k // 10)):
                    near.set(x + w // 2 + side * (w // 2 + k), by + k // 4 + t,
                             0.42 if t == 0 else 0.26)
            leaf_cluster(near, x + w // 2 + side * (w // 2 + span + 3), by + span // 4,
                         11, 0.58, 1330 + i * 3 + by, size_=(6, 11))
    for i in range(34):                                 # the canopy's underside
        leaf_cluster(near, int(i * near.w / 34.0) + rnd.randrange(-8, 8),
                     rnd.randrange(0, 18), rnd.randrange(9, 15), 0.52, 1350 + i,
                     size_=(6, 12), droop=60.0)
    for i in range(12):
        vine(near, rnd.randrange(near.w), rnd.randrange(8, 24), rnd.randrange(60, 220),
             0.30, 1380 + i, leaf_v=0.6)
    for i in range(6):                                  # ferns at the roots
        fx = rnd.randrange(near.w)
        for k, a in enumerate((-160, -130, -105, -75, -50, -20)):
            frond(near, fx, H - 2, a, rnd.randrange(20, 32), 0.48, 1395 + i * 7 + k,
                  leaflet=7.0)

    # Fg: a few blades and fern tips across the bottom, nearer than the tiles.
    # Drawn over the tiles (src/world/level.gd) but behind every entity, so it
    # must stay sparse and dark: a hint of ground cover, never a hedge.
    fg = plane("fg", "grass", (0.0, 1.8))
    H = fg.h
    rnd = random.Random(1401)
    for i in range(16):
        x = rnd.randrange(fg.w)
        bh = rnd.randrange(8, 18)
        lean = rnd.uniform(-0.35, 0.35)
        for k in range(bh):
            t = k / float(bh - 1)
            fg.set(x + int(lean * k * k / bh), H - 1 - k, 0.15 + 0.7 * t)
    for i in range(4):
        fx = rnd.randrange(fg.w)
        for a in (-150, -118, -62, -30):
            frond(fg, fx, H + 2, a, rnd.randrange(12, 20), 0.4, 1420 + i * 5 + a,
                  leaflet=4.5)
    return {"sky": sky, "far": far, "near": near, "fg": fg}


# ------------------------------------------------------------ SKY BRANCH
def _sky():
    """SKY BRANCH: up in the crowns. The bright level, so the top of every
    plane stays deep enough for the white HUD and the pale end of the sky sits
    low, behind the darkest tiles. The canopy is a long way below, under a sea
    of cloud: the furthest green in the game, and the flattest."""
    sky = plane("sky", "water", (3.0, 6.5), opaque=True)
    H, oy = sky.h, sky.h - VIEW_H
    sky_path(sky, [("water", 0.40), ("water", 0.56), ("water", 0.70),
                   ("water", 0.82), ("metal", 0.70), ("metal", 0.82),
                   ("metal", 0.92), ("metal", 1.0)], curve=1.25)
    rnd = random.Random(5010)
    for i in range(7):                                  # high thin cirrus
        cloud(sky, rnd.randrange(sky.w), rnd.randrange(20, oy + 92),
              rnd.randrange(26, 52), rnd.randrange(3, 6), 0.84, 5020 + i, ramp="metal")
    grain(sky, 5030, 1100, dv=0.07)

    # Far: the cloud sea and the canopy under it, pale because it is seen
    # through more air than anything else in the game.
    far = plane("far", "metal", (4.2, 5.8), windows={"foliage": (3.2, 4.2)})
    H, oy = far.h, far.h - VIEW_H
    rnd = random.Random(5040)
    treeline(far, oy + 190, 0.44, 5060, "foliage", bump=(8, 18), depth=60, spacing=10,
             amp=8, crest=0.22, fade=0.3)
    forest_rank(far, oy + 214, 0.36, 5061, "foliage", count=14, crown=(8, 16),
                rise=(2, 26), body=30)
    for i in range(9):                                  # the cloud sea, lit on top
        cumulus(far, rnd.randrange(far.w), oy + rnd.randrange(150, 196),
                rnd.randrange(30, 60), rnd.randrange(10, 18), 0.52, 5050 + i, ramp="metal")
    for i in range(4):                                  # towers further off
        cumulus(far, rnd.randrange(far.w), oy + rnd.randrange(90, 130),
                rnd.randrange(18, 30), rnd.randrange(16, 26), 0.66, 5070 + i, ramp="metal")
    mist(far, oy + 176, 30, 0.5)
    horizon_haze(far, oy + 140, H, 0.58, 0.30, bands=4)

    # Near: one big limb across the top with its leaves -- you are up a tree,
    # not in one. Four short vines, not nine: SKY BRANCH has climbable vine
    # tiles, and a backdrop full of dangling green strings invites a player to
    # climb the wallpaper. The edge post is on `foliage`, not `wood`, for the
    # same reason the jungle's trunks are.
    near = plane("near", "foliage", (0.2, 2.6))
    H = near.h
    rnd = random.Random(5070)
    for y in range(0, 34):                              # the limb itself
        for x in range(near.w):
            t = (y - (3 + int(7 * math.sin(2 * math.pi * x / near.w * 3)))) / 18.0
            if 0.0 <= t <= 1.0:
                s = 0.30 if t < 0.25 else (-0.24 if t > 0.78 else 0.0)
                if (x * 7 + y * 3) % 23 == 0:
                    s -= 0.2                            # bark
                near.set(x, y, _clamp(0.42 + s), "wood")
    for i in range(26):
        leaf_cluster(near, int(i * near.w / 26.0) + rnd.randrange(-6, 6),
                     rnd.randrange(22, 36), rnd.randrange(9, 14), 0.56, 5080 + i,
                     size_=(6, 11), droop=55.0)
    for i in range(4):
        vine(near, rnd.randrange(near.w), 28, rnd.randrange(26, 74), 0.30, 5090 + i,
             leaf_v=0.6)
    bark_trunk(near, 20, 0, H, 17, 0.44, 5095, taper=0.85)
    for _ in range(2):
        by = rnd.randrange(60, H - 80)
        for k in range(26):
            near.set(37 + k, by + k // 3, 0.42)
            near.set(37 + k, by + k // 3 + 1, 0.24)
        leaf_cluster(near, 66, by + 9, 11, 0.56, 5096 + by, size_=(6, 10))
    return {"sky": sky, "far": far, "near": near}


# ------------------------------------------------------- 2. SUNKEN RUINS
def arcade(p, x0, spacing, top, bottom, width, v, seed, ramp=None, broken=0.3,
           arch=True):
    """A run of dressed columns carrying arches, laid in courses (masonry),
    some broken off short. Architecture is the one subject where regularity
    is the read, so this is the only brush that repeats on a fixed pitch --
    `spacing` must divide the strip width for the wrap to hold."""
    rnd = random.Random(seed)
    x = x0
    while x < x0 + p.w:
        h = bottom - top
        cut = top + (rnd.randint(int(h * 0.3), int(h * 0.7)) if rnd.random() < broken else 0)
        masonry(p, x, cut, width, bottom - cut, v, seed + x, ramp, course=8,
                block=(width, width), chip=0.25)
        for yy in range(cut, bottom):                   # cylinder light on the shaft
            p.boost(x + 1, yy, 0.14)
            p.boost(x + width - 2, yy, -0.14)
        if cut == top:                                  # capital
            for yy in range(top - 3, top):
                for xx in range(x - 2, x + width + 2):
                    p.set(xx, yy, _clamp(v + (0.22 if yy == top - 3 else 0.0)), ramp)
            if arch and rnd.random() < 0.75:
                r = (spacing - width) / 2.0
                cx = x + width + r
                for a in range(0, 181, 2):
                    for t in range(5):
                        ax = cx - math.cos(math.radians(a)) * (r + t)
                        ay = top - 3 - math.sin(math.radians(a)) * (r * 0.8 + t)
                        p.set(int(ax), int(ay), _clamp(v + (0.24 if t == 4 else
                                                            (-0.18 if t == 0 else 0.02))), ramp)
        x += spacing


def _ruins():
    """A drowned hall. Underwater, lit from above, so every gradient runs the
    other way to the land worlds: bright at the top, black at the floor. Cold
    greens and blue-greys and nothing warm at all -- which is most of what
    separates it from the jungle."""
    sky = plane("sky", "water", (1.4, 3.8), opaque=True, windows={"stone": (1.2, 2.4)})
    H, oy = sky.h, sky.h - VIEW_H
    vband(sky, 0, oy + 92, 1.0, 0.48, curve=0.9)
    vband(sky, oy + 92, H, 0.48, 0.05, curve=1.3)
    shafts(sky, 6, 6010, dv=0.26, slope=5, width=(14, 38), reach=0.75)
    arcade(sky, 0, 56, oy + 54, oy + 200, 8, 0.30, 6011, "stone", broken=0.25)
    ridge(sky, oy + 202, 0.18, 6012, amp=13, step=13, ramp="stone", crest=0.12,
          fade=0.32, rough=0.10)
    mist(sky, oy + 84, 40, 0.5, dv=0.2)
    mist(sky, oy + 182, 44, 0.42, dv=0.16)              # silt hanging in the water
    grain(sky, 6013, 1500, dv=0.09)

    # Far: a nearer arcade with the vault it held up, algae down the shafts,
    # silt drifted at the base, fish keeping still in the gaps.
    far = plane("far", "stone", (1.1, 2.5), windows={"foliage": (0.7, 1.8),
                                                    "water": (2.4, 3.6)})
    H, oy = far.h, far.h - VIEW_H
    arcade(far, 10, 128, oy + 40, oy + 228, 16, 0.46, 6020, broken=0.35)
    masonry(far, 0, 0, far.w, oy + 14, 0.40, 6021, course=9, block=(14, 30), chip=0.2)
    rnd = random.Random(6021)
    for i in range(9):
        vine(far, rnd.randrange(far.w), rnd.randrange(oy + 10, oy + 60),
             rnd.randrange(40, 120), 0.56, 6030 + i, ramp="foliage", curl=False)
    ridge(far, oy + 220, 0.34, 6022, amp=7, step=15, thickness=40, crest=0.2,
          fade=0.3, rough=0.06)
    bubbles(far, 60, 6023, 0.7, "water", (0, H - 40))
    mist(far, oy + 120, 36, 0.42, dv=0.18)
    horizon_haze(far, oy + 120, H - 4, 0.55, 0.10, bands=5)

    # Near: the frame. Fallen drums of column and the kelp grown up them, dark
    # enough that a green frog in front of it is still a green frog.
    near = plane("near", "stone", (0.0, 1.6), windows={"foliage": (0.0, 1.2)})
    H = near.h
    rnd = random.Random(6040)
    for i in range(3):
        x = (i * near.w // 3 + rnd.randrange(40)) % near.w
        w = rnd.randrange(18, 26)
        masonry(near, x, 0, w, H, 0.50, 6041 + i, course=26, block=(w, w), chip=0.0)
        for yy in range(H):
            near.boost(x + 2, yy, 0.16)
            near.boost(x + w - 3, yy, -0.18)
    for i in range(14):                                 # kelp from the floor up
        x = rnd.randrange(near.w)
        L = rnd.randrange(60, 200)
        for k in range(L):
            y = H - 1 - k
            xx = x + 3 * math.sin(k / 13.0 + i) + 1.4 * math.sin(k / 5.0 + i)
            near.set(int(xx), y, 0.62, "foliage")
            near.set(int(xx) + 1, y, 0.40, "foliage")
            if k % 9 == 4:
                leaf(near, xx + 1, y, -30 if (k // 9) % 2 else -150, rnd.uniform(5, 9), 1.6,
                     0.70, "foliage")
    for i in range(10):
        vine(near, rnd.randrange(near.w), 0, rnd.randrange(30, 120), 0.62, 6050 + i,
             ramp="foliage", curl=False)

    fg = plane("fg", "water", (0.0, 1.3))
    H = fg.h
    rnd = random.Random(6095)
    for i in range(18):                                 # silt wisps, low down
        x = rnd.randrange(fg.w)
        y0 = H - rnd.randrange(8, 90)
        length = rnd.randrange(6, 15)
        for k in range(length):
            fg.set(x + int(1.6 * math.sin(k / 3.0 + i)), y0 - k, 0.25 + 0.55 * (k / float(length)))
    return {"sky": sky, "far": far, "near": near, "fg": fg}


# ------------------------------------------------------- 3. THERMAL HEIGHTS
def _heights():
    """High air in sunlight. The `gold` ramp must never be a field here: the
    fish is built out of gold, and a warm orange sky would take it whole. The
    warmth is `ember` at its dark end and `dirt`, gold appears only inside the
    sun, and the pale end of the sky is `metal`, which no form uses."""
    sky = plane("sky", "ember", (1.1, 3.1), opaque=True,
                windows={"metal": (3.4, 5.8), "gold": (4.4, 6.4)})
    H, oy = sky.h, sky.h - VIEW_H
    sky_path(sky, [("ember", 0.10), ("ember", 0.26), ("ember", 0.44),
                   ("ember", 0.64), ("metal", 0.22), ("metal", 0.46),
                   ("metal", 0.70), ("metal", 0.90)], curve=1.25)
    rnd = random.Random(7010)
    for i in range(7):
        cloud(sky, rnd.randrange(sky.w), rnd.randrange(20, oy + 104),
              rnd.randrange(30, 60), rnd.randrange(3, 6), 0.55, 7020 + i, ramp="metal")
    sx, sy = 318, oy + 58
    glow(sky, sx, sy, 46, 0.30, 7030, frac=0.75)        # the sun, behind it all
    for r in (10, 7):
        for y in range(sy - r, sy + r + 1):
            for x in range(sx - r, sx + r + 1):
                if math.hypot(x - sx, y - sy) <= r:
                    sky.set(x, y, 0.9 if r == 10 else 1.0, "gold")
    # the furthest range, barely there
    for i in range(6):
        peak(sky, int(i * sky.w / 6.0) + rnd.randrange(30), oy + 190,
             rnd.randrange(40, 80), rnd.randrange(40, 70), 0.30, 7035 + i, "metal",
             snow="metal", snow_v=0.46)
    mist(sky, oy + 170, 30, 0.6, dv=0.18)
    grain(sky, 7040, 1200, dv=0.07)

    # Far: the range itself, gullied, with snow following the gullies down, and
    # a cloud sea eating its feet. Dirt from 2.2, not 1.0: the fish's shadow
    # colour is 23.7 from dirt step 2, under the palette's finest step.
    far = plane("far", "dirt", (2.2, 3.4), windows={"metal": (3.8, 5.0)})
    H, oy = far.h, far.h - VIEW_H
    rnd = random.Random(7050)
    for i in range(8):
        peak(far, int(i * far.w / 8.0) + rnd.randrange(30), oy + 200,
             rnd.randrange(60, 130), rnd.randrange(30, 56), 0.52, 7055 + i,
             snow="metal", snow_v=0.78, snow_from=0.8)
    for i in range(10):
        cumulus(far, rnd.randrange(far.w), oy + rnd.randrange(184, 226),
                rnd.randrange(30, 60), rnd.randrange(10, 16), 0.42, 7060 + i, "metal")
    mist(far, oy + 168, 40, 0.42, dv=0.16)
    horizon_haze(far, oy + 150, H, 0.50, 0.26, bands=4)

    # Near: the cliff you are on, up both edges of the strip, and the ledges
    # jutting from it. Dark, because everything behind it is pale.
    near = plane("near", "dirt", (0.0, 1.5))
    H = near.h
    rnd = random.Random(7070)
    for y in range(H):
        jag = int(9 * math.sin(y / 31.0) + 5 * math.sin(y / 11.0) + 3 * math.sin(y / 4.5))
        for (lo, hi, lit_left) in ((0, 46 + jag, True), (near.w - 44 - jag, near.w, False)):
            span = max(1, hi - lo)
            for x in range(lo, hi):
                t = (x - lo) / float(span)
                edge = t < 0.16 if lit_left else t > 0.84
                fade = t > 0.86 if lit_left else t < 0.14
                strata = 0.12 if (y + int(4 * math.sin(x / 9.0))) % 11 == 0 else 0.0
                near.set(x, y, _clamp(0.42 + (0.28 if edge else (-0.3 if fade else 0.0))
                                      - strata))
    for i in range(6):
        y = rnd.randrange(20, H - 30)
        wdt = rnd.randrange(16, 40)
        left = rnd.random() < 0.5
        for k in range(rnd.randrange(5, 11)):
            for x in range(wdt - k):
                px = (34 + x) if left else (near.w - 34 - x)
                near.set(px, y + k, 0.62 if k == 0 else 0.26)
        for j in range(3):                              # a tuft clinging to it
            frond(near, (34 + wdt // 2 + j * 4) if left else (near.w - 34 - wdt // 2 - j * 4),
                  y, -60 - j * 30, rnd.randrange(8, 13), 0.5, 7075 + i * 3 + j, leaflet=3.5)
    spires(near, H + 10, 6, 0.3, 7080, height=(18, 46), width=(16, 40))

    fg = plane("fg", "metal", (0.1, 1.1))
    H = fg.h
    rnd = random.Random(7095)
    for i in range(16):                                 # spindrift, low and thin
        y = H - rnd.randrange(4, 56)
        x0 = rnd.randrange(fg.w)
        for k in range(rnd.randrange(10, 28)):
            fg.set(x0 + k, y + int(1.1 * math.sin(k / 4.0 + i)), 0.35 + 0.35 * math.sin(k / 5.0 + i))
    return {"sky": sky, "far": far, "near": near, "fg": fg}


# --------------------------------------------------------- 4. TERMITE DEEPS
def _deeps():
    """No sky under a termite mound, so every plane is earth and depth is how
    much violet reaches it. A dark world: the far plane is the darkest, and
    the near one carries what colour there is. Held low enough everywhere that
    a silhouette survives having no light on it at all."""
    sky = plane("sky", "dirt", (0.05, 1.15), opaque=True, windows={"purple": (0.6, 2.6)})
    H = sky.h
    vband(sky, 0, H, 0.30, 0.9, curve=1.4)
    rnd = random.Random(8010)
    for i in range(8):                                  # galleries going back
        cx, cy = rnd.randrange(sky.w), rnd.randrange(30, H - 30)
        for r in range(rnd.randrange(16, 40), 0, -6):
            for a in range(0, 360, 4):
                sky.set(cx + int(math.cos(math.radians(a)) * r * 1.5),
                        cy + int(math.sin(math.radians(a)) * r), 0.16 + r / 90.0)
    for i in range(10):                                 # fungus, far away
        glow(sky, rnd.randrange(sky.w), rnd.randrange(30, H - 20), rnd.randrange(14, 30),
             0.34, 8020 + i, frac=0.6)
    grain(sky, 8030, 1500, dv=0.08)

    # Far: the comb. Cell after cell, the one shape that says "something built
    # this" rather than "something dug this". The pitch divides the strip.
    far = plane("far", "wood", (0.4, 1.5), windows={"purple": (1.4, 3.6)})
    H = far.h
    rnd = random.Random(8040)
    holes = []
    for cy in range(-14, H + 10, 24):
        off = rnd.randrange(32)
        for cx in range(0, far.w, 32):
            x = cx + off + rnd.randint(-5, 5)
            y = cy + rnd.randint(-5, 5)
            if rnd.random() < 0.22:
                continue
            rx, ry = rnd.randint(11, 16), rnd.randint(7, 12)
            thick = 2 if rnd.random() < 0.6 else 3
            if rnd.random() < 0.3:                      # a cell broken through
                holes.append((x, y, rx - thick, ry - thick))
            for a in range(0, 360, 5):
                for t in range(thick):
                    ang = math.radians(a)
                    lit = math.cos(ang) < -0.3 and math.sin(ang) < 0.3
                    far.set(x + int(math.cos(ang) * (rx - t)), y + int(math.sin(ang) * (ry - t)),
                            (0.72 if lit else 0.58) if t == 0 else 0.30)
            if rnd.random() < 0.12:
                glow(far, x, y, 12, 0.5, 8050 + cx + cy, frac=0.8)
    mist(far, H // 2, 64, 0.34, dv=0.14)
    horizon_haze(far, 0, H, 0.62, 0.30, ramp="purple", bands=5)
    # Broken cells open onto the galleries behind: the plane must have holes or
    # it is a wall, not a layer (tests/test_art_depth.gd).
    for (hx, hy, rx, ry) in holes:
        for yy in range(hy - ry, hy + ry + 1):
            for xx in range(hx - rx, hx + rx + 1):
                if ((xx - hx) / float(rx)) ** 2 + ((yy - hy) / float(ry)) ** 2 < 0.8 \
                        and 0 <= yy < H:
                    far.val[yy][xx % far.w] = None

    # Near: great roots down through everything, bark-fissured, and the
    # mycelium strung between them; a few glowing caps on the roots.
    near = plane("near", "wood", (0.0, 1.4), windows={"purple": (0.8, 2.8)})
    H = near.h
    rnd = random.Random(8060)
    for i in range(4):
        x = (i * near.w // 4 + rnd.randrange(50)) % near.w
        w = rnd.randrange(20, 32)
        bark_trunk(near, x, 0, H, w, 0.48, 8061 + i, wobble=7.0)
        for _ in range(3):                              # a shelf fungus
            fy = rnd.randrange(20, H - 20)
            for k in range(-5, 6):
                for t in range(3 - abs(k) // 3):
                    near.set(x + w + k // 2, fy + t, 0.8 if t == 0 else 0.55, "purple")
    for i in range(16):
        vine(near, rnd.randrange(near.w), rnd.randrange(0, 30), rnd.randrange(24, 130),
             0.66, 8070 + i, ramp="purple", every=11, curl=False)
    for i in range(7):
        glow(near, rnd.randrange(near.w), rnd.randrange(0, H), rnd.randrange(10, 22),
             0.4, 8080 + i, frac=0.7)

    fg = plane("fg", "wood", (0.0, 1.2))                # root fringe from the roof
    rnd = random.Random(8095)
    for i in range(12):
        x = rnd.randrange(fg.w)
        length = rnd.randrange(16, 36)
        for k in range(length):
            fg.set(x + int(2.2 * math.sin(k / 5.0 + i)), k, 0.20 + 0.55 * (1.0 - k / float(length)))
    return {"sky": sky, "far": far, "near": near, "fg": fg}


# ----------------------------------------------------- 5. THE OBSIDIAN NEST
def smoke(p, x, y0, height, v, seed, ramp=None):
    """A plume rising and leaning as it goes, lit on the side toward the
    magma below rather than toward the sky."""
    rnd = random.Random(seed)
    for i in range(int(height / 6)):
        t = i / float(max(1, height / 6))
        cx = x + 14 * t * t + 3 * math.sin(i / 2.0 + seed)
        cy = y0 - i * 6
        r = 4 + 12 * t + rnd.uniform(-1, 1)
        for yy in range(int(cy - r), int(cy + r) + 1):
            for xx in range(int(cx - r), int(cx + r) + 1):
                dx, dy = (xx - cx) / r, (yy - cy) / r
                if dx * dx + dy * dy > 1.0 or not bayer_on(xx, yy, 0.85 - 0.5 * t):
                    continue
                p.set(xx, yy, _clamp(v + (0.12 if dy > 0.3 else -0.04) - 0.2 * t), ramp)


def _obsidian():
    """Black glass over a magma sea. The light comes from below: everything is
    a silhouette with its underside lit, and the brightest thing is at the
    bottom where the tiles are darkest. Ember is kept to the glow and the
    seams -- it is the bird's own hue, and a field of it would take a red
    sprite with it."""
    sky = plane("sky", "purple", (0.05, 1.05), opaque=True, windows={"ember": (0.8, 4.4)})
    H, oy = sky.h, sky.h - VIEW_H
    vband(sky, 0, oy + 168, 0.10, 0.62, curve=1.6)
    for y in range(oy + 128, H):
        t = (y - (oy + 128)) / float(H - 1 - (oy + 128))
        for x in range(sky.w):
            if bayer_on(x, y, min(1.0, (t * 1.5) ** 2.0)):
                sky.set(x, y, 0.10 + 0.86 * (t ** 1.3) + 0.05 * math.sin((x + y * 3) / 17.0),
                        "ember")
    rnd = random.Random(9010)
    for i in range(8):
        glow(sky, rnd.randrange(sky.w), H - rnd.randrange(0, 44), rnd.randrange(18, 44),
             0.30, 9020 + i, frac=0.7)
    for i in range(30):                                 # sparks going up
        sky.set(rnd.randrange(sky.w), rnd.randrange(20, H - 10), 0.95, "ember")
    grain(sky, 9030, 1300, dv=0.07)

    far = plane("far", "stone", (0.15, 1.4), windows={"ember": (1.2, 3.4)})
    H, oy = far.h, far.h - VIEW_H
    rnd = random.Random(9040)
    for i in range(5):
        smoke(far, rnd.randrange(far.w), oy + 200, rnd.randrange(120, oy + 190), 0.5,
              9045 + i)
    spires(far, oy + 208, 13, 0.44, 9041, height=(46, 150), width=(16, 46))
    for i in range(10):
        glow(far, rnd.randrange(far.w), oy + rnd.randrange(198, 224), rnd.randrange(16, 36),
             0.5, 9060 + i, frac=0.8)
    mist(far, oy + 176, 42, 0.36, dv=0.16)
    horizon_haze(far, oy + 120, H, 0.20, 0.55, bands=4)

    near = plane("near", "stone", (0.0, 1.1), windows={"ember": (0.8, 3.0)})
    H = near.h
    rnd = random.Random(9070)
    for i in range(5):                                  # the flues
        x = (i * near.w // 5 + rnd.randrange(46)) % near.w
        w = rnd.randrange(18, 30)
        for y in range(H):
            cx = x + int(4 * math.sin(y / 53.0 + i))
            for k in range(w):
                t = k / float(w - 1)
                facet = 0.10 if (y // 14 + k // 6) % 3 == 0 else 0.0
                near.set(cx + k, y, _clamp(0.44 + facet + (0.3 if t < 0.18 else
                                                           (-0.3 if t > 0.84 else 0.0))))
            if rnd.random() < 0.10:
                near.set(cx + w // 2 + rnd.choice((-1, 0, 1)), y, 0.8, "ember")
    spires(near, H + 4, 7, 0.3, 9080, height=(24, 80), width=(20, 52))
    for i in range(8):
        glow(near, rnd.randrange(near.w), H - rnd.randrange(0, 26), rnd.randrange(12, 28),
             0.42, 9090 + i, frac=0.7)

    fg = plane("fg", "stone", (0.0, 1.3), windows={"ember": (0.6, 2.4)})
    H = fg.h
    rnd = random.Random(9095)
    for i in range(14):                                 # glass shards, glinting
        x = rnd.randrange(fg.w)
        y = H - rnd.randrange(2, 32)
        h = rnd.randrange(6, 15)
        for k in range(h):
            fg.set(x, y - k, 0.25 + 0.5 * (1.0 - k / float(h)))
        if rnd.random() < 0.55:
            fg.set(x, y - h, 0.9, "ember")
    return {"sky": sky, "far": far, "near": near, "fg": fg}


WORLDS = {"jungle": _jungle, "sky": _sky, "ruins": _ruins,
          "heights": _heights, "deeps": _deeps, "obsidian": _obsidian}


def build(out_dir, worlds=None):
    """Paint and save every plane; returns {world: {plane: Plane}}."""
    out = {}
    for world, make in sorted(WORLDS.items()):
        if worlds and world not in worlds:
            continue
        planes = make()
        for name, p in planes.items():
            assert (p.w, p.h) == size(name), (world, name, p.w, p.h)
            p.render().save(os.path.join(out_dir, "bg_%s_%s.png" % (world, name)))
        out[world] = planes
    return out
