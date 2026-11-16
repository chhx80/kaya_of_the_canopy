"""Kaya on the title screen: a full figure about 170 world units tall, drawn
natively at ART_SCALE (HD pass, phase H3, docs/plan-hd.md).

The in-game Kaya is a 40-unit puppet whose limbs are capsules; at four times
that height a capsule reads as a tube and a blob of shading reads as a blob. So
this figure is built the other way round: each body part is a mask with a
designed silhouette (profiles sampled through Catmull-Rom curves, so a calf
swells and an ankle narrows), lit as a form from its own whole mask -- a
cylinder across its width, rounded at its ends, light from the upper left like
everything else in the game -- and quantised to whole ramp steps, never
dithered (the same finding as `kaya40.shade_hd`). The parts are composited back
to front; where a part passes in front of another, the one behind gets a dark
contour and a step of occlusion. Then everything a figure this size owes the
viewer is drawn texel by texel on top: the face, the weave, the folds.

She is the in-game Kaya: the same ramps (`kaya40.MAT` levels), the same
outfit -- wide straw hat with a brown ribbon, long wavy dark hair, gold hoops,
an ember bead necklace, the green crop top, yellow fringed shorts, leaf-green
ankle wraps, red sandals -- and the same ink.

Design cues only. Nothing here is traced or sampled from any picture; every
shape is a number in this file.

`build()` writes assets/sprites/title_kaya.png: FRAMES cells of CELL_W x CELL_H
texels (CELL_W / ART_SCALE x CELL_H / ART_SCALE world units), feet on the cell's
bottom row. Frame order is the idle cycle src/ui/menus/title_screen.gd plays:
0 rest, 1 breathing in, 2 rest with the hair and ribbon drifting, 3 blink.
"""

import math
import os

from PIL import Image

from . import palette
from .kaya40 import MAT, _hand_aa

CELL_W, CELL_H = 168, 352           # texels: 84 x 176 world units
FRAMES = 4
CX = 84.0                           # her centre line, texels

INK = "ink"

# (name, ankle x, ankle y, toe offset, which side is inside)
FEET = (("l", CX - 12.0, 326.0, -1.0, 1), ("r", CX + 17.0, 325.0, 2.0, -1))


def _leaves(ax, ay):
    """The ankle wrap's leaves as (base, tip, half-width): five blades rising
    from the binding, fanned out, and two hanging over the foot."""
    out = []
    for k, u in enumerate((-1.0, -0.5, 0.0, 0.5, 1.0)):
        x = ax + u * 5.0
        out.append(((x, ay - 1.0), (x + u * 4.5, ay - 13.0 + abs(u) * 3.0 + (k % 2) * 2.0),
                    3.0 if k % 2 == 0 else 2.6))
    for sx in (-1, 1):
        out.append(((ax + sx * 3.5, ay - 1.0), (ax + sx * 7.5, ay + 6.0), 2.3))
    return out


def _leaf_outline(base, tip, w, n=12):
    (bx, by), (tx, ty) = base, tip
    dx, dy = tx - bx, ty - by
    ln = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / ln, dx / ln
    left, right = [], []
    for i in range(n + 1):
        t = i / float(n)
        h = w * math.sin(math.pi * min(1.0, 0.12 + t * 0.95)) ** 0.8
        cx, cy = bx + dx * t, by + dy * t
        left.append((cx + nx * h, cy + ny * h))
        right.append((cx - nx * h, cy - ny * h))
    return left + right[::-1]

# (ramp, base level). Bases are kaya40.MAT's, so the title figure and the
# in-game sprite sit on the same steps of the same ramps.
SKIN = ("skin", MAT['s'][1])
HAIR = ("hair", MAT['h'][1])
STRAW = ("straw", MAT['a'][1])
RIBBON = ("dirt", MAT['n'][1])
TOP = ("cloth", MAT['t'][1])
SHORTS = ("gold", MAT['y'][1] - 0.6)
WRAP = ("cloth", MAT['g'][1])
SOLE = ("ember", MAT['r'][1])
BEAD = ("ember", MAT['b'][1])
HOOP = ("gold", MAT['o'][1])

L = (-0.62, -0.52, 0.59)            # palette.LIGHT, upper left, toward the viewer
_n = math.sqrt(sum(c * c for c in L))
L = tuple(c / _n for c in L)


def _cr(pts, t):
    """Catmull-Rom through (y, v...) samples; `t` indexes the samples."""
    n = len(pts)
    i = max(0, min(n - 2, int(math.floor(t))))
    u = t - i
    p0, p1 = pts[max(0, i - 1)], pts[i]
    p2, p3 = pts[i + 1], pts[min(n - 1, i + 2)]
    out = []
    for k in range(len(p1)):
        a, b, c, d = p0[k], p1[k], p2[k], p3[k]
        out.append(0.5 * ((2 * b) + (-a + c) * u + (2 * a - 5 * b + 4 * c - d) * u * u
                          + (-a + 3 * b - 3 * c + d) * u * u * u))
    return out


class Part:
    """One body part: a mask, a material, and how its form is lit."""

    def __init__(self, fig, name, mat, z, gain=2.2, ref=0.5, round_=0.55, flat=False,
                 contour=True):
        self.fig, self.name, self.mat, self.z = fig, name, mat, z
        self.gain, self.ref, self.round_, self.flat = gain, ref, round_, flat
        self.contour = contour
        self.m = [bytearray(CELL_W) for _ in range(CELL_H)]

    def on(self, x, y):
        return 0 <= x < CELL_W and 0 <= y < CELL_H and self.m[y][x]

    def set(self, x, y, v=1):
        if 0 <= x < CELL_W and 0 <= y < CELL_H:
            self.m[y][x] = v

    # ------------------------------------------------------------ shapes
    def disc(self, cx, cy, r, v=1):
        for y in range(int(cy - r - 1), int(cy + r + 2)):
            for x in range(int(cx - r - 1), int(cx + r + 2)):
                if (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= r * r:
                    self.set(x, y, v)

    def ellipse(self, cx, cy, rx, ry, clip=None, v=1):
        for y in range(int(cy - ry - 1), int(cy + ry + 2)):
            for x in range(int(cx - rx - 1), int(cx + rx + 2)):
                px, py = x + 0.5, y + 0.5
                if ((px - cx) / rx) ** 2 + ((py - cy) / ry) ** 2 <= 1.0:
                    if clip is None or clip(px, py):
                        self.set(x, y, v)

    def tube(self, pts, v=1, step=0.2):
        """A smooth limb: discs swept along a Catmull-Rom path through
        (x, y, r) samples, so radius and direction both change smoothly."""
        n = len(pts)
        t = 0.0
        while t <= n - 1 + 1e-9:
            x, y, r = _cr(pts, t)
            self.disc(x, y, r, v)
            seg = math.hypot(pts[min(n - 1, int(t) + 1)][0] - pts[int(min(t, n - 2))][0],
                             pts[min(n - 1, int(t) + 1)][1] - pts[int(min(t, n - 2))][1])
            t += step / max(seg, 1.0)

    def profile(self, rows, v=1, clip=None):
        """A vertical form: rows of (y, centre x, half-width left, half-width
        right), smoothed through Catmull-Rom and filled row by row."""
        y0, y1 = rows[0][0], rows[-1][0]
        k = 0.0
        prev = None
        samples = []
        while k <= len(rows) - 1 + 1e-9:
            samples.append(_cr(rows, k))
            k += 0.02
        for y in range(int(math.floor(y0)), int(math.ceil(y1)) + 1):
            yc = y + 0.5
            best = None
            for s in samples:
                if best is None or abs(s[0] - yc) < abs(best[0] - yc):
                    best = s
            if best is None or abs(best[0] - yc) > 1.0:
                continue
            _, cx, hl, hr = best
            for x in range(int(cx - hl - 1), int(cx + hr + 2)):
                px = x + 0.5
                if cx - hl <= px <= cx + hr:
                    if clip is None or clip(px, yc):
                        self.set(x, y, v)
            prev = best
        return prev

    def poly(self, pts, v=1):
        ys = [p[1] for p in pts]
        for y in range(int(min(ys)) - 1, int(max(ys)) + 2):
            yc = y + 0.5
            xs = []
            for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
                if (y0 <= yc < y1) or (y1 <= yc < y0):
                    xs.append(x0 + (yc - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for a, b in zip(xs[::2], xs[1::2]):
                for x in range(int(math.floor(a)), int(math.ceil(b)) + 1):
                    if a <= x + 0.5 <= b:
                        self.set(x, y, v)

    def clear_where(self, fn):
        for y in range(CELL_H):
            row = self.m[y]
            for x in range(CELL_W):
                if row[x] and fn(x + 0.5, y + 0.5):
                    row[x] = 0

    # ------------------------------------------------------------ light
    def levels(self):
        """Level per texel of the mask, lit as a form from its own mask:
        the run of texels left/right gives the across-the-form normal, the
        run up/down rounds the ends."""
        m, out = self.m, {}
        ramp, base = self.mat
        H, W = CELL_H, CELL_W
        left = [[0] * W for _ in range(H)]
        right = [[0] * W for _ in range(H)]
        up = [[0] * W for _ in range(H)]
        down = [[0] * W for _ in range(H)]
        for y in range(H):
            row = m[y]
            for x in range(W):
                if row[x]:
                    left[y][x] = left[y][x - 1] + 1 if x and row[x - 1] else 1
            for x in range(W - 1, -1, -1):
                if row[x]:
                    right[y][x] = right[y][x + 1] + 1 if x < W - 1 and row[x + 1] else 1
        for x in range(W):
            for y in range(H):
                if m[y][x]:
                    up[y][x] = up[y - 1][x] + 1 if y and m[y - 1][x] else 1
            for y in range(H - 1, -1, -1):
                if m[y][x]:
                    down[y][x] = down[y + 1][x] + 1 if y < H - 1 and m[y + 1][x] else 1
        for y in range(H):
            for x in range(W):
                if not m[y][x]:
                    continue
                if self.flat:
                    out[(x, y)] = base
                    continue
                dl, dr, du, dd = left[y][x], right[y][x], up[y][x], down[y][x]
                u = (dl - dr) / float(dl + dr)          # -1 at the left edge
                v = (du - dd) / float(du + dd)
                # only the last few texels of a long run bend toward the end
                span_v = du + dd
                endv = 0.0
                if min(du, dd) < 10 and span_v > 6:
                    endv = (1.0 - min(du, dd) / 10.0) * (1 if dd < du else -1)
                ny = self.round_ * (endv if span_v > 20 else v)
                nx = u * 0.96
                nz = math.sqrt(max(0.0, 1.0 - nx * nx - ny * ny))
                d = nx * L[0] + ny * L[1] + nz * L[2]
                out[(x, y)] = base + self.gain * (d - self.ref)
        return out


class Figure:
    def __init__(self):
        self.parts = []
        self.shadow = {}            # (x, y) -> step delta, applied after light
        self.paint = {}             # (x, y) -> (ramp, step) or INK, final

    def part(self, name, mat, **kw):
        p = Part(self, name, mat, len(self.parts), **kw)
        self.parts.append(p)
        return p

    def shade(self, x, y, d, only=None):
        x, y = int(x), int(y)
        if only is not None and self.top_name(x, y) not in only:
            return
        self.shadow[(x, y)] = self.shadow.get((x, y), 0) + d

    def top(self, x, y):
        for p in reversed(self.parts):
            if p.on(x, y):
                return p
        return None

    def top_name(self, x, y):
        p = self.top(x, y)
        return p.name if p else None

    def put(self, x, y, col, only=None):
        x, y = int(math.floor(x)), int(math.floor(y))
        if not (0 <= x < CELL_W and 0 <= y < CELL_H):
            return
        if only is not None and self.top_name(x, y) not in only:
            return
        self.paint[(x, y)] = col

    def line(self, pts, col, only=None):
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
            for k in range(n + 1):
                u = k / float(max(n, 1))
                self.put(x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, col, only)

    def curve(self, pts, col, only=None, n=40):
        """A one-texel stroke through Catmull-Rom points."""
        out = [tuple(_cr(pts, k * (len(pts) - 1) / float(n))) for k in range(n + 1)]
        self.line(out, col, only)

    # ------------------------------------------------------------ render
    def render(self):
        lv = {}
        for p in self.parts:
            lv[p.name] = p.levels()
        img = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
        px = img.load()
        top = [[None] * CELL_W for _ in range(CELL_H)]
        for y in range(CELL_H):
            for x in range(CELL_W):
                top[y][x] = self.top(x, y)
        # occlusion: a texel of a part sitting just behind another part's edge
        # gets a contour (the texel touching it) and a step of shade (the next)
        occl = {}
        for y in range(CELL_H):
            for x in range(CELL_W):
                p = top[y][x]
                if p is None or not p.contour:
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if not (0 <= nx < CELL_W and 0 <= ny < CELL_H):
                        continue
                    q = top[ny][nx]
                    if q is not None and q is not p and q.z > p.z and q.contour:
                        occl[(x, y)] = 3
                        for k in (1, 2):
                            bx, by = x - dx * k, y - dy * k
                            if (0 <= bx < CELL_W and 0 <= by < CELL_H
                                    and top[by][bx] is p and occl.get((bx, by), 0) < 2 - (k - 1)):
                                occl[(bx, by)] = 1 if k == 2 else max(occl.get((bx, by), 0), 1)
        for y in range(CELL_H):
            for x in range(CELL_W):
                p = top[y][x]
                if p is None:
                    continue
                ramp = p.mat[0]
                lvl = lv[p.name][(x, y)] + self.shadow.get((x, y), 0)
                o = occl.get((x, y), 0)
                if o >= 3:
                    lvl = min(lvl - 2.0, 1.0 if ramp != "hair" else 0.0)
                elif o:
                    lvl -= 1.0
                px[x, y] = palette.step(ramp, lvl) + (255,)
        for (x, y), col in self.paint.items():
            if col is None:
                px[x, y] = (0, 0, 0, 0)
            elif col == INK:
                px[x, y] = palette.INK + (255,)
            else:
                px[x, y] = palette.step(col[0], col[1]) + (255,)
        _ink(img)
        _hand_aa(img)
        palette.selective_outline(img)
        return img


def _ink(img):
    """Ink round the silhouette, with a second texel on the shadow side
    (right and below), as `kaya40.HDCanvas.outline` weights it."""
    w, h = img.size
    px = img.load()
    solid = [[px[x, y][3] > 0 for x in range(w)] for y in range(h)]

    def on(x, y):
        return 0 <= x < w and 0 <= y < h and solid[y][x]

    ink = palette.INK + (255,)
    first = set()
    for y in range(h):
        for x in range(w):
            if solid[y][x]:
                continue
            if on(x - 1, y) or on(x + 1, y) or on(x, y - 1) or on(x, y + 1):
                first.add((x, y))
    for x, y in first:
        px[x, y] = ink
    for y in range(h):
        for x in range(w):
            if solid[y][x] or (x, y) in first:
                continue
            for dx, dy in ((-1, 0), (0, -1)):
                if (x + dx, y + dy) in first and on(x + 2 * dx, y + 2 * dy):
                    px[x, y] = ink
                    break


# ================================================================= the figure
def figure(breath=0.0, drift=0.0, blink=False):
    """One idle frame. `breath` 0..1 lifts the chest and shoulders a texel and
    the head with them; `drift` moves the hair ends and the ribbon tails."""
    f = Figure()
    b = int(round(breath))          # texels the upper body rises
    hx, hy = CX, 68.0 - b           # face centre (between the eyes, a bit low)

    # ---------------------------------------------------------------- hair (back)
    hair = f.part("hair", HAIR, gain=2.6, ref=0.45, round_=0.3)
    rows = []
    for k, y in enumerate(range(40, 214, 6)):
        t = (y - 40) / 174.0
        w = 24 + 14 * math.sin(min(1.0, t * 1.6) * math.pi / 2) - 6 * max(0.0, t - 0.75) * 4
        wave = 2.6 * math.sin(y / 8.0 + 0.6)
        rows.append((y - b * (1 - t), hx + 0.3 * wave, w + wave, w - wave * 0.6))
    hair.profile(rows)
    # the ends: locks of different lengths, each a tapering tube that curls
    for i, (x0, ln, curl) in enumerate(((-30, 26, -1), (-21, 34, 1), (-11, 22, -1),
                                         (11, 24, 1), (20, 33, -1), (29, 27, 1))):
        X0, Y0 = hx + x0, 196.0 - b * 0.0
        pts = [(X0, Y0, 6.5)]
        for j in range(1, 5):
            t = j / 4.0
            pts.append((X0 + curl * 3.2 * math.sin(t * 3.0 + drift * 0.8) + drift * t * 2.0,
                        Y0 + ln * t, 6.5 * (1 - t) + 0.9))
        hair.tube(pts)

    # ---------------------------------------------------------------- legs
    def leg(name, hip, knee, ankle, out=1):
        p = f.part(name, SKIN, gain=2.4, ref=0.45, round_=0.25)
        (hx_, hy_), (kx, ky), (ax, ay) = hip, knee, ankle
        p.tube([(hx_, hy_, 13.5),
                (hx_ + (kx - hx_) * 0.35, hy_ + (ky - hy_) * 0.35, 12.6),
                (hx_ + (kx - hx_) * 0.75, hy_ + (ky - hy_) * 0.75, 10.4),
                (kx, ky, 8.6),
                (kx + (ax - kx) * 0.12, ky + (ay - ky) * 0.12, 8.4),
                (kx + (ax - kx) * 0.32 + out * 1.2, ky + (ay - ky) * 0.32, 9.4),
                (kx + (ax - kx) * 0.62, ky + (ay - ky) * 0.62, 7.0),
                (ax, ay, 5.0)])
        p.ellipse(kx + (ax - kx) * 0.42 - out * 3.2, ky + (ay - ky) * 0.42, 6.0, 13.0)
        return p
    leg_l = leg("leg_l", (CX - 12.0, 196.0), (CX - 13.5, 264.0), (CX - 12.0, 326.0), out=-1)
    leg_r = leg("leg_r", (CX + 11.0, 198.0), (CX + 13.5, 266.0), (CX + 17.0, 325.0), out=1)

    # ---------------------------------------------------------------- feet
    for nm, ax, ay, turn, inner in FEET:
        sole = f.part("sole_" + nm, SOLE, gain=1.6, ref=0.4)
        foot = f.part("foot_" + nm, SKIN, gain=2.0, ref=0.4, round_=0.6)
        tx = ax + turn
        foot.poly([(ax - 4.6, ay - 3), (ax + 4.6, ay - 3), (tx + 6.2, ay + 9),
                   (tx + 6.6, ay + 15), (tx - 6.6, ay + 15), (tx - 6.2, ay + 9)])
        foot.ellipse(tx + inner * 4.2, ay + 15.6, 2.5, 2.8)        # big toe
        for k in range(4):
            foot.ellipse(tx + inner * (0.8 - k * 2.0), ay + 15.4 - k * 0.5, 1.4, 2.3)
        sole.ellipse(tx, ay + 18.4, 8.4, 3.4, clip=lambda x, y, ay=ay: y > ay + 15.0)
        wrap = f.part("wrap_" + nm, WRAP, gain=1.8, ref=0.4, round_=0.2)
        wrap.ellipse(ax, ay - 1.5, 6.6, 2.6)
        for base_, tip, w in _leaves(ax, ay):
            wrap.poly(_leaf_outline(base_, tip, w))

    # ---------------------------------------------------------------- arms (back)
    def arm(name, sh, el, wr, r=(8.0, 5.6, 4.2)):
        p = f.part(name, SKIN, gain=2.4, ref=0.45, round_=0.4)
        p.tube([(sh[0], sh[1], r[0]),
                ((sh[0] + el[0]) / 2.0, (sh[1] + el[1]) / 2.0, r[0] - 0.8),
                (el[0], el[1], r[1]),
                (el[0] + (wr[0] - el[0]) * 0.35, el[1] + (wr[1] - el[1]) * 0.35, r[1] + 0.3),
                (wr[0], wr[1], r[2])])
        return p
    # her left arm (viewer's right): hand on the hip, elbow out
    arm_r = arm("arm_r", (CX + 24.0, 110.0 - b), (CX + 41.0, 150.0), (CX + 27.5, 182.0))

    # ---------------------------------------------------------------- torso
    torso = f.part("torso", SKIN, gain=2.4, ref=0.45, round_=0.3)
    torso.profile([(96 - b, CX, 8.0, 8.0), (101 - b, CX, 14.0, 14.0), (106 - b, CX, 23.0, 23.0),
                   (114 - b, CX, 23.5, 23.5), (126 - b * 0.5, CX, 22.5, 22.5),
                   (140, CX, 19.5, 19.5), (152, CX - 0.4, 17.0, 17.2), (162, CX - 1.0, 17.0, 17.6),
                   (174, CX - 1.6, 21.0, 21.5), (186, CX - 2.0, 26.5, 26.5),
                   (198, CX - 1.5, 27.5, 27.0), (206, CX - 1.0, 26.0, 26.0)])
    neck = f.part("neck", SKIN, gain=2.2, ref=0.45, round_=0.0)
    neck.profile([(80 - b, hx, 7.5, 7.5), (92 - b, hx, 7.6, 7.6), (100 - b, hx, 9.0, 9.0),
                  (104 - b, hx, 13.0, 13.0)])

    # ---------------------------------------------------------------- top
    top = f.part("top", TOP, gain=2.4, ref=0.45, round_=0.35)
    hem = lambda x: 141.0 + 1.6 * math.cos((x - CX) / 24.0 * math.pi * 0.5) - b * 0.5

    def neckline(x):
        d = min(abs(x - CX), 22.0)
        return (117.0 - b - 3.0 * math.sin(math.pi * d / 22.0)
                + 3.0 * max(0.0, 1.0 - d / 4.0) - 2.0 * max(0.0, d - 17.0))
    for y in range(100, 150):
        for x in range(int(CX - 30), int(CX + 31)):
            if torso.on(x, y) and neckline(x + 0.5) <= y + 0.5 <= hem(x + 0.5):
                top.set(x, y)
    for sx in (-1, 1):                                  # straps
        for y in range(int(99 - b), int(116 - b)):
            xs = CX + sx * (12.5 + (y - 99 + b) * 0.1)
            for x in (int(xs) - 1, int(xs)):
                if torso.on(x, y) or neck.on(x, y):
                    top.set(x, y)

    # ---------------------------------------------------------------- shorts
    shorts = f.part("shorts", SHORTS, gain=2.2, ref=0.42, round_=0.3)
    wb = lambda x: 171.0 + 1.5 * (1 - min(1.0, abs(x - CX) / 26.0))   # waistband dips

    def hem_y(x):
        """The shorts' lower edge: each leg opening dips to the outside, and
        the two meet at the crotch."""
        for cxl, sgn in ((CX - 12.5, -1), (CX + 12.0, 1)):
            if (x - CX) * sgn > 0:
                return 205.5 + 3.5 * ((x - cxl) * sgn / 14.0)
        return 201.0
    for y in range(160, 216):
        for x in range(int(CX - 34), int(CX + 34)):
            px, py = x + 0.5, y + 0.5
            if py < wb(px) or py > hem_y(px):
                continue
            near = (torso.on(x, y) or leg_l.on(x, y) or leg_r.on(x, y)
                    or (py > 186 and abs(px - CX) < 30.0))
            if near and abs(px - (CX - 1.0)) < 31.0:
                shorts.set(x, y)
    shorts.clear_where(lambda x, y: y > 200.0 and abs(x - CX) < (y - 200.0) * 1.3 + 0.6)
    f_hem = hem_y
    fringe = f.part("fringe", SHORTS, gain=1.2, ref=0.45, round_=0.0, contour=False)

    # ---------------------------------------------------------------- arms (front)
    # her right arm (viewer's left): hanging, relaxed, a slight bend
    arm_l = arm("arm_l", (CX - 24.0, 110.0 - b), (CX - 29.0, 158.0), (CX - 31.0, 198.0))
    hand_l = f.part("hand_l", SKIN, gain=2.2, ref=0.45, round_=0.5)
    hx0, hy0 = CX - 31.0, 198.0
    hand_l.poly([(hx0 - 4.6, hy0), (hx0 + 4.2, hy0), (hx0 + 5.6, hy0 + 8), (hx0 + 4.8, hy0 + 15),
                 (hx0 + 2.6, hy0 + 21), (hx0 - 0.6, hy0 + 23), (hx0 - 3.6, hy0 + 20),
                 (hx0 - 5.2, hy0 + 12)])
    hand_l.ellipse(hx0 + 4.6, hy0 + 9.0, 2.4, 5.0)   # thumb, toward her front
    # her left hand resting on the hip, fingers forward over the shorts
    hand_r = f.part("hand_r", SKIN, gain=2.2, ref=0.45, round_=0.5)
    wx, wy = CX + 27.5, 182.0
    hand_r.poly([(wx - 2.0, wy - 4.5), (wx + 4.5, wy - 2.5), (wx + 2.6, wy + 6.0),
                 (wx - 5.0, wy + 9.5), (wx - 11.0, wy + 8.0), (wx - 12.0, wy + 4.0),
                 (wx - 8.0, wy - 2.0)])

    # ---------------------------------------------------------------- head
    head = f.part("head", SKIN, gain=2.2, ref=0.42, round_=0.45)
    head.profile([(44 - b, hx, 17.0, 17.0), (54 - b, hx, 18.2, 18.2), (66 - b, hx, 18.4, 18.4),
                  (74 - b, hx, 17.2, 17.2), (82 - b, hx, 13.6, 13.6), (88 - b, hx, 8.4, 8.4),
                  (92 - b, hx, 3.6, 3.6)])

    # ---------------------------------------------------------------- hair (front)
    locks = f.part("locks", HAIR, gain=2.4, ref=0.42, round_=0.2)
    for sx in (-1, 1):
        x0 = hx + sx * 17.0
        locks.tube([(x0 - sx * 1.0, 46 - b, 4.2), (x0 + sx * 0.6, 62 - b, 4.8),
                    (x0 + sx * 0.2, 78 - b, 4.6), (x0 + sx * 2.2, 92 - b, 4.2),
                    (x0 + sx * 3.6, 102 - b, 3.0)])
    # the hairline: parted a little off centre, swept to both temples under
    # the brim, so the face is framed rather than capped
    for y in range(int(46 - b), int(68 - b)):
        for x in range(int(hx - 19), int(hx + 20)):
            dx = x + 0.5 - (hx - 2.0)
            if y + 0.5 < 53.0 - b + abs(dx) * 0.3 + (dx / 18.0) ** 4 * 7.0 and head.on(x, y):
                locks.set(x, y)
    # one long lock over her left shoulder (viewer's right), onto the chest
    locks.tube([(hx + 17.5, 92 - b, 4.4), (hx + 19.5, 108 - b, 5.0), (hx + 18.0, 124 - b, 4.6),
                (hx + 20.0 + drift * 0.6, 140 - b * 0.5, 3.8),
                (hx + 18.5 + drift * 1.0, 152, 1.6)])

    # ---------------------------------------------------------------- hat
    BX, BY, BRX, BRY = hx - 0.5, 40.0 - b, 57.0, 12.5
    brim = f.part("brim", STRAW, gain=1.6, ref=0.3, round_=0.15)
    brim.ellipse(BX, BY, BRX, BRY)
    brim.ellipse(BX, BY + 1.5, BRX - 0.5, BRY - 0.5)       # the lip's thickness
    crown = f.part("crown", STRAW, gain=2.0, ref=0.38, round_=0.6)
    CB = BY - 3.0                                          # where it sits
    crown.ellipse(BX, CB, 21.5, 26.0, clip=lambda x, y: y < CB)
    crown.ellipse(BX, CB, 21.5, 4.5)
    band = f.part("band", RIBBON, gain=1.8, ref=0.4, round_=0.0)

    def band_bot(x):
        u = (x - BX) / 21.5
        return CB + 4.5 * math.sqrt(max(0.0, 1 - u * u))
    for y in range(int(CB - 10), int(CB + 6)):
        for x in range(int(BX - 23), int(BX + 24)):
            if crown.on(x, y) and band_bot(x + 0.5) - 6.0 <= y + 0.5 <= band_bot(x + 0.5):
                band.set(x, y)

    # ---------------------------------------------------------------- shadows
    # the brim's shadow across the forehead and the top of the hair
    for x in range(CELL_W):
        u = (x + 0.5 - BX) / BRX
        if abs(u) >= 1:
            continue
        edge = BY + BRY * math.sqrt(1 - u * u)
        for y in range(int(edge), int(edge) + 10):
            d = 2.5 if y < edge + 5 else 1.2
            f.shade(x, y, -d, only=("head", "locks", "hair"))
    # under the chin onto the neck; the neck into the collar
    for x in range(int(hx - 10), int(hx + 11)):
        for y in range(int(89 - b), int(97 - b)):
            f.shade(x, y, -2 if y < 94 - b else -1, only=("neck",))
    # under the bust, under the hem onto the midriff
    for x in range(int(CX - 22), int(CX + 23)):
        h = hem(x + 0.5)
        for y in range(int(h) + 1, int(h) + 4):
            f.shade(x, y, -1, only=("torso",))
    # the shorts' shadow on the thighs, and between the thighs
    for x in range(int(CX - 34), int(CX + 34)):
        h = f_hem(x + 0.5)
        for y in range(int(h) + 1, int(h) + 7):
            f.shade(x, y, -1, only=("leg_l", "leg_r"))

    # ---------------------------------------------------------------- details
    _face(f, hx, hy, blink)
    _hat_detail(f, crown, band, brim, BX, BY, BRX, BRY, CB, band_bot, hx, b, drift)
    _hair_detail(f, hair, locks, hx, b, drift)
    _top_detail(f, top, neckline, hem, b)
    _shorts_detail(f, shorts, fringe, wb, hem_y, drift)
    _skin_detail(f, hx, b, torso, leg_l, leg_r)
    _hands(f, hand_l, hand_r, hx0, hy0, wx, wy)
    _feet(f)
    _jewellery(f, hx, b)
    return f


# ============================================================ face, texel by texel
SK = "skin"


def _face(f, hx, hy, blink):
    X, Y = int(math.floor(hx)), int(math.floor(hy))
    P = f.put
    only = ("head",)
    # eyes: (dx, dy, colour) for her right eye (viewer's left), outer corner
    # first; the other is its mirror. Lid and lash, white, a brown iris with a
    # darker rim, a pupil, a catch-light at the upper left, a lit lower iris.
    ink, white = INK, ("metal", 6)
    iris, iris_lo, rim = ("hair", 3.4), ("hair", 5.2), ("hair", 1.4)
    pupil, glint = ("hair", 0), ("metal", 6)
    lid, crease = ("skin", 1), ("skin", 2)
    open_eye = [
        # upper lid: a clean ink line, thicker over the iris, a lash flick
        (-12, -3, ink), (-11, -2, ink), (-10, -2, ink), (-9, -3, ink), (-8, -3, ink),
        (-7, -3, ink), (-6, -3, ink), (-5, -3, ink), (-4, -2, ink), (-3, -1, ink),
        (-8, -4, ink), (-7, -4, ink), (-6, -4, ink), (-13, -4, ink),
        # white at both corners, the iris filling the middle, glint upper left
        (-10, -1, white), (-11, -1, ("metal", 5)), (-10, 0, ("metal", 5)), (-4, -1, white),
        (-4, 0, ("metal", 5)),
        (-9, -2, rim), (-8, -2, rim), (-7, -2, rim), (-6, -2, rim), (-5, -2, rim),
        (-9, -1, iris), (-8, -1, glint), (-7, -1, pupil), (-6, -1, pupil), (-5, -1, iris),
        (-9, 0, iris), (-8, 0, pupil), (-7, 0, pupil), (-6, 0, pupil), (-5, 0, iris),
        (-9, 1, iris_lo), (-8, 1, iris_lo), (-7, 1, iris_lo), (-6, 1, iris_lo), (-5, 1, iris),
        (-8, 2, ("hair", 2)), (-7, 2, ("hair", 2)), (-6, 2, ("hair", 2)),
        # lower lid: a soft line, darker at the outer corner
        (-11, 0, lid), (-10, 1, lid), (-9, 2, crease), (-5, 2, crease), (-4, 1, crease),
        (-12, -1, ink),
        (-11, -5, crease), (-10, -5, crease), (-9, -6, crease), (-8, -6, crease),
        (-7, -6, crease), (-6, -6, crease), (-5, -5, crease),       # lid crease
    ]
    shut_eye = [
        (-13, -2, ink), (-12, -1, ink), (-11, 0, ink), (-10, 0, ink), (-9, 1, ink),
        (-8, 1, ink), (-7, 1, ink), (-6, 1, ink), (-5, 0, ink), (-4, 0, ink), (-3, -1, lid),
        (-10, 1, lid), (-5, 1, lid), (-8, 2, crease), (-7, 2, crease),
        (-10, -2, crease), (-9, -2, crease), (-8, -2, crease), (-7, -2, crease),
        (-6, -2, crease), (-5, -2, crease),
    ]
    for sx in (-1, 1):
        for dx, dy, col in (shut_eye if blink else open_eye):
            # the viewer's right eye is the mirror; its glint stays upper left
            if sx > 0 and col == glint:
                col = pupil
            if sx > 0 and (dx, dy) == (-5, -1):
                col = glint
            P(X + (dx if sx < 0 else -dx - 1), Y + dy, col, only)
    # brows: arched, thicker toward the nose, hair-coloured
    brow = ("hair", 1)
    for sx in (-1, 1):
        for dx, dy, c in ((-12, -6, ("hair", 2)), (-11, -7, brow), (-10, -8, brow),
                          (-9, -8, brow), (-8, -9, brow), (-7, -9, brow), (-6, -9, brow),
                          (-5, -8, brow), (-4, -8, brow), (-4, -7, brow), (-3, -7, ("hair", 2)),
                          (-6, -8, ("hair", 2)), (-7, -8, ("hair", 2))):
            P(X + (dx if sx < 0 else -dx - 1), Y + dy, c, only)
    # nose: a lit bridge and tip on the left, a shadow down the right side,
    # two nostrils, a soft shadow under the tip
    for dy in range(0, 6):
        P(X - 1, Y + dy, (SK, 4), only)
        P(X + 1, Y + dy + 1, (SK, 2), only)
    P(X, Y + 6, (SK, 4.6), only)
    P(X - 1, Y + 6, (SK, 4), only)
    P(X + 1, Y + 7, (SK, 2), only)
    P(X + 2, Y + 7, (SK, 2), only)
    P(X - 2, Y + 8, ("skin", 1), only)
    P(X + 2, Y + 8, ("skin", 1), only)
    P(X - 1, Y + 9, (SK, 2), only)
    P(X, Y + 9, (SK, 2), only)
    P(X + 1, Y + 9, (SK, 2), only)
    # mouth: a warm, closed-corner smile showing a line of teeth
    lipd, lip, lipl = ("ember", 2), ("ember", 3.6), ("ember", 4.6)
    teeth = ("metal", 6)
    mouth = [(-6, 12, lipd), (-5, 13, lipd), (5, 12, lipd), (4, 13, lipd),
             (-4, 13, lipd), (-3, 13, lipd), (-2, 13, lipd), (-1, 13, lipd), (0, 13, lipd),
             (1, 13, lipd), (2, 13, lipd), (3, 13, lipd),
             (-3, 14, teeth), (-2, 14, teeth), (-1, 14, teeth), (0, 14, teeth), (1, 14, teeth),
             (2, 14, ("metal", 5)), (-4, 14, lipd), (3, 14, lipd),
             (-3, 15, lip), (-2, 15, lipl), (-1, 15, lipl), (0, 15, lip), (1, 15, lip),
             (2, 15, lip), (-2, 16, ("skin", 2)), (-1, 16, ("skin", 2)), (0, 16, ("skin", 2)),
             (1, 16, ("skin", 2)),
             (-2, 12, lip), (-1, 12, ("ember", 3)), (0, 12, lip), (1, 12, ("ember", 3)),
             (-6, 11, (SK, 2)), (6, 11, (SK, 2))]                # smile dimples
    for dx, dy, c in mouth:
        P(X + dx, Y + dy, c, only)
    # cheeks: a warm blush, three texels on the apple of each cheek
    for sx in (-1, 1):
        for dx, dy, c in ((-11, 5, ("ember", 5)), (-9, 5, ("ember", 5)),
                          (-10, 5, (SK, 4.4)), (-12, 5, (SK, 4)), (-10, 6, (SK, 4))):
            P(X + (dx if sx < 0 else -dx - 1), Y + dy, c, only)


def _hat_detail(f, crown, band, brim, BX, BY, BRX, BRY, CB, band_bot, hx, b, drift):
    P = f.put
    # brim: the weave runs round it in rings, each ring stitched over-under;
    # a sunlit lip on the upper-left edge, the underside along the front
    for y in range(int(BY - BRY - 2), int(BY + BRY + 3)):
        for x in range(int(BX - BRX - 1), int(BX + BRX + 2)):
            if f.top_name(x, y) != "brim":
                continue
            u = (x + 0.5 - BX) / BRX
            v = (y + 0.5 - BY) / BRY
            r = math.sqrt(u * u + v * v)
            ring = (r - 0.38) * 14.0
            if ring < 0:
                continue
            k = int(ring)
            frac = ring - k
            ang = math.atan2(v * BRY, u * BRX)
            seg = int((ang + math.pi) * (BRX * r) / 3.0 + (k % 2) * 0.5)
            lit = (u + v * 1.4) < -0.1
            if frac < 0.22:
                P(x, y, ("straw", 2.6 if lit else 2.2))
            elif (x + 3 * k) % 5 == 0 and 0.35 < frac < 0.8:
                P(x, y, ("straw", 4.8 if lit else 4.0))
    for x in range(CELL_W):
        u = (x + 0.5 - BX) / BRX
        if abs(u) >= 1:
            continue
        e = BY + 1.5 + (BRY - 0.5) * math.sqrt(max(0.0, 1 - ((x + 0.5 - BX) / (BRX - 0.5)) ** 2))
        ye = int(e)
        for y, c in ((ye, ("straw", 1.0)), (ye - 1, ("straw", 1.6)), (ye - 2, ("straw", 2.4))):
            if f.top_name(x, y) == "brim":
                P(x, y, c)
        top_e = BY - BRY * math.sqrt(1 - u * u)
        if u < 0.3:
            P(x, int(top_e) + 1, ("straw", 6 if u < -0.2 else 5), only=("brim",))
    for k in range(17):                                       # frayed straws
        u = -0.96 + k * 0.12
        if k % 4 != 1:
            continue
        x = BX + u * BRX
        e = BY + 1.5 + (BRY - 0.5) * math.sqrt(max(0.0, 1 - u * u))
        f.line([(x, e), (x + u * 3.0, e + 2.5)], ("straw", 3))
    # crown: an over-under basket weave in rows that follow its curve
    for y in range(int(CB - 27), int(CB + 6)):
        for x in range(int(BX - 23), int(BX + 24)):
            if f.top_name(x, y) != "crown":
                continue
            u = (x + 0.5 - BX) / 21.5
            # rows bend with the dome: flatter near the top
            yy = y + 0.5 - 3.0 * (1 - math.sqrt(max(0.0, 1 - u * u)))
            row = int(math.floor(yy / 4.0))
            ph = int(math.floor(yy)) % 4
            cx = x + 2 * (row % 2)
            lit = u < -0.1
            if ph == 0:
                P(x, y, ("straw", 2.4))
            elif cx % 4 == 0:
                P(x, y, ("straw", 2.8))
            elif ph == 1 and lit:
                P(x, y, ("straw", 5.0))
    # the ribbon band: a lit upper edge, a dark lower one, a bow on her left
    for x in range(int(BX - 23), int(BX + 24)):
        bb = band_bot(x + 0.5)
        P(x, int(bb - 6.0) + 1, ("dirt", 3.6), only=("band",))
        P(x, int(bb) - 1, ("dirt", 0.8), only=("band",))
    kx, ky = BX + 13.0, int(band_bot(BX + 13.0)) - 3
    bow = [
        "..kk.....kk..",
        ".kNnk...kNnk.",
        "kNnnnk.knnnDk",
        "knnnnDkkDnnDk",
        "knnnDDKKDDnDk",
        ".kDDkkKKkkDk.",
        "..kk.kDDk.kk.",
        ".....kDDk....",
    ]
    pal = {'k': INK, 'n': ("dirt", 2.4), 'N': ("dirt", 3.8), 'D': ("dirt", 1.2),
           'K': ("dirt", 3.0)}
    for j, row in enumerate(bow):
        for i, ch in enumerate(row):
            if ch != '.':
                P(kx - 6 + i, ky - 4 + j, pal[ch])
    # the tails hang over the brim and lift a little in the breeze
    for t0, ln, dx in ((-1.0, 9.0, 1.0), (1.0, 7.0, 6.0)):
        x0, y0 = kx + t0, ky + 4
        pts = [(x0 + (dx + drift * 2.5) * (j / 6.0) + 0.8 * math.sin(j * 0.9), y0 + ln * j / 6.0)
               for j in range(7)]
        for j, (x, y) in enumerate(pts):
            w = 2 if j < 6 else 1
            for k in range(-w, w + 1):
                c = ("dirt", 3.4 if k < 0 else 2.0)
                if abs(k) == w:
                    c = INK
                P(x + k, y, c)
            if j < 6:
                nx, ny = pts[j + 1]
                for k in range(-w, w + 1):
                    P((x + nx) / 2.0 + k, (y + ny) / 2.0,
                      INK if abs(k) == w else ("dirt", 3.4 if k < 0 else 2.0))
        lx, ly = pts[-1]
        P(lx - 1, ly + 1, INK)
        P(lx + 1, ly + 1, INK)
        P(lx, ly + 1, ("dirt", 1.0))


def _hair_detail(f, hair, locks, hx, b, drift):
    """Strands: grooves that follow the wave, and a sheen down the lit side
    of each lock."""
    for lane in range(-5, 6):
        off = lane * 5.6
        pts = []
        for i in range(30):
            y = 44 + i * 6.0
            x = hx + off * (1.0 + i / 60.0) + 2.6 * math.sin(y / 8.0 + 0.6 + lane * 0.7)
            pts.append((x, y))
        groove = ("hair", 1.0)
        sheen = ("hair", 4.4 if lane < 0 else 3.6)
        f.curve(pts, groove, only=("hair",), n=180)
        for (x, y) in pts:
            if math.sin(y / 8.0 + 0.6 + lane * 0.7) > 0.35:
                f.put(x - 2, y, sheen, only=("hair",))
                f.put(x - 2, y + 1, sheen, only=("hair",))
                f.put(x - 3, y + 2, ("hair", 3.4), only=("hair",))
    for sx in (-1, 1):                                        # face-framing locks
        x0 = hx + sx * 17.0
        f.curve([(x0 - sx * 1.0, 48 - b), (x0 + sx * 0.6, 62 - b), (x0 + sx * 0.2, 78 - b),
                 (x0 + sx * 2.2, 92 - b)], ("hair", 1.0), only=("locks",))
        f.curve([(x0 - sx * 1.0 - 2, 50 - b), (x0 + sx * 0.6 - 2, 62 - b),
                 (x0 + sx * 0.2 - 2, 72 - b)], ("hair", 4.6), only=("locks",))
    f.curve([(hx + 19.0, 96 - b), (hx + 20.5, 108 - b), (hx + 19.0, 124 - b),
             (hx + 20.5 + drift * 0.6, 138 - b)], ("hair", 1.0), only=("locks",))
    f.curve([(hx + 16.5, 98 - b), (hx + 17.5, 110 - b), (hx + 16.0, 124 - b)],
            ("hair", 4.6), only=("locks",))
    # the parting and the hair swept from it to each temple
    for sx in (-1, 1):
        for k in range(3):
            f.curve([(hx - 2.0 + sx * (1 + k * 3), 50 - b),
                     (hx - 2.0 + sx * (7 + k * 4), 53 - b + k),
                     (hx - 2.0 + sx * (13 + k * 2), 58 - b + k * 2)],
                    ("hair", 1.0 if k != 1 else 4.2), only=("locks",), n=24)
    f.line([(hx - 2, 49 - b), (hx - 2, 53 - b)], ("hair", 0.6), only=("locks",))


def _top_detail(f, top, neckline, hem, b):
    P = f.put
    # the hem, lit, with the shadow line just above it
    for x in range(int(CX - 26), int(CX + 27)):
        h = int(hem(x + 0.5))
        if f.top_name(x, h) == "top":
            P(x, h, ("cloth", 4.6))
            P(x, h - 1, ("cloth", 2.0))
    # the neckline's piped edge
    for x in range(int(CX - 24), int(CX + 25)):
        n = int(math.ceil(neckline(x + 0.5) - 0.5))
        P(x, n, ("cloth", 5.4), only=("top",))
    # a gather between the cups, a fold under each, tension pulls to the sides
    f.curve([(CX - 0.5, 118 - b), (CX, 124 - b), (CX - 0.5, 131 - b)], ("cloth", 1.6),
            only=("top",))
    f.curve([(CX + 1, 119 - b), (CX + 1.5, 125 - b)], ("cloth", 4.0), only=("top",))
    for sx in (-1, 1):
        # each cup: a shadow round its underside, a lit upper curve (brighter
        # on the left, toward the light), and a pull out to the side seam
        f.curve([(CX + sx * 1.5, 126 - b), (CX + sx * 6, 131 - b * 0.5),
                 (CX + sx * 12, 132 - b * 0.5), (CX + sx * 18, 128 - b)],
                ("cloth", 1.8), only=("top",))
        f.curve([(CX + sx * 2.5, 126 - b), (CX + sx * 6.5, 130 - b * 0.5),
                 (CX + sx * 12, 131 - b * 0.5)], ("cloth", 2.4), only=("top",))
        f.curve([(CX + sx * 4, 120 - b), (CX + sx * 9, 117.5 - b), (CX + sx * 14, 118.5 - b)],
                ("cloth", 5.0 if sx < 0 else 4.2), only=("top",))
        f.curve([(CX + sx * 5, 121 - b), (CX + sx * 9, 119.5 - b)],
                ("cloth", 4.2 if sx < 0 else 3.6), only=("top",))
        f.curve([(CX + sx * 17, 121 - b), (CX + sx * 20, 128 - b)], ("cloth", 2.2),
                only=("top",))
        # a soft fold from under the cup to the hem
        f.curve([(CX + sx * 9, 134 - b * 0.5), (CX + sx * 11, 138 - b * 0.5)],
                ("cloth", 2.4), only=("top",))
    # strap highlights
    for sx in (-1, 1):
        for y in range(int(99 - b), int(113 - b)):
            xs = CX + sx * (12.5 + (y - 99 + b) * 0.1)
            P(int(xs) - 1, y, ("cloth", 5.0 if sx < 0 else 4.2), only=("top",))


def _shorts_detail(f, shorts, fringe, wb, hem_y, drift):
    P = f.put
    # waistband: five texels, lit top, stitched, with belt loops and a button
    for x in range(int(CX - 32), int(CX + 32)):
        w = int(wb(x + 0.5))
        for k in range(5):
            if f.top_name(x, w + k) != "shorts":
                continue
            if k == 0:
                P(x, w + k, ("gold", 6))
            elif k == 4:
                P(x, w + k, ("gold", 3))
            elif k == 2 and x % 3 == 0:
                P(x, w + k, ("gold", 3.4))
    for lx in (-21, 20):                                      # belt loops
        x = CX + lx
        w = int(wb(x))
        for k in range(0, 6):
            P(x, w + k, ("gold", 5.6 if k < 3 else 4.6), only=("shorts",))
            P(x + 1, w + k, ("gold", 3.2), only=("shorts",))
    bx, by = int(CX - 1), int(wb(CX)) + 1
    for dx, dy, c in ((0, 0, ("gold", 3)), (1, 0, ("gold", 3)), (-1, 1, ("gold", 3)),
                      (0, 1, ("gold", 6)), (1, 1, ("gold", 4)), (2, 1, ("gold", 2)),
                      (0, 2, ("gold", 2)), (1, 2, ("gold", 2))):
        P(bx + dx, by + dy, c)
    # fly: a seam with a stitched flap, curving into the crotch
    f.line([(CX - 1, by + 4), (CX - 1, 199)], ("gold", 3.0), only=("shorts",))
    f.curve([(CX + 3.5, by + 5), (CX + 4, 190), (CX + 0.5, 197)], ("gold", 3.6),
            only=("shorts",))
    # pocket openings, a pull from each hip toward the crotch
    for sx in (-1, 1):
        f.curve([(CX + sx * 13, 177), (CX + sx * 19, 183), (CX + sx * 25, 184)],
                ("gold", 3.4), only=("shorts",))
        f.curve([(CX + sx * 3, 198), (CX + sx * 9, 194), (CX + sx * 15, 194)],
                ("gold", 4.0), only=("shorts",))
    # a lit stripe above each leg's hem, then the fringe: tassels hanging from
    # the hem, alternately long and short, swinging with the breeze
    for x in range(int(CX - 33), int(CX + 34)):
        ys = [y for y in range(196, 214) if f.top_name(x, y) == "shorts"]
        if not ys:
            continue
        y = max(ys)
        if y < 202:
            continue
        P(x, y - 3, ("gold", 6))
        P(x, y - 2, ("gold", 5.4))
        P(x, y, ("gold", 3.4))
        ln = 4 + (2 if x % 2 else 0) + (1 if x % 5 == 0 else 0)
        sw = drift * 1.2
        for k in range(1, ln):
            xx = x + int(round(sw * k / ln))
            fringe.set(xx, y + k)
            c = ("gold", 4.6 if x % 2 == 0 else 3.8) if k < ln - 1 else ("gold", 5.4)
            if (x + k) % 4 == 0 and k < ln - 1:
                c = ("gold", 3.2)
            f.paint[(xx, y + k)] = c


def _skin_detail(f, hx, b, torso, leg_l, leg_r):
    P = f.put
    # collarbones, a soft line from the throat out to each shoulder
    for sx in (-1, 1):
        f.curve([(hx + sx * 3, 102 - b), (hx + sx * 9, 103 - b), (hx + sx * 15, 102 - b)],
                ("skin", 2.2), only=("torso", "neck"))
        f.curve([(hx + sx * 4, 103 - b), (hx + sx * 9, 104 - b)], ("skin", 4.4),
                only=("torso",))
    # navel and the soft line of the midriff
    P(CX - 1, 160, ("skin", 1))
    P(CX - 1, 161, ("skin", 1.6))
    P(CX - 2, 160, ("skin", 2))
    P(CX - 1, 162, ("skin", 4))
    f.line([(CX - 1, 146), (CX - 1, 156)], ("skin", 2.6), only=("torso",))
    # knees: a lit cap over a shadow crease; shin light down the near side
    for lg, kx, ky in ((leg_l, CX - 13.5, 264.0), (leg_r, CX + 13.5, 266.0)):
        f.curve([(kx - 4, ky - 3), (kx - 1, ky - 5), (kx + 2, ky - 4)], ("skin", 4.4),
                only=(lg.name,))
        f.curve([(kx - 4, ky + 3), (kx, ky + 5), (kx + 3, ky + 3)], ("skin", 2.0),
                only=(lg.name,))
    # the inner thigh shadow line where the legs meet
    for y in range(206, 240):
        for x in range(int(CX - 6), int(CX + 6)):
            if f.top_name(x, y) == "leg_l" and f.top_name(x + 1, y) == "leg_r":
                P(x, y, ("skin", 1))


def _hands(f, hand_l, hand_r, hx0, hy0, wx, wy):
    P = f.put
    # the hanging hand: four fingers seen edge-on, the thumb in front of them
    for k, (x0, y0, x1, y1) in enumerate(((-3.5, 12, -3.0, 19), (-1.0, 13, -0.5, 21),
                                          (1.6, 13, 1.8, 20))):
        f.line([(hx0 + x0, hy0 + y0), (hx0 + x1, hy0 + y1)], ("skin", 1.6), only=("hand_l",))
    f.curve([(hx0 + 2.6, hy0 + 4), (hx0 + 3.4, hy0 + 10), (hx0 + 3.0, hy0 + 14)],
            ("skin", 1.4), only=("hand_l",))
    for dx, dy in ((-3, 4), (-3, 5), (-2, 3), (-4, 8)):
        P(hx0 + dx, hy0 + dy, ("skin", 4.4), only=("hand_l",))
    P(hx0 + 5, hy0 + 6, ("skin", 4.6), only=("hand_l",))
    # the hand on the hip: knuckles and fingers wrapped forward over the shorts
    for k in range(4):
        x = wx - 10.0 + k * 2.6
        f.line([(x, wy + 2.0 - k * 0.6), (x - 0.4, wy + 7.0 - k * 0.8)], ("skin", 1.6),
               only=("hand_r",))
        P(x + 1, wy + 1.5 - k * 0.7, ("skin", 4.4), only=("hand_r",))
    f.curve([(wx - 1.5, wy - 3.5), (wx + 2.0, wy - 1.0), (wx + 2.6, wy + 3.0)],
            ("skin", 4.4), only=("hand_r",))


def _feet(f):
    P = f.put
    for _, ax, ay, turn, inner in FEET:
        # leaf wraps: each blade gets a lit left edge, a dark right edge that
        # separates it from the next, and a midrib; then the binding cord
        for base_, tip, w in _leaves(ax, ay):
            ol = _leaf_outline(base_, tip, w)
            n = len(ol) // 2
            f.line(ol[:n], ("cloth", 4.8), only=("wrap_l", "wrap_r"))
            f.line(ol[n:], ("cloth", 1.0), only=("wrap_l", "wrap_r"))
            (bx, by), (tx2, ty2) = base_, tip
            f.line([(bx, by), (bx + (tx2 - bx) * 0.8, by + (ty2 - by) * 0.8)], ("cloth", 2.0),
                   only=("wrap_l", "wrap_r"))
        for x in range(int(ax - 7), int(ax + 8)):
            P(x, ay - 1.0, ("dirt", 2.0), only=("wrap_l", "wrap_r"))
            P(x, ay - 2.0, ("dirt", 4.0) if x % 3 == 0 else ("dirt", 3.0),
              only=("wrap_l", "wrap_r"))
        # sandal: a thong between the big toe and the next, two thin straps
        # out to the sole on either side
        tx = ax + turn
        mx, my = tx + inner * 2.6, ay + 13.0
        for side_ in (-1, 1):
            f.line([(mx, my), (ax + side_ * 5.0, ay + 3.0)], ("ember", 4.2),
                   only=("foot_l", "foot_r"))
            f.line([(mx, my + 1), (ax + side_ * 5.0, ay + 4.0)], ("ember", 2.2),
                   only=("foot_l", "foot_r"))
        P(mx, my, ("ember", 5))
        # toes: a crease between each, a lit nail on each
        P(tx + inner * 2.6, ay + 16, ("skin", 1.4), only=("foot_l", "foot_r"))
        for k in range(4):
            x = tx + inner * (0.8 - k * 2.0)
            P(x, ay + 16.5 - k * 0.5, ("skin", 4.8), only=("foot_l", "foot_r"))
            P(x + inner * -1.0, ay + 16.5 - k * 0.5, ("skin", 1.8), only=("foot_l", "foot_r"))
        P(tx + inner * 4.2, ay + 16.5, ("skin", 5.0), only=("foot_l", "foot_r"))
        P(tx + inner * 4.2 - 1, ay + 16.5, ("skin", 4.4), only=("foot_l", "foot_r"))
        for x in range(int(tx - 9), int(tx + 10)):
            P(x, ay + 20, ("ember", 1.4), only=("sole_l", "sole_r"))
            P(x, ay + 17, ("ember", 4.0), only=("sole_l", "sole_r"))


def _jewellery(f, hx, b):
    P = f.put
    # gold hoops hanging from the lobes, in front of the hair: a clean ring,
    # bright on its upper-left arc, darker underneath, a glint
    for sx in (-1, 1):
        ex, ey, r = hx + sx * 18.5, 87.5 - b, 3.7
        for y in range(int(ey - r - 2), int(ey + r + 2)):
            for x in range(int(ex - r - 2), int(ex + r + 2)):
                dx, dy = x + 0.5 - ex, (y + 0.5 - ey) * 0.92
                d = math.hypot(dx, dy)
                if abs(d - r) < 0.62:
                    a = math.atan2(dy, dx)
                    lvl = 5.4 if -2.6 < a < -0.5 or (dx < 0 and dy < 0) else (
                        4.0 if dy < 1.5 else 3.0)
                    P(x, y, ("gold", lvl))
        P(ex - 2.0, ey - 2.5, ("gold", 6.0))
        P(ex - 0.5, ey - r - 1.0, ("gold", 3.0))
    # bead necklace: round ember beads on a dark cord, hanging in a curve
    # below the collarbones; each bead lit upper left, the middle one larger
    bead = ["..ab..", ".aLbb.", ".bbbc.", "..cc.."]
    big = [".abb.", "aLbbb", "bbbbc", "bbbcc", ".ccc."]
    pal = {'a': ("ember", 5.2), 'L': ("ember", 6), 'b': ("ember", 4.6), 'c': ("ember", 3.2)}
    pts = []
    for k in range(-5, 6):
        t = k / 5.5
        pts.append((k, hx + t * 15.5, 105.0 - b + 7.0 * (1 - t * t)))
    for (k0, x0, y0), (k1, x1, y1) in zip(pts, pts[1:]):
        f.line([(x0, y0 + 1), (x1, y1 + 1)], ("hair", 1))
    for k, x, y in pts:
        g = big if k == 0 else bead
        ox, oy = int(x) - len(g[0]) // 2, int(y) - 1
        for j, row in enumerate(g):
            for i, ch in enumerate(row):
                if ch != '.':
                    P(ox + i, oy + j, pal[ch])


# ================================================================= the sheet
def frames():
    poses = (dict(), dict(breath=1.0, drift=0.6), dict(drift=1.2), dict(blink=True))
    return [figure(**p).render() for p in poses]


def build():
    """Writes assets/sprites/title_kaya.png natively at ART_SCALE. Saved
    directly rather than through `palette.sheet()`, like the HUD portrait:
    each frame has already been through `selective_outline()` in `render()`,
    and this is a picture for a menu, not a sheet the game animates in the
    world."""
    s = palette.ART_SCALE
    assert CELL_W % s == 0 and CELL_H % s == 0
    cells = frames()
    img = Image.new("RGBA", (CELL_W * len(cells), CELL_H), (0, 0, 0, 0))
    for i, c in enumerate(cells):
        img.alpha_composite(c, (i * CELL_W, 0))
    img.save(os.path.join(palette.SPRITES, "title_kaya.png"))
    print("title_kaya.png  %d frames of %dx%d texels (%dx%d world units)"
          % (len(cells), CELL_W, CELL_H, CELL_W // s, CELL_H // s))


if __name__ == "__main__":
    out = frames()[0]
    out.save(os.environ.get("OUT", "/tmp/title_kaya.png"))
