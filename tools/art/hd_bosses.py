"""The five bosses drawn natively at ART_SCALE (docs/plan-hd.md, phase H1).

Same animals, same poses, same numbers. Every boss here is the puppet in
tools/art/enemies40.py -- its PHASES and POSES dicts are imported, not copied
-- re-drawn on an `HDCanvas`, which takes the 1x (world-unit) coordinates the
puppet was written in and rasterises them at ART_SCALE. So a frame's
silhouette, its fit over the unchanged hitbox and every tell are the 1x
frame's, sampled twice as finely; what is new is what a 64x64 cell could not
hold, drawn in native texels:

  GROVE WARDEN    pitted chitin with growth lines and a sheen, ringed horns,
                  a pupil and a catch-light, serrated mandibles, jointed legs
                  with spurs and two-pronged claws, veined wing membranes,, cracks that glow into the shell
  TIDE MAW        mottled skin with pores and a row of photophores, a fin with
                  rays, needle teeth with a root and a glassy tip, gums and a
                  throat, a glossy eye, a lure with a hot core
  STORMCREST      scalloped body feathers, separated primaries with shafts,
                  crest feathers with a rachis, a brow ridge over a real eye,
                  a cere and a nostril on the beak, scaled legs and talons
  BROOD QUEEN     stretch striations and spiracles on every band, faceted
                  compound eyes, antennae, serrated sickles, jointed legs
  OBSIDIAN HEART  facet planes with cold edges and hard glints on the glass,
                  forked cracks that light the glass round them, a core with
                  rings and rays

Lighting is the bosses' 1x lighting (`auto_shade(depth=3, rate=1, lit=1,
dark=1)`) carried to the finer grid the way the approved look sample does it
(`kaya40.shade_hd`): volume measured over twice the texels, so depth doubles
and the rate halves; whole ramp steps, never a Bayer dither; the lit and the
shadowed edge two texels deep with a step inside. The ink line is the look
sample's weighted outline: one texel all round and a second on the shadow
side, so the line keeps its 1x weight where the form turns away from the light.

Sheets keep their names, frame order and world-unit cell (64x64 in
data/enemies/*.json); only the texels per unit change.
"""

import math

from PIL import Image

from . import palette
from . import enemies40 as e40
from .enemies40 import BW, BH, BFLOOR, lerp, polar, limb

S = palette.ART_SCALE
HW, HH = BW * S, BH * S


# ====================================================================== canvas
class HDCanvas(e40.Canvas):
    """A Canvas whose drawing calls take world units and rasterise at S.
    `t()` and `stroke()` work in native texels; `line()`, `arc()` and `dot()`
    take world units but draw one texel wide, for the details that only
    exist at this size."""

    def __init__(self, w=BW, h=BH, s=S):
        self.s = s
        self.w, self.h = w * s, h * s
        self.g = [['.'] * self.w for _ in range(self.h)]

    # ---- 1x primitives, rasterised at S
    def px(self, x, y, ch):
        """One world unit: an S x S block."""
        x0, y0 = int(math.floor(x)) * self.s, int(math.floor(y)) * self.s
        for dy in range(self.s):
            for dx in range(self.s):
                self.set(x0 + dx, y0 + dy, ch)

    def capsule(self, a, b, r0, ch, r1=None, only=None):
        s = self.s
        r1 = r0 if r1 is None else r1
        ax, ay, bx, by = a[0] * s, a[1] * s, b[0] * s, b[1] * s
        r0, r1 = r0 * s, r1 * s
        dx, dy = bx - ax, by - ay
        l2 = dx * dx + dy * dy or 1e-9
        rr = max(r0, r1)
        for y in range(int(min(ay, by) - rr - 1), int(max(ay, by) + rr + 2)):
            if not 0 <= y < self.h:
                continue
            for x in range(int(min(ax, bx) - rr - 1), int(max(ax, bx) + rr + 2)):
                if not 0 <= x < self.w:
                    continue
                px, py = x + 0.5, y + 0.5
                t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
                qx, qy = ax + t * dx, ay + t * dy
                r = r0 + (r1 - r0) * t
                if (px - qx) ** 2 + (py - qy) ** 2 <= r * r:
                    if only is None or self.g[y][x] in only:
                        self.g[y][x] = ch

    def ellipse(self, c, rx, ry, ch, ang=0.0, clip=None, only=None):
        s = self.s
        cx, cy, rx, ry = c[0] * s, c[1] * s, rx * s, ry * s
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        rr = max(rx, ry)
        for y in range(int(cy - rr - 1), int(cy + rr + 2)):
            if not 0 <= y < self.h:
                continue
            for x in range(int(cx - rr - 1), int(cx + rr + 2)):
                if not 0 <= x < self.w:
                    continue
                px, py = x + 0.5 - cx, y + 0.5 - cy
                u = px * ca + py * sa
                v = -px * sa + py * ca
                if (u / rx) ** 2 + (v / ry) ** 2 <= 1.0:
                    if clip is None or clip((x + 0.5) / s, (y + 0.5) / s):
                        if only is None or self.g[y][x] in only:
                            self.g[y][x] = ch

    def poly(self, pts, ch, only=None):
        s = self.s
        pts = [(p[0] * s, p[1] * s) for p in pts]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        n = len(pts)
        for y in range(max(0, int(min(ys)) - 1), min(self.h, int(max(ys)) + 2)):
            py = y + 0.5
            cuts = []
            j = n - 1
            for i in range(n):
                xi, yi = pts[i]
                xj, yj = pts[j]
                if (yi > py) != (yj > py):
                    cuts.append((xj - xi) * (py - yi) / (yj - yi) + xi)
                j = i
            cuts.sort()
            for k in range(0, len(cuts) - 1, 2):
                for x in range(max(0, int(math.floor(cuts[k] - 0.5)) + 1),
                               min(self.w, int(math.floor(cuts[k + 1] - 0.5)) + 1)):
                    if cuts[k] <= x + 0.5 < cuts[k + 1]:
                        if only is None or self.g[y][x] in only:
                            self.g[y][x] = ch

    # ---- native texels
    def t(self, x, y, ch, only=None):
        """One native texel at native coordinates."""
        x, y = int(math.floor(x)), int(math.floor(y))
        if 0 <= x < self.w and 0 <= y < self.h:
            if only is None or self.g[y][x] in only:
                self.g[y][x] = ch

    def stroke(self, pts, ch, only=None):
        """A one-texel line through native points."""
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
            for k in range(n + 1):
                u = k / max(n, 1)
                self.t(x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, ch, only)

    def dot(self, x, y, ch, only=None):
        """One texel at a world point."""
        self.t(x * self.s, y * self.s, ch, only)

    def line(self, pts, ch, only=None):
        """A one-texel line through world points."""
        self.stroke([(x * self.s, y * self.s) for x, y in pts], ch, only)

    def arc(self, c, rx, ry, a0, a1, ch, only=None, ang=0.0):
        """A one-texel elliptical arc in world units. Angles in degrees,
        0 = +x, 90 = +y (down); `ang` rotates the ellipse as ellipse() does."""
        n = int(max(rx, ry) * self.s * abs(a1 - a0) / 40.0) + 3
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        pts = []
        for k in range(n + 1):
            a = math.radians(lerp(a0, a1, k / n))
            u, v = math.cos(a) * rx, math.sin(a) * ry
            pts.append((c[0] + u * ca - v * sa, c[1] + u * sa + v * ca))
        self.line(pts, ch, only)

    def outline(self, ink='k'):
        """The look sample's weighted line (kaya40.HDCanvas.outline): one
        texel all round, a second on the shadow side (right and below)."""
        out = [row[:] for row in self.g]
        for y in range(self.h):
            for x in range(self.w):
                if self.g[y][x] != '.':
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if self.get(x + dx, y + dy) not in '.' + ink:
                        out[y][x] = ink
                        break
        self.g = out
        out = [row[:] for row in self.g]
        for y in range(self.h):
            for x in range(self.w):
                if self.g[y][x] != '.':
                    continue
                for dx, dy in ((-1, 0), (0, -1)):
                    if (self.get(x + dx, y + dy) == ink
                            and self.get(x + 2 * dx, y + 2 * dy) not in '.' + ink):
                        out[y][x] = ink
                        break
        self.g = out


# ===================================================================== helpers
def local(c0, ang, u, v):
    """The world point at (u, v) in the frame of an ellipse centred on `c0`
    and rotated by `ang` degrees, as HDCanvas.ellipse() rotates one."""
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    return (c0[0] + u * ca - v * sa, c0[1] + u * sa + v * ca)


def rim_hd(c, body, ch, depth=None):
    """enemies40.rim() at S: re-paint the top edge of everything in `body`
    with `ch`, `depth` texels deep (default one world unit, as at 1x)."""
    depth = depth or c.s
    marks = []
    for y in range(c.h):
        for x in range(c.w):
            if c.g[y][x] in body and c.get(x, y - 1) not in body:
                for k in range(depth):
                    if c.get(x, y + k) in body:
                        marks.append((x, y + k))
    for x, y in marks:
        c.g[y][x] = ch


def dust_hd(c, n, seed, ch, y=62.6, x0=6, x1=58):
    """enemies40.dust(): the same specks in the same places, each a little
    clod of three or four texels instead of a square world unit."""
    for k in range(n):
        t = (k * 0.618 + seed * 0.37) % 1.0
        px, py = (x0 + t * (x1 - x0)) * c.s, (y - (k % 3) * 1.4) * c.s
        shape = ((0, 0), (1, 0), (0, 1), (1, 1)) if k % 2 else ((0, 0), (1, 0), (1, 1))
        for dx, dy in shape:
            c.t(px + dx, py + dy, ch)


def notches(c, pts, side, every, depth, ch, only):
    """Serrations: texels of `ch` stepped in from one side of a polyline (in
    world units) every `every` units, `depth` units deep. `side` is +1/-1:
    which normal of the path to cut from."""
    acc = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0) or 1e-6
        nx, ny = -(y1 - y0) / L * side, (x1 - x0) / L * side
        d = acc
        while d < L:
            px, py = x0 + (x1 - x0) * d / L, y0 + (y1 - y0) * d / L
            c.line([(px + nx * depth[0], py + ny * depth[0]),
                    (px + nx * depth[1], py + ny * depth[1])], ch, only)
            d += every
        acc = d - L


# ===================================================================== shading
def _chebyshev(body, w, h, cap):
    """Distance from each body texel to the nearest non-body one (outside the
    grid counts as non-body), in the chessboard metric, capped at `cap`: the
    ring search auto_shade() does, as two passes."""
    d = [[0] * w for _ in range(h)]
    for y in range(h):
        row, up = d[y], d[y - 1] if y else None
        for x in range(w):
            if not body[y][x]:
                continue
            if up is None or x == 0 or x == w - 1:
                row[x] = 1
                continue
            row[x] = min(cap, 1 + min(up[x - 1], up[x], up[x + 1], row[x - 1]))
    for y in range(h - 1, -1, -1):
        row, dn = d[y], d[y + 1] if y < h - 1 else None
        for x in range(w - 1, -1, -1):
            if not body[y][x]:
                continue
            if dn is None or x == 0 or x == w - 1:
                row[x] = 1
                continue
            row[x] = min(row[x], 1 + min(dn[x - 1], dn[x], dn[x + 1], row[x + 1]))
    return d


def shade(rows, mapping, depth=3, rate=1.0, lit=1.0, dark=1.0, light=palette.LIGHT):
    """The bosses' auto_shade() at S (module docstring): `depth` and `rate`
    are the 1x numbers, carried to the finer grid here."""
    s = S
    # The interior tops out where the 1x one does, (depth - 1) * rate above
    # base, reached over S times the texels.
    depth_t = depth * s
    rate_t = rate * (depth - 1) / max(1, depth_t - 1)
    lit_t = (lit, lit * 0.5)
    dark_t = (dark, dark * 0.5)
    h, w = len(rows), len(rows[0])
    mat = [[ch in mapping for ch in r] for r in rows]
    body = [[mat[y][x] or rows[y][x] == 'k' for x in range(w)] for y in range(h)]
    dist = _chebyshev(body, w, h, depth_t + 1)

    def in_mat(x, y):
        return 0 <= x < w and 0 <= y < h and mat[y][x]

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    for y in range(h):
        for x in range(w):
            ch = rows[y][x]
            if not mat[y][x]:
                if ch == 'k':
                    px[x, y] = palette.INK + (255,)
                continue
            ramp, base = mapping[ch]
            lvl = base + (min(dist[y][x], depth_t) - 1) * rate_t
            for k in (1, 2):
                if not in_mat(x + light[0] * k, y + light[1] * k):
                    lvl += lit_t[k - 1]
                    break
            for k in (1, 2):
                if not in_mat(x - light[0] * k, y - light[1] * k):
                    lvl -= dark_t[k - 1]
                    break
            px[x, y] = palette.step(ramp, math.floor(lvl + 0.5)) + (255,)
    return img


def hand_aa(img):
    """kaya40._hand_aa, the look sample's pass: where the ink line turns a
    stair-step corner (ink with material on two perpendicular sides and air
    on the other two) the ink becomes the darkest step of the material it
    hugs, which rounds the curve the way a pixel artist rounds it."""
    w, h = img.size
    px = img.load()
    ink = palette.INK
    lookup = {c: (n, i) for n, steps in palette.RAMPS.items() for i, c in enumerate(steps)}

    def mat(x, y):
        if 0 <= x < w and 0 <= y < h:
            p = px[x, y]
            if p[3] and p[:3] != ink:
                return lookup.get(p[:3])
        return None

    def clear(x, y):
        return not (0 <= x < w and 0 <= y < h) or px[x, y][3] == 0

    edits = []
    for y in range(h):
        for x in range(w):
            p = px[x, y]
            if p[3] == 0 or p[:3] != ink:
                continue
            n, s_, e, w_ = mat(x, y - 1), mat(x, y + 1), mat(x + 1, y), mat(x - 1, y)
            for a, b, oa, ob in ((n, e, (0, 1), (-1, 0)), (n, w_, (0, 1), (1, 0)),
                                 (s_, e, (0, -1), (-1, 0)), (s_, w_, (0, -1), (1, 0))):
                if a and b and clear(x + oa[0], y + oa[1]) and clear(x + ob[0], y + ob[1]):
                    ramp, i = min((a, b), key=lambda m: m[1])
                    edits.append((x, y, palette.step(ramp, max(0, i - 2)) + (255,)))
                    break
    for x, y, col in edits:
        px[x, y] = col
    return len(edits)


def render(rows, mapping, **kw):
    img = shade(rows, mapping, **kw)
    hand_aa(img)
    return img


# ===================================================================== grove
# THE GROVE WARDEN: enemies40.grove() at S. Every 1x call is here, in its
# order and with its numbers; the native passes are marked HD.
GROVE = dict(e40.GROVE)
GROVE.update({
    'q': ("purple", 2),          # chitin pits and growth lines
    'L': ("purple", 5),          # the sheen on the chitin
    'm': ("water", 4),           # the lit lip under each belly seam
    'e': ("gold", 2),            # horn growth rings, the claw's shade
    'f': ("metal", 4),           # the mandible's serrations
    'i': ("ember", 2),           # a crack's glow bleeding into the shell
    'v': ("water", 4),           # wing membrane, the lit cells
    'z': ("ember", 1),           # the throat
})
G_SHELL = 'pdPqL'


def grove(ph, po):
    c = HDCanvas()
    cx = 32.0 + po["sway"]
    arx, ary = ph["ab"]
    ary += po["breath"]
    base = 58.0 - ph["lift"] + po["crouch"] + po["dy"]
    acy = base - ary
    tcy = acy - ary * 0.8
    hcy = tcy - ph["th"][1] * 0.9
    jaw = ph["jaw"] + po["jaw"]
    # flight wings, LEAP only: raised behind everything
    if ph["wings"]:
        for s in (-1, 1):
            wc, wa = (cx + s * 15.0, tcy - 2.0), s * 28.0
            c.ellipse(wc, 5.6, 13.0, 'A', ang=wa)
            # HD: a lit panel along the leading edge, then the venation --
            # radials fanning from the root and cross-veins closing cells
            c.ellipse(local(wc, wa, -s * 1.6, -2.0), 2.4, 9.0, 'v', ang=wa, only='A')
            root = local(wc, wa, 0.0, 12.0)
            tips = [local(wc, wa, u, v) for u, v in
                    ((-4.4, -6.0), (-2.4, -11.0), (0.6, -12.6), (3.2, -9.6), (4.6, -3.0))]
            for tp in tips:
                mid = ((root[0] * 0.45 + tp[0] * 0.55), (root[1] * 0.45 + tp[1] * 0.55))
                c.line([root, mid, tp], 'a', only='Av')
            for v in (-2.0, -7.0):
                pts = [local(wc, wa, u, v + abs(u) * 0.3) for u in (-4.6, -2.0, 0.6, 3.0, 4.6)]
                c.line(pts, 'a', only='Av')
            c.path([(cx + s * 6.0, tcy - 4.0), (cx + s * 18.0, tcy - 12.0),
                    (cx + s * 22.0, tcy + 4.0)], 0.5, 'a', only='Av')
    # legs: three pairs off the abdomen's sides, feet on the floor
    for s in (-1, 1):
        up = max(0.0, po["step"] * s) * 3.0
        for k, (hy, fx) in enumerate(((-6.0, 3.0), (0.0, 6.0), (5.0, 9.0))):
            hip = (cx + s * (arx - 3.0), acy + hy)
            foot = (32.0 + s * (arx + fx * 0.6 + ph["legx"]) * po["spread"]
                    + po["step"] * s * (k - 1) * 0.8, BFLOOR - 0.8 - up)
            ch = 'd' if k == 1 else 'p'
            kn = limb(c, hip, foot, 7.0 + ph["lift"] * 0.6, 7.0 + ph["lift"] * 0.5,
                      ph["leg"], ph["leg"] * 0.6, ch, bend=s)
            c.capsule(foot, (foot[0] + s * 1.6, foot[1]), 0.8, 'o')      # claw
            c.px(kn[0], kn[1] - 1, 'P')
            # HD: the knee joint as an ink seam across the leg, two spurs on
            # the shin, and a second prong on the claw with a lit tip
            lx, ly = foot[0] - kn[0], foot[1] - kn[1]
            L = math.hypot(lx, ly) or 1.0
            ux, uy = lx / L, ly / L
            j = (kn[0] + ux * 1.2, kn[1] + uy * 1.2)
            r = ph["leg"] * 0.8
            c.line([(j[0] - uy * r, j[1] + ux * r), (j[0] + uy * r, j[1] - ux * r)], 'k',
                   only='pdP')
            for t in (0.4, 0.68):
                b = (kn[0] + lx * t + s * 0.6, kn[1] + ly * t)
                c.capsule(b, (b[0] + s * 1.3, b[1] + 0.6), 0.32, ch, 0.12)
            c.capsule((foot[0] + s * 0.2, foot[1] + 0.2), (foot[0] - s * 0.9, foot[1] + 0.5),
                      0.4, 'o', 0.2)
            c.line([(foot[0] + s * 0.4, foot[1] + 0.5), (foot[0] + s * 1.6, foot[1] + 0.5)],
                   'e', only='o')
            c.dot(foot[0] + s * 2.1, foot[1] - 0.3, 'y', only='o')
    # abdomen with its plate courses and the belly plate
    c.ellipse((cx, acy), arx, ary, 'p')
    for k in (1, 2):
        c.ellipse((cx, acy + 1.0), arx - k * 4.0, ary - k * 3.2, 'd', only='p')
        c.ellipse((cx, acy + 1.0), arx - k * 4.0 - 0.9, ary - k * 3.2 - 0.9, 'p', only='d')
    # HD: growth lines along each course, a row of pits with lit lips, and a
    # sheen where the light finds the dome
    for k in (0, 1, 2):
        c.arc((cx, acy + 1.0), arx - k * 4.0 - 2.0, ary - k * 3.2 - 1.8, 196, 344, 'q',
              only='p')
    for k in (0, 1):
        rx, ry = arx - k * 4.0 - 3.0, ary - k * 3.2 - 2.6
        for a in range(200, 345, 16 - k * 3):
            px, py = cx + math.cos(math.radians(a)) * rx, acy + 1.0 + math.sin(math.radians(a)) * ry
            c.dot(px, py, 'q', only='p')
            c.dot(px - 0.5, py - 0.5, 'L', only='p')
    for dr in (0.6, 1.1):
        c.arc((cx, acy), arx - dr, ary - dr, 206, 248, 'L', only='p')
    c.ellipse((cx, acy + 2.0), arx * 0.55, ary * 0.6, 'n')
    c.ellipse((cx, acy + 2.6), arx * 0.4, ary * 0.42, 'N')
    for k in range(3):
        c.capsule((cx - arx * 0.45, acy - 2.0 + k * 3.4), (cx + arx * 0.45, acy - 2.0 + k * 3.4),
                  0.45, 'N', only='n')
        # HD: each sclerite's lower lip catches light
        c.line([(cx - arx * 0.42, acy - 1.0 + k * 3.4), (cx + arx * 0.42, acy - 1.0 + k * 3.4)],
               'm', only='nN')
    c.ellipse((cx - arx * 0.2, acy - ary * 0.12), arx * 0.16, ary * 0.12, 'm', only='nN')
    if ph["cracks"]:
        for pts in (((cx - 10, acy - 6), (cx - 6, acy - 1), (cx - 9, acy + 4)),
                    ((cx + 11, acy - 5), (cx + 7, acy + 1), (cx + 10, acy + 6))):
            c.path(list(pts), 1.5, 'i', only=G_SHELL)                    # HD: the glow
            c.path(list(pts), 0.8, 'r', only=G_SHELL + 'i')
            c.path(list(pts), 0.4, 'R', only='r')
    # thorax and head, each set off by an ink arc
    c.ellipse((cx, tcy), ph["th"][0], ph["th"][1], 'p')
    c.path([(cx - ph["th"][0] + 1, tcy + 3), (cx, tcy + ph["th"][1] - 0.4),
            (cx + ph["th"][0] - 1, tcy + 3)], 0.5, 'k')
    c.ellipse((cx - 3.0, tcy - 3.0), 4.0, 2.0, 'P')
    # HD: the pronotum's midline, its pits, the sheen's hot edge
    c.line([(cx, tcy - ph["th"][1] + 1.2), (cx, tcy + 1.0)], 'q', only='pP')
    for s in (-1, 1):
        for k in range(3):
            c.dot(cx + s * (3.0 + k * 2.2), tcy - 1.0 + (k % 2) * 1.6, 'q', only='p')
    c.arc((cx - 3.0, tcy - 3.0), 3.4, 1.4, 200, 280, 'L', only='P')
    if ph["spines"]:
        for s in (-1, 1):
            for k in range(5):
                b = (cx + s * (ph["th"][0] - 1.0 + k * 1.6), tcy - 2.0 + k * 2.6)
                a, ln = s * (40 + k * 12), 6.0 - k * 0.6
                c.spike(b, a, ln, 1.3, 'r')
                c.line([b, polar(b, ln * 0.8, a)], 'R', only='r')        # HD: hot core
    hx, hy = ph["hd"]
    c.ellipse((cx, hcy), hx, hy, 'd')
    c.ellipse((cx, hcy - 1.0), hx - 1.4, hy - 1.6, 'p')
    # HD: a suture down the brow and a sheen on the head capsule
    c.line([(cx, hcy - hy + 1.6), (cx, hcy - 2.6)], 'q', only='p')
    c.arc((cx, hcy - 1.0), hx - 2.0, hy - 2.4, 210, 250, 'L', only='p')
    # crown: two horns sweeping out and a short spike between, rearing with
    # the tell
    for s in (-1, 1):
        a = s * (ph["hang"] - po["rear"])
        root = (cx + s * 3.0, hcy - hy + 2.0)
        mid = polar(root, ph["horn"] * 0.55, a)
        tip = polar(mid, ph["horn"] * 0.55, a + s * 18.0)
        c.path([root, mid, tip], 1.6, 'o', 0.6)
        c.px(tip[0], tip[1], 'y')
        # HD: growth rings across the horn and a lit edge up its front
        for t in (0.18, 0.36, 0.54, 0.72):
            p = (lerp(root[0], mid[0], t * 2) if t < 0.5 else lerp(mid[0], tip[0], t * 2 - 1),
                 lerp(root[1], mid[1], t * 2) if t < 0.5 else lerp(mid[1], tip[1], t * 2 - 1))
            aa = math.radians(a + (s * 18.0 if t >= 0.5 else 0.0))
            nx, ny = math.cos(aa), math.sin(aa)
            r = 1.6 - t * 1.0
            c.line([(p[0] - nx * r, p[1] - ny * r), (p[0] + nx * r, p[1] + ny * r)], 'e',
                   only='o')
        c.line([(root[0] - 0.9, root[1] - 0.2), (mid[0] - 0.7, mid[1] - 0.2),
                (tip[0] - 0.3, tip[1])], 'y', only='o')
    c.spike((cx, hcy - hy + 1.5), 0.0, 4.0 + po["rear"] * 0.12, 1.4, 'o')
    c.line([(cx - 0.5, hcy - hy + 1.2), (cx - 0.2, hcy - hy - 1.8 - po["rear"] * 0.1)], 'y',
           only='o')
    # eyes
    for s in (-1, 1):
        e = (cx + s * 4.0, hcy - 1.0)
        c.arc((e[0], e[1] - 0.6), 2.6, 2.4, 200, 340, 'P', only='p')     # HD: brow ridge
        if ph["eye"] != 'w':
            # HD: a gold rim, the iris, a pupil turned out and a catch-light
            c.ellipse(e, 2.3, 2.1, 'o')
            c.ellipse(e, 1.8, 1.6, ph["eye"])
            c.ellipse((e[0] + s * 0.3, e[1] + 0.3), 0.75, 1.1, 'k')
            c.dot(e[0] - 0.9, e[1] - 0.9, 'w')
            c.dot(e[0] - 0.4, e[1] - 0.9, 'w')
        else:
            # HD: FURY's eyes are gone white, with a gold glare round them
            c.ellipse(e, 2.3, 2.1, 'y')
            c.ellipse(e, 1.8, 1.6, 'w')
    # mandibles: two white hooks under the head, opening with the jaw
    for s in (-1, 1):
        root = (cx + s * 3.0, hcy + hy - 2.0)
        tip = (cx + s * (3.0 + jaw * 0.9), hcy + hy + 7.0 + jaw * 0.3)
        knee = (root[0] + s * (2.6 + jaw * 0.5), root[1] + 3.0)
        c.path([root, knee, tip], 1.6, 'w', 0.6)
        # HD: serrations along the inner edge
        notches(c, [knee, tip], s, 1.1, (0.2, 0.9), 'f', 'w')
    if jaw > 2.0:
        mouth = (cx, hcy + hy + 1.0)
        c.ellipse(mouth, 1.4 + jaw * 0.3, 1.2 + jaw * 0.25, 'k')
        c.ellipse((mouth[0], mouth[1] + 0.4), 0.9 + jaw * 0.2, 0.6 + jaw * 0.15, 'z',
                  only='k')                                              # HD: throat
        if ph["cracks"]:
            c.ellipse((cx, hcy + hy + 1.2), 0.8 + jaw * 0.15, 0.6 + jaw * 0.12, 'r')
        for k in (-1, 1):                                                # HD: fangs
            c.line([(mouth[0] + k * 0.8, mouth[1] - 1.0 - jaw * 0.2),
                    (mouth[0] + k * 0.7, mouth[1] - 0.2)], 'w', only='kz')
    dust_hd(c, po["dust"], 1, 'o')
    c.outline()
    return c.rows()


# ===================================================================== tide maw
# THE TIDE MAW: enemies40.tide_maw() at S.
TIDE = dict(e40.TIDE)
TIDE.update({
    'u': ("water", 3), 'U': ("water", 4), 'x': ("ember", 2),    # mottling, per body
    'j': ("water", 5), 'J': ("water", 6), 'X': ("ember", 4),    # pores' lit lips
    'g': ("ember", 2),           # gums
    'Z': ("water", 0),           # the throat, past the hinge
    'N': ("water", 2),           # the tongue ridge
    'Y': ("gold", 6),            # the lure's hot core
})
#: per body character: (mottle, lit speck, photophore)
T_SKIN = {'b': ('u', 'j', 'l'), 'c': ('U', 'J', 'l'), 'r': ('x', 'X', 'y')}


def tide_maw(ph, po):
    c = HDCanvas()
    dy = po["dy"]
    body, shade = ph["body"], ph["shade"]
    mott, speck, photo = T_SKIN[body]
    gape = po["gape"] + ph["gape"]
    hx, hy = 30.0, 40.0 + dy                          # the jaw hinge
    # trunk, off the bottom-left corner
    c.path([(-6.0, 72.0), (4.0, 60.0), (16.0, 46.0 + dy * 0.6), (22.0, 38.0 + dy)],
           15.0, body, 11.0 + po["breath"])
    c.ellipse((8.0, 60.0), 9.0, 4.0, shade, clip=lambda x, y: y > 58.0)
    # skull
    c.ellipse((25.0, 35.0 + dy), 13.0, 10.6 + po["breath"] * 0.5, body)
    c.ellipse((22.0, 30.0 + dy), 7.0, 3.2, 'c' if body == 'b' else 'l'
              if body == 'c' else 'o', only=body)                 # crown light
    # HD: skin -- blotches of a darker tone, pores with a lit lip, and a
    # lateral line of photophores running down the trunk to the skull
    for k in range(14):
        t = (k * 0.618) % 1.0
        bx = 2.0 + t * 26.0
        by = 64.0 - t * 30.0 + ((k * 7) % 5 - 2) * 2.2 + dy * t
        c.ellipse((bx, by), 1.2 + (k % 3) * 0.5, 0.8 + (k % 2) * 0.4, mott, ang=-40.0,
                  only=body)
    for k in range(22):
        t = (k * 0.381) % 1.0
        bx = 4.0 + t * 30.0
        by = 62.0 - t * 30.0 + ((k * 5) % 7 - 3) * 1.6 + dy * t
        c.dot(bx, by, mott, only=body)
        c.dot(bx - 0.5, by - 0.5, speck, only=body)
    for k in range(6):
        p = (3.0 + k * 3.0, 59.0 - k * 3.4 + dy * k * 0.12)
        c.ellipse(p, 0.75, 0.75, 'k', only=body + mott + shade)
        c.ellipse((p[0] - 0.15, p[1] - 0.15), 0.45, 0.45, photo, only='k')
    # HD: a pectoral fin laid along the trunk, rays and a lit leading edge
    fr = (14.0, 47.0 + dy * 0.7)
    fin = [fr, (8.0, 50.0 + dy * 0.5), (3.0, 56.0), (6.0, 57.0), (11.0, 53.0 + dy * 0.6)]
    c.poly(fin, shade, only=body + mott + speck)
    for k in range(4):
        e = (lerp(3.0, 11.0, k / 3.0), lerp(56.4, 53.0, k / 3.0) + dy * 0.2 * k / 3.0)
        c.line([(fr[0] - 0.4, fr[1] + 0.4), e], body, only=shade)
    c.line([fr, (8.0, 50.0 + dy * 0.5), (3.4, 55.6)], speck, only=shade + body)
    c.path([(16.0, 27.0 + dy), (13.4, 35.0 + dy), (16.0, 44.0 + dy)], 0.55, 'k')  # operculum
    # HD: the gill cover's lit lip behind the slit
    c.line([(15.0, 27.6 + dy), (12.6, 35.0 + dy), (15.0, 43.4 + dy)], speck, only=body)
    # mouth: cavity first, the two jaws over its edges
    ut = (hx + ph["jaw"], hy - 6.0 - gape * 0.55 + po["tilt"])
    lt = (hx + ph["jaw"] - 2.0, hy + 4.0 + gape * 0.45 + po["tilt"])
    c.poly([(hx - 2.0, hy - 1.0), ut, (ut[0] - 1.0, (ut[1] + lt[1]) / 2), lt], 'n')
    # HD: the throat goes black toward the hinge, a tongue ridge runs out
    c.poly([(hx - 2.0, hy - 1.0), (lerp(hx, ut[0], 0.35), lerp(hy - 1.0, ut[1], 0.35)),
            (lerp(hx, lt[0], 0.35), lerp(hy - 1.0, lt[1], 0.35))], 'Z', only='n')
    c.line([(hx + 1.0, hy + 0.4), (lerp(hx, lt[0], 0.7), lerp(hy, lt[1], 0.7) - 1.6)], 'N',
           only='nZ')
    c.path([(hx - 6.0, hy - 6.0), ((hx + ut[0]) / 2, (hy - 6.0 + ut[1]) / 2 - 1.0), ut],
           5.0, body, 1.4)
    c.path([(hx - 4.0, hy + 5.0), ((hx + lt[0]) / 2, (hy + 6.0 + lt[1]) / 2 + 1.4), lt],
           5.4, shade, 1.6)
    # HD: gums along both jaws' biting edge
    c.line([(hx, hy - 2.4), (lerp(hx, ut[0], 0.5), lerp(hy - 2.4, ut[1] + 1.0, 0.5)),
            (ut[0] - 0.6, ut[1] + 0.8)], 'g', only=body + mott + speck)
    c.line([(hx, hy + 2.0), (lerp(hx, lt[0], 0.5), lerp(hy + 2.0, lt[1] - 1.2, 0.5)),
            (lt[0] - 0.6, lt[1] - 1.0)], 'g', only=shade)
    # teeth: a comb on each jaw, pointing into the gap
    for k in range(7):
        t = 0.2 + k * 0.12
        u = (lerp(hx, ut[0], t), lerp(hy - 2.6, ut[1] + 1.0, t))
        l = (lerp(hx, lt[0], t), lerp(hy + 2.2, lt[1] - 1.2, t))
        ln = 2.6 + (k % 2) * 1.2
        c.capsule(u, (u[0] + 0.4, u[1] + ln), 0.55, 'w', 0.2)
        c.capsule(l, (l[0] - 0.4, l[1] - ln), 0.55, 'w', 0.2)
        # HD: a dull root and a glassy, curved tip on every needle
        c.line([(u[0] - 0.2, u[1]), (u[0] - 0.1, u[1] + ln * 0.35)], 'a', only='w')
        c.line([(l[0] + 0.2, l[1]), (l[0] + 0.1, l[1] - ln * 0.35)], 'a', only='w')
        c.dot(u[0] + 0.7, u[1] + ln - 0.1, 'w')
        c.dot(l[0] - 0.8, l[1] - ln, 'w')
    # gill rakers
    for k in range(ph["gills"]):
        x = 18.0 + k * 2.4
        c.capsule((x, 37.0 + dy), (x - 1.4, 43.0 + dy), 0.5, 'n')
        c.line([(x - 0.4, 37.0 + dy), (x - 1.8, 43.0 + dy)], speck, only=body)  # HD: lip
    # barbels, UNDERTOW only
    if ph["barb"]:
        for k in range(2):
            pts = [(hx + 6.0 + k * 4, hy + 8.0 + gape * 0.2), (hx + 2 + k * 3, hy + 15.0),
                   (hx - 6 + k * 2, hy + 20.0 - k * 2)]
            c.path(pts, 0.6, 'o')
            c.ellipse(pts[-1], 0.8, 0.8, 'y')                    # HD: a bead at the end
    # the eye: a block in an ink socket with a catchlight, no pupil -- HD: a
    # lit socket rim, the glassy eye darkening to its lower edge, two lights
    e = (30.0, 28.0 + dy)
    c.ellipse(e, 3.8, 3.6, speck, only=body + mott)
    c.ellipse(e, 3.2, 3.0, 'k')
    c.ellipse(e, 2.2, 2.0, ph["eye"])
    c.arc(e, 1.7, 1.5, 20, 160, 'J' if ph["eye"] != 'y' else 'o')
    c.ellipse((e[0] - 0.7, e[1] - 0.7), 0.55, 0.55, 'w')
    c.dot(e[0] + 0.9, e[1] + 0.8, 'w')
    # the lure: a stalk off the crown arcing up and forward over the mouth
    s = po["stalk"]
    root = (21.0, 26.0 + dy)
    p1 = (lerp(root[0], 24.0, s), lerp(root[1], 10.0 + dy * 0.5, s))
    p2 = (lerp(root[0] - 2, 38.0, s), lerp(root[1] - 4, 4.0 + dy * 0.5, s))
    bulb = (lerp(root[0] + 2, 47.0 + po["swing"], s), lerp(root[1] - 6, 11.0 + dy * 0.4, s))
    c.path([root, p1, p2, bulb], 1.1, shade, 0.6)
    # HD: the stalk is jointed like a fin ray
    stalk = [root, p1, p2, bulb]
    for i in range(3):
        for t in (0.33, 0.66):
            a, b = stalk[i], stalk[i + 1]
            q = (lerp(a[0], b[0], t), lerp(a[1], b[1], t))
            c.dot(q[0], q[1], body, only=shade)
    c.ellipse(bulb, 3.4, 3.4, 'k')
    c.ellipse(bulb, 2.6, 2.6, ph["lure"])
    # HD: a hot core in the bulb, its light pooled low, a glint high
    c.ellipse((bulb[0] + 0.3, bulb[1] + 0.3), 1.4, 1.4, 'Y' if ph["lure"] != 'l' else 'w')
    c.ellipse((bulb[0] - 1.0, bulb[1] - 1.0), 0.5, 0.5, 'w')
    c.outline()
    return c.rows()


# ================================================================== stormcrest
# THE STORMCREST: enemies40.stormcrest() at S.
STORM = dict(e40.STORM)
STORM.update({
    's': ("stone", 2), 'S': ("stone", 4), 'D': ("stone", 0),    # feather shadow
    'h': ("stone", 4), 'H': ("stone", 6), 'j': ("stone", 2),    # feather edge, lit
    'e': ("gold", 2),            # leg scutes, the cere's shade
    'Y': ("gold", 6),            # the beak's hot edge
    'R': ("ember", 2),           # the ember's glow into the plumage
})
#: per body character: (feather shadow, feather lit edge)
S_FEATHER = {'a': ('s', 'h'), 'A': ('S', 'H'), 'd': ('D', 'j')}
#: per plume character: its shaft
S_SHAFT = {'w': 'A', 'y': 'o', 'o': 'e'}


def _scallops(c, cx, cy, rx, ry, ang, rows, per, dark, lit, only):
    """Rows of overlapping feather tips across an ellipse: each a small U of
    shadow with a lit edge above it, offset by half a feather row to row."""
    for r in range(rows):
        v = -0.75 + 1.5 * (r + 0.5) / rows
        for k in range(per):
            u = -0.85 + 1.7 * (k + 0.5 * (r % 2) + 0.25) / per
            if u * u + v * v > 0.8:
                continue
            p = local((cx, cy), ang, u * rx, v * ry)
            c.arc(p, 1.3, 0.9, 20, 160, dark, only=only)
            c.arc((p[0] - 0.3, p[1] - 0.6), 1.1, 0.7, 30, 150, lit, only=only)


def stormcrest(ph, po):
    c = HDCanvas()
    body, belly, plume = ph["body"], ph["belly"], ph["plume"]
    fdark, flit = S_FEATHER[body]
    shaft = S_SHAFT[plume]
    dy = po["dy"]
    bx, by = 29.0, 37.0 + dy
    # legs first (straight to the grid; they do not rotate)
    legs = HDCanvas()
    if po["legs"]:
        for k, s in ((0, 1), (1, -1)):
            hip = (bx + 2.0 + k * 4.0, by + 9.0)
            foot = (bx + 3.0 + k * 4.0 + po["step"] * s * 0.6, BFLOOR - 1.4)
            kn = limb(legs, hip, foot, 9.4, 9.8, 1.5, 1.0, 'o', bend=-1)
            # HD: scutes down the tarsus and a lit front edge
            for t in (0.2, 0.36, 0.52, 0.68, 0.84):
                q = (lerp(kn[0], foot[0], t), lerp(kn[1], foot[1], t))
                legs.line([(q[0] - 0.9, q[1] - 0.2), (q[0] + 0.9, q[1] + 0.2)], 'e', only='o')
            legs.line([(kn[0] + 0.7, kn[1]), (foot[0] + 0.6, foot[1] - 1.0)], 'y', only='o')
            # feathered thigh over the knee
            legs.ellipse((lerp(hip[0], kn[0], 0.5), lerp(hip[1], kn[1], 0.5)), 2.2, 3.0, body)
            legs.line([(lerp(hip[0], kn[0], 0.3) - 1.0, lerp(hip[1], kn[1], 0.8)),
                       (lerp(hip[0], kn[0], 0.6) + 1.0, lerp(hip[1], kn[1], 0.9))], fdark,
                      only=body)
            for t in (-1, 0, 1):
                legs.capsule(foot, (foot[0] + 2.6 * t + 1.0, foot[1] + 0.8), 0.6, 'k')
                # HD: each talon hooks down to a point
                legs.capsule((foot[0] + 2.6 * t + 1.0, foot[1] + 0.8),
                             (foot[0] + 2.6 * t + 1.0 + 0.6 * (1 if t >= 0 else -1),
                              foot[1] + 1.5), 0.35, 'k', 0.15)
    # tail: a wedge off the back, low, under the wing
    tl = ph["tail"]
    c.poly([(bx - 8.0, by - 2.0), (bx - 8.0 - tl, by + 4.0 - po["open"] * 3),
            (bx - 6.0 - tl * 0.9, by + 9.0), (bx - 6.0, by + 5.0)], plume)
    for k in range(3):
        c.capsule((bx - 8.0, by + 1.0 + k), (bx - 7.0 - tl * (0.7 + k * 0.08), by + 3.0 + k * 2.4),
                  0.45, body, only=plume)
    # HD: tail feathers split, each with a shaft
    for k in range(5):
        t = k / 4.0
        e = (lerp(bx - 8.0 - tl, bx - 6.0 - tl * 0.9, t),
             lerp(by + 4.0 - po["open"] * 3, by + 9.0, t))
        c.line([(bx - 7.0, by + 1.5 + t * 3.0), e], shaft, only=plume)
    # the mass: an egg lying forward, the pale breast low and forward
    c.ellipse((bx, by), 15.0, 10.6 + po["breath"] * 0.4, body, ang=-8.0)
    # HD: the body is feathered -- rows of scalloped tips over the back
    _scallops(c, bx - 2.0, by - 1.0, 13.0, 9.0, -8.0, 5, 6, fdark, flit, body)
    c.ellipse((bx + 6.0, by + 3.0), 9.0, 7.0, belly, ang=-20.0)
    for k in range(4):                                             # breast barring
        c.path([(bx + 1.0 + k * 3.0, by + 0.0), (bx + 2.0 + k * 3.0, by + 3.0),
                (bx + 1.0 + k * 3.0, by + 6.0)], 0.45, body, only=belly)
        # HD: a fine chevron between the bars
        c.line([(bx + 2.6 + k * 3.0, by + 1.0), (bx + 3.4 + k * 3.0, by + 3.0),
                (bx + 2.6 + k * 3.0, by + 5.0)], fdark if belly != 'w' else 'A', only=belly)
    # head, beak, eye
    hx, hy = bx + 14.0, by - 11.0
    c.capsule((bx + 8.0, by - 4.0), (hx - 1.0, hy + 2.0), 5.0, body, 4.0)   # neck
    c.ellipse((hx, hy), 6.4, 5.8, body)
    c.ellipse((hx + 2.0, hy + 2.4), 4.0, 3.0, belly, only=body)
    # HD: hackles -- short strokes down the nape
    for k in range(5):
        q = (hx - 4.6 + k * 0.6, hy - 1.0 + k * 1.6)
        c.line([q, (q[0] - 1.0, q[1] + 1.8)], fdark, only=body)
    c.poly([(hx + 4.0, hy - 2.6), (hx + 10.6, hy - 1.0), (hx + 12.0, hy + 2.6),
            (hx + 10.4, hy + 4.4), (hx + 9.8, hy + 1.6), (hx + 4.6, hy + 2.6)], 'y')
    # HD: the cere at the beak's root with a nostril, the hook's hot edge
    c.poly([(hx + 4.0, hy - 2.6), (hx + 6.6, hy - 2.0), (hx + 6.2, hy + 1.6),
            (hx + 4.6, hy + 2.4)], 'o', only='y')
    c.dot(hx + 5.6, hy - 1.0, 'e')
    c.dot(hx + 6.0, hy - 1.0, 'k')
    c.line([(hx + 7.0, hy - 2.0), (hx + 10.4, hy - 1.0), (hx + 11.6, hy + 1.6)], 'Y', only='y')
    c.capsule((hx + 5.0, hy + 0.6), (hx + 9.4, hy + 1.4), 0.45, 'o')          # gape line
    # HD: a real eye -- gold iris ring, a black pupil, a catch-light
    c.ellipse((hx + 2.4, hy - 1.4), 1.6, 1.5, ph["eye"])
    c.arc((hx + 2.4, hy - 1.4), 1.3, 1.2, 20, 160, 'o' if ph["eye"] == 'y' else 'R')
    c.ellipse((hx + 2.8, hy - 1.3), 0.7, 0.75, 'k')
    c.dot(hx + 2.3, hy - 1.9, 'w')
    # the brow, heavier than at 1x: a raptor's frown
    c.capsule((hx + 0.2, hy - 3.6), (hx + 4.4, hy - 3.0), 0.55, 'k')
    c.capsule((hx + 2.8, hy - 3.2), (hx + 4.6, hy - 2.4), 0.4, 'k')
    # crest: a fan of feathers off the crown, swept back
    fan = ph["fan"]
    for k in range(fan):
        t = k / max(1, fan - 1)
        a = -95.0 + t * (50.0 + 30.0 * po["fanned"])
        ln = ph["crest"] * (0.7 + 0.4 * math.sin(t * math.pi)) * (1.0 + 0.15 * po["fanned"])
        root = (hx - 2.0, hy - 3.0)
        tip = polar(root, ln, a)
        mid = ((root[0] + tip[0]) / 2, (root[1] + tip[1]) / 2 - 1.0)
        c.path([root, mid, tip], 1.3, plume, 0.5)
        c.line([root, mid, polar(tip, 0.8, a + 180)], shaft, only=plume)   # HD: rachis
    # wing: folded along the back, or swung up and back with its primaries
    op = po["open"]
    sh = (bx + 6.0, by - 6.0)
    wa = lerp(-100.0, -20.0, op)                     # from straight back to raised
    span = ph["span"] * lerp(0.75, 1.0, op)
    tip = polar(sh, span, wa)
    wmid = ((sh[0] + tip[0]) / 2, (sh[1] + tip[1]) / 2 + 2.0 - op * 3)
    c.path([sh, wmid, tip], 5.4, body, 2.4)
    for k in range(5):                                             # primaries
        t = 0.55 + k * 0.11
        root = (lerp(sh[0], tip[0], t), lerp(sh[1], tip[1], t) + 1.0)
        fa = wa + 180.0 - 40.0 + k * 10.0 - op * 40.0
        end = polar(root, 6.0 + k * 1.2, fa)
        c.capsule(root, end, 1.0, body, 0.5)
        # HD: each primary separated by a shadow and split by its shaft
        c.line([root, end], fdark, only=body)
        c.line([(root[0] - 0.5, root[1] - 0.5), (end[0] - 0.4, end[1] - 0.4)], flit,
               only=body)
    # HD: coverts -- two rows of scallops along the wing's arm
    for k in range(6):
        t = 0.12 + k * 0.13
        q = (lerp(sh[0], tip[0], t), lerp(sh[1], tip[1], t) + 1.6 - op)
        c.arc(q, 1.4, 1.0, 20, 160, fdark, only=body)
        c.arc((q[0] + 0.8, q[1] - 1.8), 1.2, 0.8, 20, 160, fdark, only=body)
    for k in range(2):                                             # the bars
        t = 0.35 + k * 0.25
        a0 = (lerp(sh[0], tip[0], t) - 2.0, lerp(sh[1], tip[1], t) - 2.5)
        a1 = (lerp(sh[0], tip[0], t) + 2.0, lerp(sh[1], tip[1], t) + 2.5)
        c.capsule(a0, a1, 0.8, plume, only=body + fdark + flit)
        c.line([a0, a1], shaft, only=plume)                        # HD
    if ph["ember"]:
        for k in range(3):
            a0 = (bx - 8.0 + k * 5, by + 2.0 - k)
            a1 = (bx - 4.0 + k * 5, by + 6.0 - k)
            c.capsule(a0, a1, 1.1, 'R', only=body + fdark + flit)  # HD: the glow
            c.capsule(a0, a1, 0.6, 'r', only=body + fdark + flit + 'R')
    rows = c.rows()
    if po["ang"]:
        rows = e40.rotate_rows(rows, po["ang"], (bx + 4.0) * S, by * S)
    # composite the (unrotated) legs behind the body
    out = HDCanvas()
    for y in range(HH):
        for x in range(HW):
            ch = rows[y][x]
            out.g[y][x] = ch if ch != '.' else legs.g[y][x]
    out.outline()
    return out.rows()


# ================================================================= brood queen
# THE BROOD QUEEN: enemies40.brood_queen() at S. Her brightness is the
# mechanic (src/enemies/brood_queen.gd fades her to dark_alpha unless she is
# attacking), so nothing added here is brighter than the body it sits on:
# the attack poses' white rim stays the brightest thing on her.
QUEEN = dict(e40.QUEEN)
QUEEN.update({
    'm': ("skin", 1),            # stretch striations, spiracles
    'M': ("stone", 2),           # sutures and joints on the armour
    'f': ("stone", 1),           # the compound eye's dark facets
    'F': ("stone", 4),           # its lit facets
    'q': ("ember", 2),           # the glow round the split
})


def brood_queen(ph, po):
    c = HDCanvas()
    body, seg = ph["body"], ph["seg"]
    ax, ay = 26.0, 44.0 + po["dy"] - po["arch"] * 0.5
    arx, ary = 21.0, 17.0 + po["arch"] * 0.5 + po["breath"]
    # ovipositor, off the bottom-left
    ovi = [(10.0, 54.0 + po["dy"]), (2.0, 60.0), (-4.0, 63.0)]
    c.path(ovi, 5.0, body, 3.0)
    for t in (0.25, 0.5, 0.75):                                    # HD: its rings
        q = (lerp(ovi[0][0], ovi[2][0], t), lerp(ovi[0][1], ovi[2][1], t))
        r = lerp(4.6, 3.0, t)
        c.line([(q[0] - r * 0.55, q[1] - r * 0.8), (q[0] + r * 0.55, q[1] + r * 0.8)], 'm',
               only=body)
    # legs under the thorax, behind it
    tx, ty = 47.0 + po["reach"] * 0.6, 49.0 + po["dy"]
    for k in range(3):
        hip = (tx - 4.0 + k * 4.0, ty + 3.0)
        off = po["legs"] * (1 if k % 2 else -1) * 2.0
        foot = (hip[0] + 2.0 + off, BFLOOR - 1.0)
        kn = limb(c, hip, foot, 5.0, 6.0, 1.3, 0.8, 'a', bend=1 if k else -1)
        # HD: a joint seam at the knee, a lit edge, a tarsal claw
        lx, ly = foot[0] - kn[0], foot[1] - kn[1]
        L = math.hypot(lx, ly) or 1.0
        j = (kn[0] + lx / L * 0.9, kn[1] + ly / L * 0.9)
        c.line([(j[0] - ly / L, j[1] + lx / L), (j[0] + ly / L, j[1] - lx / L)], 'M', only='a')
        c.line([(kn[0] - 0.6, kn[1]), (foot[0] - 0.5, foot[1] - 1.0)], 'A', only='a')
        c.capsule(foot, (foot[0] + 1.2, foot[1] + 0.4), 0.4, 'a', 0.2)
    # abdomen: bands, the glow between them, blisters, the split
    c.ellipse((ax, ay), arx, ary, body)
    for k in range(5):                                             # dorsal tubercles
        t = 0.2 + k * 0.15
        bxp = ax - arx + t * 2 * arx
        top = ay - ary * math.sqrt(max(0.0, 1 - ((bxp - ax) / arx) ** 2))
        c.ellipse((bxp, top + 1.0), 2.6, 2.4, body)
    # HD: fine stretch striations across each band, under the seams
    for k in range(13):
        bxp = ax - arx + 3.5 + k * 3.0
        c.line([(bxp + 0.8, ay - ary + 2.0), (bxp - 0.6, ay - 2.0), (bxp - 0.6, ay + 3.0),
                (bxp + 0.8, ay + ary - 3.0)], 'm', only=body)
    for k in range(6):
        bxp = ax - arx + 6.0 + k * 6.0
        seam = [(bxp + 1.6, ay - ary - 2.0), (bxp - 1.0, ay), (bxp + 1.6, ay + ary + 2.0)]
        c.path(seam, 1.3, seg, only=body + 'm')
        if ph["glow"] != seg:
            c.path(seam, 0.4, ph["glow"], only=seg)
        # HD: a spiracle on every band, high on the flank, with a lit rim
        sp = (bxp + 3.4, ay - ary * 0.45)
        c.ellipse(sp, 0.8, 0.6, 'm', only=body)
        c.arc(sp, 0.9, 0.8, 200, 300, 'l' if body == 'b' else body, only=body)
    c.ellipse((ax + 2.0, ay + ary * 0.6), arx * 0.8, ary * 0.3, 'n' if body == 'b' else 'b',
              only=body + 'm')                                    # underside shadow
    for k in range(ph["blisters"]):
        bc = (ax - 10.0 + k * 9.0, ay + ary * 0.55)
        c.ellipse(bc, 3.4, 2.6, 'w' if k == 1 else 'l')
        c.ellipse(bc, 3.4, 2.6, 'y', only='w')
        # HD: each blister's skin thins to a darker crown
        c.arc(bc, 2.6, 1.8, 200, 340, 'o' if k == 1 else 'b', only='yl')
    if ph["split"]:
        for k in range(4):
            bxp = ax - 12.0 + k * 7.0
            outer = [(bxp - 1.6, ay - 9.0), (bxp + 3.0, ay - 3.0), (bxp + 0.4, ay + 2.0),
                     (bxp + 3.4, ay + 9.0), (bxp - 2.4, ay + 4.0), (bxp - 0.6, ay - 1.0)]
            # HD: the heat scorches the skin round the split
            c.poly([(x + (x - bxp) * 0.35, y * 1.0) for x, y in outer], 'q',
                   only=body + seg + 'm' + ph["glow"])
            c.poly(outer, 'R')
            c.poly([(bxp - 0.8, ay - 6.0), (bxp + 1.8, ay - 2.4), (bxp, ay + 2.0),
                    (bxp + 2.0, ay + 6.0), (bxp - 1.4, ay + 3.0), (bxp - 0.2, ay - 1.0)], 'r')
            c.capsule((bxp + 0.2, ay - 3.0), (bxp + 0.4, ay + 3.0), 0.4, 'y', only='r')
    for k in range(ph["spines"]):
        t = 0.15 + k * 0.13
        bxp = ax - arx + t * 2 * arx
        top = ay - ary * math.sqrt(max(0.0, 1 - ((bxp - ax) / arx) ** 2))
        c.spike((bxp, top + 1.0), -20.0 + k * 6, 5.0, 1.2, 'o')
        c.line([(bxp, top + 1.0), polar((bxp, top + 1.0), 3.6, -20.0 + k * 6)], 'R',
               only='o')                                           # HD: its dark core
    # thorax plate and head capsule
    c.ellipse((tx, ty - 1.0), 6.6, 6.0, ph["plate"])
    c.path([(tx - 5.0, ty - 2.0), (tx, ty + 0.4), (tx + 5.0, ty - 2.0)], 0.5, 'k')
    # HD: the plate's sutures and pits
    c.line([(tx - 3.0, ty - 6.0), (tx - 1.6, ty - 3.0)], 'M', only=ph["plate"])
    c.line([(tx + 2.4, ty - 6.2), (tx + 1.6, ty - 3.2)], 'M', only=ph["plate"])
    for q in ((tx - 3.6, ty + 1.6), (tx, ty + 2.6), (tx + 3.4, ty + 1.4)):
        c.dot(q[0], q[1], 'M', only=ph["plate"])
    hx, hy = tx + 8.4 + po["reach"], ty - 1.0
    # HD: two beaded antennae off the brow, swept back over the head
    for k, sw in enumerate((0.0, 1.4)):
        a0 = (hx + 1.0 - sw, hy - 4.2)
        pts = [a0, (a0[0] - 1.6, a0[1] - 3.0 + po["dy"] * 0.2), (a0[0] - 4.4 - sw, a0[1] - 4.6)]
        c.path(pts, 0.45, 'a', 0.3)
        for q in pts[1:]:
            c.dot(q[0], q[1], 'A', only='a')
    c.ellipse((hx, hy), 5.4, 5.0, ph["plate"])
    # HD: the clypeus line and a compound eye of lit and dark facets where 1x
    # had two pixels
    c.arc((hx, hy + 0.6), 4.0, 3.2, -40, 60, 'M', only=ph["plate"])
    e = (hx + 2.0, hy - 2.0)
    c.ellipse(e, 1.5, 1.2, 'k')
    for dx, dy_ in ((-0.6, -0.5), (0.4, -0.5), (-0.1, 0.1), (0.9, 0.1), (-0.6, 0.6), (0.4, 0.6)):
        c.dot(e[0] + dx, e[1] + dy_, 'F' if dy_ < 0 else 'f')
    # mandibles: two sickles leaving the right of the frame, opening with gape
    g = ph["gape"] + po["gape"]
    for s in (-1, 1):
        root = (hx + 3.6, hy + 1.0 + s * 1.6)
        knee = (hx + 9.0, hy + 1.0 + s * (2.6 + g * 0.5))
        tip = (hx + 12.0, hy + 1.0 + s * (1.0 + g * 0.6) - 1.0)
        c.path([root, knee, tip], 1.8, ph["jaw"], 0.5)
        # HD: teeth along the inner edge of each sickle
        notches(c, [root, knee], -s, 1.0, (0.3, 1.2), 'k', ph["jaw"])
    if po["lit"]:
        # Two units deep: at 12 % alpha over a dark chamber a one-unit rim on
        # a pale body is not there at all.
        lit_set = set((body, seg, ph["glow"], 'n', 'b', ph["plate"], ph["jaw"], 'l', 'o', 'R',
                       'r', 'm', 'M', 'q', 'f', 'F'))
        rim_hd(c, lit_set, 'w', depth=2 * S)
    dust_hd(c, po["dust"], 2, 'o', x0=20, x1=60)
    c.outline()
    return c.rows()


# ============================================================== obsidian heart
# THE OBSIDIAN HEART: enemies40.obsidian_heart() at S. Glass, so the native
# pass is about edges: facet planes with hard borders, conchoidal ripples,
# glints, and cracks that light the glass beside them.
OBSIDIAN = dict(e40.OBSIDIAN)
OBSIDIAN.update({
    'f': ("purple", 1), 'F': ("purple", 3),     # facet planes, per shell
    'c': ("water", 3),           # the cold reflection along a facet edge
    'i': ("ember", 2),           # a warm crack's light in the glass
    'I': ("gold", 2),            # a gold crack's light in the glass
    'Y': ("gold", 6),            # the core's ring at full flare
})
#: per shell character: (the facet plane a step above it)
O_FACET = {'g': 'f', 'G': 'F'}


def obsidian_heart(ph, po):
    c = HDCanvas()
    shell = ph["shell"]
    facet = O_FACET[shell]
    glass = (shell, ph["seam"], facet, 'c')
    sx = 1.0 + po["squash"] * 0.05
    sy = 1.0 - po["squash"] * 0.04
    pt_y = 58.0 + po["dy"] * 0.5
    lobe_y = pt_y - (pt_y - 29.0) * sy + po["dy"]
    lean = po["lean"] * 1.3
    cx = 32.0
    r = 13.6 * sx + po["breath"] * 0.4
    dxl = 10.6 * sx
    # roots, behind the heart
    for k, rx in enumerate((-12.0, -4.0, 4.0, 12.0)):
        lift = (2.0 if (k % 2 == 0) == (po["roots"] > 0) and po["roots"] else 0.0)
        top = (cx + rx * 0.8, pt_y - 6.0)
        pts = [top, (cx + rx * 1.1, pt_y + 1.0), (cx + rx * 1.25 + 1.0, BFLOOR - 0.8 - lift)]
        ch = ph["seam"] if k % 2 else shell
        c.path(pts, 2.6, ch, 1.6)
        # HD: a root is a glass rod -- a hard lit edge down its left side
        c.line([(p[0] - 1.2, p[1]) for p in pts[1:]], 'c' if ch == shell else facet, only=ch)
    # the heart: two lobes and the point, the crown leaned
    for s in (-1, 1):
        c.ellipse((cx + s * dxl + lean, lobe_y), r, r, shell)
    c.poly([(cx - dxl - r * 0.94 + lean, lobe_y + r * 0.34), (cx, pt_y + 1.0),
            (cx + dxl + r * 0.94 + lean, lobe_y + r * 0.34),
            (cx + lean, lobe_y)], shell)
    # HD: knapped glass -- each lobe broken into planes. The upper-left plane
    # of each lobe sits a step up, cut off by a straight edge with a cold
    # reflection on it. (Conchoidal ripples were tried: concentric arcs read
    # as a symbol, not as glass.)
    for s in (-1, 1):
        lc = (cx + s * dxl + lean, lobe_y)
        c.poly([(lc[0] - r, lc[1] - r), (lc[0] + r * 0.5, lc[1] - r),
                (lc[0] - r * 0.2, lc[1] + r * 0.05), (lc[0] - r, lc[1] + r * 0.25)], facet,
               only=shell)
        c.line([(lc[0] + r * 0.45, lc[1] - r * 0.95), (lc[0] - r * 0.2, lc[1] + r * 0.05),
                (lc[0] - r * 0.95, lc[1] + r * 0.25)], 'c', only=shell + facet)
        # glints: a hard two-texel streak on each lobe's crown
        g0 = (lc[0] - r * 0.55, lc[1] - r * 0.55)
        c.line([g0, (g0[0] + 1.6, g0[1] - 0.9)], 'w', only=shell + facet)
    # the lower plane, between the point and the core
    c.poly([(cx - 6.0 + lean * 0.5, lobe_y + r * 0.5), (cx, pt_y - 1.0),
            (cx + 7.0 + lean * 0.5, lobe_y + r * 0.45)], facet, only=(shell,))
    # the cleft between the lobes, forced open by `gape`
    g = ph["gape"] + po["flare"]
    c.poly([(cx + lean - g * 0.5 + 1.0, lobe_y - r - 2.0), (cx + lean + g * 0.5 + 2.0, lobe_y - r - 2.0),
            (cx + lean + 1.4, lobe_y - r * 0.2)], '.')
    # core and cracks
    core = (cx + lean * 0.5 + 1.0, lobe_y + 9.0)
    cr = ph["core_r"] + po["flare"] * 1.6
    hot = po["flare"] >= 1.0
    # Overdriven cracks go one step *brighter* than the phase's own: gold
    # cracks go white rather than ember, which would read as cooling.
    # The anticipation beat (flare 0.5) lights them already: the brighten has
    # to start before the strike, not on it.
    crack_ch = ({'h': 'y', 'y': 'w', 'R': 'w'}[ph["crack"]] if po["flare"] >= 0.5
                else ph["crack"])
    halo = {'h': 'c', 'y': 'I', 'R': 'i', 'w': 'I'}[crack_ch]
    for k in range(ph["crack_n"]):
        a = -150.0 + k * 300.0 / max(1, ph["crack_n"] - 1) + (k % 2) * 9.0
        mid = polar(core, cr + 5.0, a + 8.0)
        tip = polar(core, cr + 15.0, a - 6.0)
        wid = ph["crack_w"] + po["flare"] * 0.3
        # HD: the crack lights the glass either side of it
        c.path([core, mid, tip], wid + 0.9, halo, 0.6, only=glass)
        c.path([core, mid, tip], wid, crack_ch, 0.4, only=glass + (halo,))
        # and forks once near its end
        fk = polar(mid, 3.4, a + 40.0 * (1 if k % 2 else -1))
        c.line([(lerp(mid[0], tip[0], 0.4), lerp(mid[1], tip[1], 0.4)), fk], crack_ch,
               only=glass + (halo,))
    for k in range(2):                                             # cold seams
        a = -60.0 + k * 140.0
        c.path([polar(core, cr + 2.0, a), polar(core, cr + 12.0, a + 15.0)], 0.5, ph["seam"],
               only=(shell, facet))
    c.ellipse(core, cr + 1.2, cr + 1.0, ph["seam"], only=(shell, facet, halo, 'c'))
    c.ellipse(core, cr, cr * 0.94, ph["core"])
    c.ellipse(core, cr * 0.55, cr * 0.5,
              'y' if po["flare"] >= 0.5 else ('R' if ph["core"] == 'r' else 'o'))
    # HD: the core's structure -- a ring inside it and rays from the centre
    c.arc(core, cr * 0.78, cr * 0.72, 0, 360, 'Y' if hot else ph["core"],
          only=(ph["core"],))
    for k in range(8):
        a = k * 45.0 + 22.5
        c.line([polar(core, cr * 0.3, a), polar(core, cr * 0.85, a)],
               'y' if po["flare"] >= 0.5 else 'o', only=(ph["core"],))
    if hot:
        c.ellipse(core, cr * 0.25, cr * 0.25, 'w')
    # the rim light along the crown
    rim_hd(c, set(glass), ph["rim"])
    for k in range(ph["shards"]):
        a = -120.0 + k * 60.0
        p = polar((cx, lobe_y + 6.0), 27.0 + (k % 2) * 2.0, a + po["lean"] * 4.0)
        c.poly([(p[0] - 1.6, p[1]), (p[0], p[1] - 2.6), (p[0] + 1.8, p[1] + 0.4),
                (p[0] + 0.2, p[1] + 2.4)], shell)
        # HD: a shard has two faces, the lit one up and left
        c.poly([(p[0] - 1.6, p[1]), (p[0], p[1] - 2.6), (p[0] + 0.1, p[1] + 0.2)], facet,
               only=(shell,))
        c.px(p[0], p[1] - 1.4, ph["rim"])
    dust_hd(c, po["dust"], 3, 'G')
    c.outline()
    return c.rows()


# ===================================================================== sheets
def _frames(make, phases, poses):
    return [make(ph, po) for ph in phases for po in poses]


def grove_cells():
    return [render(r, GROVE) for r in _frames(grove, e40.GROVE_PHASES, e40.GROVE_POSES)]


def tide_maw_cells():
    return [render(r, TIDE) for r in _frames(tide_maw, e40.TIDE_PHASES, e40.TIDE_POSES)]


def stormcrest_cells():
    return [render(r, STORM) for r in _frames(stormcrest, e40.STORM_PHASES, e40.STORM_POSES)]


def brood_queen_cells():
    # depth 2, as at 1x: she is the one boss shaded flatter (enemies40)
    return [render(r, QUEEN, depth=2)
            for r in _frames(brood_queen, e40.QUEEN_PHASES, e40.QUEEN_POSES)]


def obsidian_heart_cells():
    return [render(r, OBSIDIAN) for r in _frames(obsidian_heart, e40.OBS_PHASES, e40.OBS_POSES)]


#: sheet name -> builder. Cell sizes and anchors are enemies40.SHEETS', in
#: world units; the sheet is S times that in texels.
BUILDERS = {
    "boss_grove": grove_cells,
    "boss_tide_maw": tide_maw_cells,
    "boss_stormcrest": stormcrest_cells,
    "boss_brood_queen": brood_queen_cells,
    "boss_obsidian_heart": obsidian_heart_cells,
}


def build_sheet(name):
    """Write one boss sheet natively at S (selout on, as every character
    sheet is) and return its frame count. The name must be listed in
    tools/art/hd_native/hdbosses.txt, or publish_hd() would double it."""
    if name not in palette.HD_NATIVE:
        raise SystemExit("hd_bosses: %s is drawn at %dx but is not in HD_NATIVE" % (name, S))
    _, w, h, _, _ = e40.SHEETS[name]
    cells = BUILDERS[name]()
    palette.sheet(name, cells, w * S, h * S, selout=True)
    return len(cells)
