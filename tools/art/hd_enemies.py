"""The seven ordinary enemies drawn natively at ART_SCALE (HD pass, phase H1).

docs/plan-hd.md, step 2. Each enemy is the SAME puppet as
tools/art/enemies40.py: the same poses, the same parts in the same places,
given in world units. `HCanvas` rasterises them at ART_SCALE texels per unit,
so the silhouette is the 1x silhouette sampled twice as finely. On top of it,
every builder spends the new texels on what a 32 px cell could not hold:

  walker   clubbed antennae, a faceted eye with a catch-light, toothed
           mandibles, rows of punctures with lit lips, a fine elytral seam,
           jointed legs with tarsal claws, belly segments
  jumper   warty hide, a gold iris and slit pupil, an angry lid on the tell,
           a lipped grin with a row of fangs, chevrons on the big thigh, toes
  shooter  veined petals, a ring of teeth around the face, a seed spiral in
           the disc, fangs round the open throat, leaf veins, stem thorns
  swimmer  crescent scales, a lateral line, a scowling eye with a pupil,
           interlocking triangular teeth, rayed fins
  charger  fur strokes along the hide, single bristles in the crest, an eye
           with a brow that hardens on the tell, two nostrils, a tapered
           shaded tusk, cloven hooves, a tail tuft, puffs of steam, stars
  dropper  plated carapace with pits, a specular scute, spined and clawed
           legs, glinting eyes, chelicerae
  flyer    veined glassy wings, banded fuzz, a faceted eye, a glossy
           abdomen, a segmented antenna and jointed legs

Every TELL named on enemies40's builders is kept, and drawn at least as hard:
the frame dicts are the 1x ones (enemies40.J_*, S_*, charger poses ...).

Shading is kaya40.shade_hd (whole ramp steps, a two-texel rim), then
kaya40._hand_aa on the ink's stair-steps; the sheet goes through selout like
every character sheet. Sheets are saved at ART_SCALE; their names are listed
in tools/art/hd_native/hdenemies.txt so palette.publish_hd leaves them alone.
"""

import math

from . import enemies40 as e40
from . import kaya40
from . import palette
from .enemies40 import Canvas, limb, polar

S = palette.ART_SCALE


def _h(*k):
    """A deterministic hash in [0, 1) -- texture placement that never moves
    between runs, so regenerated sheets are byte-stable."""
    v = 2166136261
    for n in k:
        v = ((v ^ (int(n) & 0xffffffff)) * 16777619) & 0xffffffff
    v ^= v >> 13
    v = (v * 0x5bd1e995) & 0xffffffff
    v ^= v >> 15
    return (v & 0xffff) / 65536.0


# ====================================================================== canvas
class HCanvas(Canvas):
    """A Canvas whose primitives take WORLD units and rasterise at S texels per
    unit. `t()`, `dot()` and `stroke()` place single texels, for the detail
    that only exists at this density."""

    def __init__(self, w, h, s=S):
        super().__init__(w * s, h * s)
        self.s = s

    # -- shapes, world units
    def capsule(self, a, b, r0, ch, r1=None, only=None):
        s = self.s
        r1 = r0 if r1 is None else r1
        Canvas.capsule(self, (a[0] * s, a[1] * s), (b[0] * s, b[1] * s), r0 * s, ch,
                       r1 * s, only=only)

    def ellipse(self, c, rx, ry, ch, ang=0.0, clip=None, only=None):
        s = self.s
        cl = None if clip is None else (lambda x, y: clip(x / s, y / s))
        Canvas.ellipse(self, (c[0] * s, c[1] * s), rx * s, ry * s, ch, ang=ang, clip=cl,
                       only=only)

    def poly(self, pts, ch, only=None):
        s = self.s
        Canvas.poly(self, [(x * s, y * s) for x, y in pts], ch, only=only)

    def px(self, x, y, ch):
        """A whole world unit (s x s texels): what px() meant at 1x."""
        s = self.s
        fx, fy = int(math.floor(x)) * s, int(math.floor(y)) * s
        for dy in range(s):
            for dx in range(s):
                self.set(fx + dx, fy + dy, ch)

    # -- single texels
    def t(self, x, y, ch, only=None):
        """One texel at texel coordinates."""
        x, y = int(math.floor(x)), int(math.floor(y))
        if only is None or self.get(x, y) in only:
            self.set(x, y, ch)

    def dot(self, x, y, ch, only=None):
        """One texel at WORLD coordinates."""
        self.t(x * self.s, y * self.s, ch, only)

    def stroke(self, pts, ch, only=None):
        """A one-texel line through WORLD points."""
        s = self.s
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            x0, y0, x1, y1 = x0 * s, y0 * s, x1 * s, y1 * s
            n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
            for k in range(n + 1):
                u = k / n
                self.t(x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, ch, only)

    def at(self, x, y):
        """The character under a WORLD point."""
        return self.get(int(math.floor(x * self.s)), int(math.floor(y * self.s)))

    def scatter(self, n, box, ch, only, seed, lip=None, lip_d=(1, 1)):
        """`n` single-texel marks inside `box` (world x0, y0, x1, y1), painted
        only over `only`. With `lip`, each mark gets a second texel offset by
        `lip_d` -- a pit with a lit lip, a wart with its shadow."""
        x0, y0, x1, y1 = box
        for k in range(n):
            x = (x0 + _h(seed, k, 1) * (x1 - x0)) * self.s
            y = (y0 + _h(seed, k, 2) * (y1 - y0)) * self.s
            if self.get(int(x), int(y)) not in only:
                continue
            self.t(x, y, ch)
            if lip is not None:
                self.t(x + lip_d[0], y + lip_d[1], lip, only)

    def outline(self, ink='k'):
        """kaya40.HDCanvas's weighted line: one ink texel all round, a second
        on the shadow side (right and below), so the line keeps its 1x weight
        where the form turns from the light and is fine where it catches it."""
        Canvas.outline(self, ink)
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


def eye(c, ctr, r, iris, pupil='k', glint='W', ring=None, slit=False, look=(0.25, 0.1)):
    """An eye at HD: an iris disc, a pupil set toward where it looks, and a
    one-texel catch-light at its upper left. `ring` paints an ink socket."""
    if ring:
        c.ellipse(ctr, r + 0.5, r + 0.45, ring)
    c.ellipse(ctr, r, r * 0.95, iris)
    px, py = ctr[0] + look[0] * r, ctr[1] + look[1] * r
    if slit:
        c.capsule((px, py - r * 0.6), (px, py + r * 0.6), 0.32, pupil)
    else:
        c.ellipse((px, py), r * 0.45, r * 0.5, pupil)
    c.dot(ctr[0] - r * 0.45, ctr[1] - r * 0.5, glint)


# ================================================================= walker
# THE BARK BEETLE, 32x24 world units, the 14x11 box at (9, 13).
WALKER = dict(e40.WALKER)
WALKER.update({
    'e': ("purple", 1),          # puncture pits, seam lip shadow
    'S': ("purple", 6),          # specular on the shell
    'R': ("ember", 2),           # eye facets in shade
    'W': ("metal", 6),           # catch-light
    'M': ("gold", 5),            # mandible tip
    'n': ("gold", 1),            # mandible tooth notch
    'j': ("purple", 5),          # leg joints, lit
    'c': ("purple", 1),          # tarsal claws, belly segment lines
})


def walker_hd(i, n=6):
    c = HCanvas(32, 24)
    fy = 23.6
    ph = 2 * math.pi * i / n
    bob = 0.5 * abs(math.sin(ph))
    sy = 13.8 - bob
    feet = []

    def leg(hip, base_x, phase, ch, reach=1.0):
        s = math.sin(ph + phase)
        fx = base_x + 2.2 * math.cos(ph + phase)
        lift = max(0.0, s) * 2.2
        foot = (fx, fy - 0.4 - lift)
        kn = limb(c, hip, foot, 4.4 * reach, 4.8 * reach, 0.8, 0.55, ch,
                  bend=-1 if fx < hip[0] else 1)
        feet.append((hip, kn, foot, ch))

    for hx, bx, p in ((12.5, 9.5, 0.0), (16.0, 16.0, math.pi), (19.0, 22.5, 0.0)):
        leg((hx, sy + 3.0), bx, p + 0.3, 'Q')
    # antennae: elbowed, thinner than 1x could draw, ending in a club
    sway = math.sin(ph) * 0.6
    for off, ch in ((0.0, 'Q'), (1.2, 'q')):
        e1 = (27.6 + off * 0.4, 11.2 - off * 0.3 + sway * 0.5)
        tip = (30.4 + off * 0.3, 9.4 + sway - off * 0.6)
        c.path([(24.6 + off * 0.3, sy - 0.4), e1, tip], 0.42, ch, 0.36)
        c.ellipse(tip, 0.95, 0.75, ch, ang=-30.0)
        c.dot(tip[0] - 0.3, tip[1] - 0.3, 'j', only=ch)
    # elytra
    c.ellipse((14.6, sy), 9.0, 6.3, 'p', clip=lambda x, y: y < sy + 4.6)
    c.ellipse((14.6, sy + 3.4), 8.4, 2.0, 'P')
    for k in range(4):                                             # belly segments
        x = 9.0 + k * 3.4
        c.stroke([(x, sy + 2.4), (x - 0.6, sy + 4.6)], 'c', only='P')
    c.path([(9.0, sy - 3.8), (13.0, sy - 5.0), (17.0, sy - 4.8)], 0.6, 'L', only='p')
    c.capsule((11.6, sy - 4.6), (13.2, sy - 4.9), 0.3, 'S', only='L')
    # the seam: a fine ink line with a shadowed lip under it
    seam = [(21.0, sy - 5.4), (15.0, sy - 5.9), (8.0, sy - 3.2), (5.9, sy + 1.0)]
    c.stroke([(x, y + 0.5) for x, y in seam], 'e', only='p')
    c.stroke(seam, 'k', only='pPL')
    # three rows of punctures following the dome, each a pit with a lit lip
    for row, (y0, x0, x1) in enumerate(((-2.8, 8.0, 19.0), (-0.6, 7.0, 19.6),
                                        (1.5, 7.6, 18.6))):
        m = 7
        for k in range(m):
            x = x0 + (x1 - x0) * (k + 0.5 * (row % 2)) / m
            y = sy + y0 + 0.35 * math.sin(k * 1.3 + row)
            if c.at(x, y) == 'p':
                c.dot(x, y, 'e')
                c.dot(x + 0.5, y + 0.5, 'd', only='p')
    # pronotum and head
    c.ellipse((22.4, sy + 0.4), 3.6, 3.9, 'h')
    c.capsule((21.4, sy - 2.6), (23.6, sy - 2.4), 0.35, 'q', only='h')   # pronotum ridge
    c.path([(20.4, sy - 3.3), (19.4, sy + 0.2), (20.1, sy + 3.4)], 0.4, 'k')
    c.ellipse((25.6, sy + 2.0), 2.4, 2.3, 'h')
    c.stroke([(24.0, sy + 0.2), (24.2, sy + 3.8)], 'k', only='h')       # head suture
    # compound eye: ember with a shaded lower rim, facets, a catch-light
    ex, ey = 25.9, sy + 1.0
    c.ellipse((ex, ey), 1.15, 1.05, 'r')
    c.ellipse((ex + 0.35, ey + 0.4), 0.8, 0.6, 'R', only='r')
    c.dot(ex + 0.2, ey, 'R', only='r')
    c.dot(ex - 0.5, ey - 0.5, 'W')
    # mandibles, opening and closing with the gait; a tooth on each
    jaw = 0.6 * math.sin(ph * 2)
    for (a, b, r) in (((26.6, sy + 3.5), (28.6, sy + 3.2 - jaw), 0.55),
                      ((26.4, sy + 3.9), (28.4, sy + 4.6 + jaw), 0.5)):
        c.capsule(a, b, r, 'm', r * 0.55)
        c.dot(b[0] - 0.2, b[1] - 0.3, 'M', only='m')
        c.dot((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 0.3, 'n', only='m')
    for hx, bx, p in ((11.0, 8.0, math.pi), (15.5, 16.5, 0.0), (19.5, 25.0, math.pi)):
        leg((hx, sy + 3.6), bx, p, 'q')
    # joints and tarsal claws on every leg (near legs drawn last, on top)
    for hip, kn, foot, ch in feet:
        c.dot(kn[0] - 0.3, kn[1] - 0.3, 'j' if ch == 'q' else 'q', only=ch)
        d = 1 if foot[0] >= hip[0] else -1
        c.stroke([(foot[0], foot[1] + 0.4), (foot[0] + d * 0.9, foot[1] + 0.6)], 'c')
    c.outline()
    return c.rows()


# ================================================================= jumper
# THE EMBER HOPPER, 32x32, the 12x11 box at (10, 21).
# TELL -- the crouch, as at 1x: knees above the back, spines up and gold. At
# HD the eyes also go from round and watchful to lidded slits.
JUMPER = dict(e40.JUMPER)
JUMPER.update({
    'i': ("gold", 4),            # iris
    'W': ("metal", 6),           # catch-light
    'v': ("ember", 1),           # wart shadow, chevrons, toe creases
    'U': ("ember", 6),           # wart highlight, lip
    'b': ("ember", 4),           # belly folds, lit
    'Y': ("gold", 6),            # spine tips at the tell
    'L': ("ember", 4),           # the lid
})


def jumper_hd(p):
    c = HCanvas(32, 32)
    by, rx, ry = p["by"], p["rx"], p["ry"]
    bx = 16.0
    hip = (bx - 2.2, by + 0.8)
    k = (p["knee"][0] + 1.4, p["knee"][1] + 0.8)
    c.capsule((hip[0] + 1.0, hip[1]), k, 1.5, 'R', 1.1)
    c.capsule(k, (p["foot"][0] + 1.8, p["foot"][1]), 0.9, 'R', 0.6)
    c.capsule((bx + 3.0, by + 2.0), (bx + 4.2 + p["front"], 31.0), 0.7, 'R')
    # spines: the same comb, each with a lit edge and, raised, a hot tip
    for j, t in enumerate((-0.75, -0.4, -0.05, 0.3)):
        ang = math.degrees(t * 1.2)
        base = (bx + math.sin(t * 1.25) * rx * 0.9, by - math.cos(t * 1.25) * ry * 0.85)
        ln = p["spine"] + (0.6 if j in (1, 2) else 0.0)
        c.spike(base, ang - 22, ln, 1.1, p["spine_ch"])
        tip = polar(base, ln * 0.82, ang - 22)
        if p["spine_ch"] == 'y':
            c.ellipse(tip, 0.55, 0.55, 'Y', only='y')
        c.stroke([polar(base, ln * 0.25, ang - 30), polar(base, ln * 0.7, ang - 25)], 'v',
                 only=p["spine_ch"])
    # the body
    c.ellipse((bx, by), rx, ry, 'r')
    c.ellipse((bx + 0.4, by + ry * 0.55), rx * 0.8, ry * 0.4, 'R')
    for k2 in range(3):                                            # belly folds
        yy = by + ry * (0.45 + 0.18 * k2)
        c.stroke([(bx - rx * 0.4, yy), (bx + rx * 0.7, yy - 0.2)], 'b', only='R')
    c.ellipse((bx - 1.0, by - ry * 0.45), rx * 0.55, ry * 0.35, 'u')
    # warts: bumps with a lit crown and a shadow under, over the hide only
    for k2 in range(14):
        a = _h(7, k2) * 2 * math.pi
        d = 0.35 + 0.55 * _h(8, k2)
        x = bx + math.cos(a) * rx * d - 0.6
        y = by + math.sin(a) * ry * d * 0.75 - 0.6
        if c.at(x, y) in 'ru' and c.at(x, y + 0.5) in 'ru':
            c.dot(x, y, 'U')
            c.dot(x, y + 0.5, 'v')
    # eyes: two bulbs, gold irises, slit pupils; on the tell a lid comes down
    for ex in (bx + 1.8, bx + 5.2):
        e = (ex, by - ry + 0.9)
        c.ellipse(e, 1.3, 1.4, 'w')
        c.ellipse((e[0] + 0.3, e[1] + 0.15), 0.8, 0.9, 'i', only='w')
        c.capsule((e[0] + 0.45, e[1] - 0.35), (e[0] + 0.45, e[1] + 0.65), 0.28, 'k', only='wi')
        c.dot(e[0] - 0.45, e[1] - 0.55, 'W', only='wi')
        if p["lid"] > 0.0:
            # The lid's edge: the higher it rides, the calmer. At the coil
            # it covers the top half, a hard angry line across the eye.
            lid_y = e[1] - 1.4 + 1.5 * p["lid"]
            c.ellipse(e, 1.3, 1.4, 'L', clip=lambda x, y, ly=lid_y, e=e: y < ly - (x - e[0]) * 0.35)
            c.stroke([(e[0] - 1.3, lid_y + 0.45), (e[0] + 1.3, lid_y - 0.45)], 'k', only='wiLkW')
    # mouth: a wide grin with a lip above it and a row of fangs below
    my = by + 1.0
    m0, m1 = (bx + 2.0, my), (bx + rx - 0.4, my - 0.6)
    c.capsule(m0, m1, 0.42, 'm')
    c.stroke([(m0[0], m0[1] - 0.6), (m1[0] - 0.4, m1[1] - 0.7)], 'U', only='ru')
    for f, ln in ((0.35, 0.7), (0.62, 1.05), (0.85, 0.6)):
        fx = lerp(m0[0], m1[0], f)
        fy = lerp(m0[1], m1[1], f) + 0.3
        c.capsule((fx, fy), (fx + 0.1, fy + ln), 0.32, 'w', 0.12)
    # near front leg, with three toes
    ff = (bx + 3.0 + p["front"], 31.0)
    c.capsule((bx + 2.0, by + 2.4), ff, 0.8, 'u')
    for tx in (-0.8, 0.2, 1.1):
        c.capsule((ff[0], ff[1] - 0.2), (ff[0] + tx, ff[1] + 0.3), 0.32, 'u')
    # near hind leg: the big thigh with chevrons, the shin, a long toed foot
    c.capsule(hip, p["knee"], 2.8, 'u', 1.6)
    kx, ky = p["knee"]
    dx, dy = kx - hip[0], ky - hip[1]
    L = math.hypot(dx, dy) or 1.0
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux
    for f in (0.3, 0.5, 0.7):
        cx, cy = hip[0] + dx * f, hip[1] + dy * f
        w = 2.2 - f * 1.2
        c.stroke([(cx + nx * w, cy + ny * w), (cx + ux * 0.8, cy + uy * 0.8),
                  (cx - nx * w, cy - ny * w)], 'v', only='u')
    c.capsule(p["knee"], p["foot"], 1.0, 'r', 0.7)
    c.dot(kx - 0.4, ky - 0.6, 'U', only='u')                       # the kneecap
    fo = p["foot"]
    c.capsule(fo, (fo[0] - 2.0, fo[1]), 0.6, 'r')
    for tx in (-2.9, -2.3):
        c.capsule((fo[0] - 1.8, fo[1]), (fo[0] + tx, fo[1] + 0.4), 0.3, 'r')
    c.dot(fo[0] - 1.0, fo[1] - 0.1, 'v', only='r')
    # dust: two-texel puffs, a lit top over a darker base
    for d in range(p["dust"]):
        for x, y in ((4.0 + d * 2.6, 30.6 - (d % 2)), (26.5 - d * 2.2, 30.6 - ((d + 1) % 2))):
            c.ellipse((x + 0.5, y + 0.4), 0.8, 0.55, 'o')
            c.dot(x + 0.2, y, 'y', only='o')
    c.outline()
    return c.rows()


def lerp(a, b, t):
    return a + (b - a) * t


# ================================================================= shooter
# THE SPITTING BLOOM, 32x32, the 12x14 box at (10, 18).
# TELL -- the bloom opens and the throat lights, as at 1x; at HD a ring of
# fangs shows round the throat as it opens.
SHOOTER = dict(e40.SHOOTER)
SHOOTER.update({
    'v': ("purple", 1),          # petal veins
    'V': ("purple", 4),          # petal tips, lit
    'W': ("metal", 6),           # catch-light on the spit
    't': ("metal", 4),           # the face ring's notches
    's': ("gold", 3),            # seeds
    'f': ("metal", 6),           # fangs round the throat
    'n': ("grass", 2),           # leaf side veins
    'T': ("grass", 1),           # stem thorns
    'O': ("gold", 4),            # throat glow ring
})


def shooter_hd(p):
    c = HCanvas(32, 32)
    hx, hy = p["hx"], p["hy"]
    # roots: the mound and a few tendrils into the ground
    c.ellipse((16.0, 31.0), 4.6, 1.4, 'g')
    for k, (x0, x1) in enumerate(((13.0, 11.2), (15.6, 15.2), (18.4, 20.4))):
        c.stroke([(x0, 31.0), (x1, 31.9)], 'G', only='g')
    for side in (-1, 1):
        tip = (16.0 + side * 8.6, 26.4 + p["leaf"] * side)
        mid = (16.0 + side * 4.6, 25.6 + p["leaf"] * side * 0.5)
        c.path([(16.0, 30.0), mid, tip], 1.7, 'l', 0.5)
        c.path([(16.0 + side * 1.0, 29.6), (mid[0], mid[1] + 0.6), tip], 0.3, 'G', only='l')
        for f in (0.3, 0.55, 0.78):                                # side veins
            vx = lerp(16.0 + side * 1.0, tip[0], f)
            vy = lerp(29.6, tip[1], f) + 0.2
            c.stroke([(vx, vy), (vx + side * 0.9, vy - 1.0)], 'n', only='l')
            c.stroke([(vx, vy), (vx + side * 0.9, vy + 0.8)], 'n', only='l')
    # stem, with two thorns
    stem = [(16.0, 31.0), (16.0 - p["lean"] * 0.4, 28.0), (hx - p["lean"] * 0.3, hy + 3.0)]
    c.path(stem, 1.2, 'G', 1.0)
    for f, side in ((0.35, -1), (0.62, 1)):
        a, b = (stem[0], stem[1]) if f < 0.5 else (stem[1], stem[2])
        u = (f / 0.5) if f < 0.5 else ((f - 0.5) / 0.5)
        x, y = lerp(a[0], b[0], u), lerp(a[1], b[1], u)
        c.spike((x + side * 0.8, y), side * 60.0, 1.4, 0.4, 'T')
    # petals, back row then front, each with its own ink edge and a vein
    n = 6
    for ch, r_mul, off in (('P', 1.1, 30.0), ('p', 1.0, 0.0)):
        for k in range(n):
            ang = k * 360.0 / n + off + p["lean"] * 6.0
            r = p["pr"] * r_mul
            ctr = polar((hx, hy), r * 0.45 + p["plen"] * 0.55, ang)
            c.ellipse(ctr, p["plen"] + 0.6, p["pw"] + 0.6, 'k', ang=ang - 90.0)
            c.ellipse(ctr, p["plen"], p["pw"], ch, ang=ang - 90.0)
            tip = polar(ctr, p["plen"] * 0.7, ang)
            c.stroke([polar(ctr, -p["plen"] * 0.4, ang), tip], 'v', only=ch)
            if ch == 'p':
                c.ellipse(polar(ctr, p["plen"] * 0.55, ang), p["plen"] * 0.3,
                          p["pw"] * 0.45, 'V', ang=ang - 90.0, only='p')
    # face: a white ring notched into teeth, the seed disc, the mouth
    fx = hx + 0.8
    fr = p["face"]
    c.ellipse((fx, hy), fr, fr * 0.95, 'w')
    m = max(10, int(fr * 5))
    for k in range(m):
        a = k * 360.0 / m
        c.dot(*polar((fx, hy), fr - 0.35, a), 't', only='w')
    c.ellipse((fx, hy), fr - 0.9, (fr - 0.9) * 0.95, 'y')
    golden = 137.508
    for k in range(int(fr * 6)):                                   # the seed spiral
        rr = 0.55 * math.sqrt(k + 0.5)
        if rr > fr - 1.1:
            break
        c.dot(*polar((fx, hy), rr, k * golden), 's', only='y')
    if p["mouth"] > 0.0:
        mo = (fx + 0.4, hy + 0.2)
        c.ellipse(mo, p["mouth"], p["mouth"] * 0.9, 'm')
        if p["throat"] != 'm':
            c.ellipse((fx + 0.4, hy + 0.3), p["mouth"] * 0.7, p["mouth"] * 0.65, 'r')
            c.ellipse((fx + 0.4, hy + 0.3), p["mouth"] * 0.5, p["mouth"] * 0.48, 'O', only='r')
            c.ellipse((fx + 0.4, hy + 0.3), p["mouth"] * 0.4, p["mouth"] * 0.4, p["throat"])
        # fangs round the rim, pointing in: the more it opens, the more show
        nf = int(p["mouth"] * 3)
        for k in range(nf):
            a = k * 360.0 / max(1, nf) + 15.0
            root = polar(mo, p["mouth"] * 0.98, a)
            tipf = polar(mo, p["mouth"] * 0.55, a)
            c.capsule(root, tipf, 0.32, 'f', 0.1)
    else:
        c.capsule((fx - 0.8, hy + 0.6), (fx + 1.6, hy + 0.6), 0.42, 'm')
        c.dot(fx - 0.6, hy + 0.1, 'f')
        c.dot(fx + 1.2, hy + 0.1, 'f')
    if p["spit"]:
        sp = (fx + p["mouth"] + 2.4, hy)
        c.ellipse(sp, 1.3, 1.1, 'p')
        c.ellipse((sp[0] + 0.3, sp[1] + 0.3), 0.7, 0.5, 'P', only='p')
        c.dot(sp[0] - 0.5, sp[1] - 0.5, 'W')
        c.ellipse((fx + p["mouth"] + 4.6, hy - 1.0), 0.55, 0.55, 'p')
        c.ellipse((fx + p["mouth"] + 0.9, hy + 1.2), 0.4, 0.4, 'p')
    c.outline()
    return c.rows()


# ================================================================= swimmer
# THE RIVER PIRANHA, 32x24, the 14x9 box at (9, 8).
SWIMMER = dict(e40.SWIMMER)
SWIMMER.update({
    's': ("water", 4),           # scale crescents
    'D': ("water", 2),           # fin rays
    'B': ("ember", 5),           # belly sheen
    'v': ("ember", 2),           # belly speckle
    'i': ("gold", 4),            # iris
    'W': ("metal", 6),           # catch-light
    'T': ("metal", 4),           # tooth shade
})


def swimmer_hd(i, n=6):
    c = HCanvas(32, 24)
    ph = 2 * math.pi * i / n
    tail = math.sin(ph) * 3.2
    bend = math.sin(ph - 0.9) * 0.8
    gape = max(0.0, math.sin(ph * 1.0 + 0.6)) * 1.6
    cx, cy = 16.6, 12.4 + bend * 0.3
    root = (cx - 8.8, cy + bend * 0.5)
    tpts = [root, (root[0] - 5.6, cy - 4.6 + tail), (root[0] - 3.6, cy + tail * 0.5),
            (root[0] - 5.6, cy + 4.6 + tail)]
    c.poly(tpts, 'C')
    for f in (-0.75, -0.4, 0.4, 0.75):                              # tail rays
        end = (root[0] - 5.2 + abs(f) * 0.6, cy + tail * (0.5 + abs(f) * 0.5) + f * 5.2)
        c.stroke([(root[0] - 0.4, root[1]), end], 'D', only='C')
    dorsal = [(cx - 3.0, cy - 5.2), (cx - 5.6, cy - 8.4 + bend), (cx + 1.6, cy - 5.6)]
    anal = [(cx - 3.6, cy + 5.0), (cx - 6.0, cy + 7.4 - bend), (cx - 0.4, cy + 5.4)]
    c.poly(dorsal, 'C')
    c.poly(anal, 'C')
    for fin, sgn in ((dorsal, -1), (anal, 1)):
        for f in (0.25, 0.55, 0.85):
            b0 = (lerp(fin[0][0], fin[2][0], f), lerp(fin[0][1], fin[2][1], f) - sgn * 0.2)
            c.stroke([b0, (lerp(b0[0], fin[1][0], 0.75), lerp(b0[1], fin[1][1], 0.75))], 'D',
                     only='C')
    c.ellipse((cx, cy), 9.2, 5.8, 'c', clip=lambda x, y: x < cx + 6.6 or y > cy - 4.0)
    c.ellipse((cx + 4.0, cy + 0.6), 5.6, 5.0, 'c')
    c.ellipse((cx - 0.6, cy + 3.0), 7.2, 2.6, 'r', clip=lambda x, y: y > cy + 1.0)
    c.capsule((cx - 4.0, cy + 2.4), (cx + 2.0, cy + 2.1), 0.3, 'B', only='r')
    c.scatter(10, (cx - 7.0, cy + 2.8, cx + 4.0, cy + 5.2), 'v', 'r', 31)
    # scales: offset rows of crescents over the back, finer toward the tail
    for row in range(4):
        y = cy - 4.2 + row * 1.6
        for k in range(8):
            x = cx - 7.0 + k * 1.8 + (0.9 if row % 2 else 0.0)
            if x > cx + 3.0:
                continue
            c.stroke([(x - 0.6, y - 0.2), (x, y + 0.45), (x + 0.6, y - 0.2)], 's', only='c')
    c.capsule((cx - 6.0, cy - 2.0), (cx + 3.0, cy - 3.2), 0.38, 'b')
    for k in range(6):                                             # lateral line
        c.dot(cx - 6.5 + k * 1.7, cy + 0.6 - k * 0.12, 'b', only='cs')
    # gill line, a fine ink stroke with a lit lip ahead of it
    gill = [(cx + 3.2, cy - 3.4), (cx + 2.4, cy), (cx + 3.0, cy + 3.4)]
    c.stroke([(x + 0.5, y) for x, y in gill], 'b', only='cs')
    c.path(gill, 0.32, 'k')
    # the mouth: an underslung jaw, interlocking triangular teeth
    jx, jy = cx + 9.2, cy + 2.0
    c.poly([(jx - 3.6, jy - 0.8), (jx + 0.4, jy - 1.4 - gape * 0.4),
            (jx + 0.6, jy + 1.0 + gape), (jx - 3.0, jy + 1.2)], 'm')
    for t in range(4):
        ux = jx - 2.8 + t * 0.95
        uy = jy - 1.0 - gape * 0.2
        c.poly([(ux - 0.4, uy - 0.1), (ux + 0.45, uy - 0.1), (ux + 0.05, uy + 0.95)], 'w')
        c.dot(ux + 0.15, uy + 0.4, 'T', only='w')
        lx = jx - 2.35 + t * 0.95
        ly = jy + 1.1 + gape * 0.8
        c.poly([(lx - 0.4, ly + 0.1), (lx + 0.45, ly + 0.1), (lx + 0.05, ly - 0.95)], 'w')
    # pectoral fin, beating, with rays
    pa = 20 + math.sin(ph + 1.0) * 25
    c.ellipse((cx + 1.0, cy + 1.4), 2.4, 1.0, 'C', ang=pa)
    for f in (-0.5, 0.5):
        c.stroke([(cx + 2.6, cy + 1.4 + f * 0.3),
                  polar((cx + 2.6, cy + 1.4), 3.6, 270 + pa + f * 22)], 'D', only='C')
    # the eye: gold iris, pupil forward, a catch-light, and a hard brow
    e = (cx + 5.8, cy - 1.6)
    eye(c, e, 1.4, 'y', look=(0.35, 0.15))
    c.ellipse((e[0] + 0.2, e[1] + 0.4), 1.0, 0.6, 'i', only='y')
    c.ellipse((e[0] + 0.5, e[1] + 0.15), 0.6, 0.65, 'k')
    c.dot(e[0] - 0.6, e[1] - 0.7, 'W')
    c.path([(e[0] - 1.6, e[1] - 2.0), (e[0] + 1.4, e[1] - 1.1)], 0.36, 'k')
    c.outline()
    return c.rows()


# ================================================================= charger
# THE THORN BOAR, 32x24, the 14x11 box at (9, 13).
# TELL -- the crest stands up in three beats, the head drops, a forehoof paws,
# the eye goes red. At HD the brow also clamps down over the eye.
CHARGER = dict(e40.CHARGER)
CHARGER.update({
    'f': ("dirt", 1),            # fur strokes in shadow
    'F': ("dirt", 3),            # fur strokes, lit
    'Y': ("gold", 6),            # bristle tips, raised
    'R': ("ember", 2),           # bristle roots
    'W': ("metal", 6),           # catch-light
    'T': ("metal", 4),           # tusk shade
    'i': ("skin", 2),            # inner ear
    'S': ("metal", 6),           # steam core
    'g': ("gold", 6),            # star centre
})


def charger_hd(p):
    p = dict(e40.C_BASE, **p)
    c = HCanvas(32, 24)
    fy = 23.4
    dy, hd = p["dy"], p["head"]
    bx, by = 14.4, 13.6 + dy
    g = p["gait"]

    def foot(base_x, phase, amp):
        if g is None:
            return base_x, 0.0
        return (base_x + amp * math.cos(g + phase),
                max(0.0, math.sin(g + phase)) * 2.0 * p["stride"])

    def hoof(fx, fyy):
        c.capsule((fx, fyy), (fx + 0.6, fyy + 0.5), 0.8, 'h')
        c.stroke([(fx + 0.4, fyy - 0.2), (fx + 0.5, fyy + 1.0)], 'k', only='h')   # cloven

    for hx, ph in ((9.0, math.pi), (19.0, 0.0)):
        fx, lift = foot(hx - 0.4, ph, 2.0 * p["stride"])
        c.capsule((hx, by + 2.0), (fx, fy - 0.6 - lift), 1.2, 'n', 0.9)
        hoof(fx - 0.2, fy - 0.9 - lift)
    # crest: the 1x seven bristles, each split into single hairs, with roots
    # in the hide and (raised) hot tips
    for k in range(7):
        t = k / 6.0
        base = (8.0 + t * 12.0, by - 5.4 + math.sin(t * math.pi) * -0.8)
        ln = p["crest"] * (0.7 + 0.5 * math.sin(t * math.pi))
        # At rest the 1x crest read as spikes only because 1x pixels are
        # coarse; at 2x it lay down into a band. The resting bristles stand
        # 10 degrees prouder and thinner, each with its own ink edge laid
        # before the fill. The tell is still far the tallest outline.
        rest = p["crest_ch"] == 'r'
        a = p["crest_ang"] + (k % 2) * 6.0 + (10.0 if rest else 0.0)
        wd = 0.75 if rest else 0.9
        c.spike(base, a, ln + 0.45, wd + 0.3, 'k')
        c.spike(base, a, ln, wd, p["crest_ch"])
        c.spike((base[0] + 0.7, base[1] + 0.2), a + 7.0, ln * 0.8, 0.5, p["crest_ch"])
        c.stroke([polar(base, 0.2, a), polar(base, ln * 0.4, a)], 'R', only=p["crest_ch"])
        if p["crest_ch"] == 'y':
            c.ellipse(polar(base, ln * 0.8, a), 0.45, 0.45, 'Y', only='y')
    # tail, with a tuft
    c.path([(5.6, by - 1.4), (3.8, by - 2.6), (4.2, by - 0.4)], 0.5, 'm')
    for a in (-160, 160, 180):
        c.capsule((4.2, by - 0.4), polar((4.2, by - 0.4), 1.4, a), 0.35, 'n', 0.15)
    # barrel, hump, belly, lit shoulder
    c.ellipse((bx, by), 9.2, 5.0, 'm')
    c.ellipse((bx + 4.6, by - 1.0), 5.0, 4.8, 'm')
    c.ellipse((bx - 0.6, by + 3.2), 7.0, 1.8, 'n')
    c.ellipse((bx + 3.0, by - 3.0), 4.0, 1.6, 'M')
    # fur: short strokes swept back and down, dark in the hide, lit on the
    # shoulder, so the barrel reads as hair and not as a brown balloon
    for k in range(34):
        x = bx - 8.4 + _h(11, k) * 15.0
        y = by - 4.4 + _h(12, k) * 8.0
        under = c.at(x, y)
        if under not in 'mM':
            continue
        ch = 'F' if under == 'M' or _h(13, k) > 0.7 else 'f'
        c.stroke([(x, y), (x - 0.9, y + 0.45)], ch, only='mMn')
    # head
    hx0, hy0 = bx + 7.0, by - 1.4
    sx, sy = hx0 + 6.4, by + 3.0 + hd
    c.poly([(hx0 - 1.0, hy0 - 3.0), (hx0 + 2.6, hy0 - 2.4 + hd * 0.4), (sx + 0.4, sy - 1.6),
            (sx + 0.8, sy + 1.4), (hx0 + 1.6, sy + 1.8), (hx0 - 1.6, hy0 + 3.4)], 'm')
    c.stroke([(hx0 + 2.4, hy0 - 1.6 + hd * 0.4), (sx - 0.6, sy - 1.6)], 'M', only='m')  # bridge
    c.stroke([(hx0 + 2.2, sy + 1.2), (sx - 0.6, sy + 1.0)], 'k', only='m')              # mouth
    c.ellipse((sx + 0.6, sy), 1.4, 1.7, 'M')
    c.ellipse((sx + 0.9, sy + 0.5), 0.9, 0.9, 'm', only='M')
    c.dot(sx + 0.9, sy - 0.2, 'h')
    c.dot(sx + 1.4, sy + 0.4, 'h')                                  # two nostrils
    # ear, with the inside showing
    ear = [(hx0 - 0.4, hy0 - 2.6), (hx0 - 2.4, hy0 - 6.4 + hd * 0.3), (hx0 + 1.6, hy0 - 2.8)]
    c.poly(ear, 'M')
    c.poly([(hx0 - 0.2, hy0 - 3.0), (hx0 - 1.8, hy0 - 5.6 + hd * 0.3), (hx0 + 0.8, hy0 - 3.1)],
           'i', only='M')
    # the eye: a dark socket, the iris, a catch-light, and a brow that is
    # lifted on patrol and clamped down when it means to run
    ex, ey = hx0 + 2.0, hy0 - 0.4 + hd * 0.5
    c.ellipse((ex, ey), 0.95, 0.8, 'k')
    c.ellipse((ex + 0.2, ey), 0.6, 0.55, p["eye"])
    c.dot(ex - 0.15, ey - 0.35, 'W')
    if p["eye"] == 'E' or p["crest_ch"] == 'y':
        c.path([(ex - 1.3, ey - 1.6), (ex + 1.2, ey - 0.7)], 0.38, 'k')
    else:
        c.path([(ex - 1.1, ey - 1.3), (ex + 1.2, ey - 1.4)], 0.32, 'k')
    # tusk: curving up past the snout, tapering, shaded underneath
    tusk = [(sx - 1.6, sy + 1.6), (sx + 0.6, sy + 2.0), (sx + 2.2, sy - 0.2)]
    c.path(tusk, 0.6, 'w', 0.3)
    c.stroke([(sx - 1.2, sy + 2.0), (sx + 0.6, sy + 2.3), (sx + 1.7, sy + 1.0)], 'T', only='w')
    for hx, ph, near_front in ((10.4, 0.0, False), (20.0, math.pi, True)):
        fx, lift = foot(hx + 0.2, ph, 2.2 * p["stride"])
        if near_front and p["paw"] > 0.0:
            fx, lift = hx + 1.0 - p["paw"] * 2.6, p["lift"]
        c.capsule((hx, by + 1.6), (fx, fy - 0.8 - lift), 1.4, 'M', 1.0)
        c.stroke([(hx + 0.6, by + 2.4), (fx + 0.5, fy - 2.0 - lift)], 'F', only='M')
        hoof(fx, fy - 0.8 - lift)
    for d in range(p["dust"]):
        x, y = 20.0 - d * 2.4, fy - 0.6 - (d % 2) * 1.2
        c.ellipse((x + 0.5, y + 0.3), 0.85, 0.6, 's')
    if p["dust"] >= 3:                                             # snorted steam
        for k, (x, y, r) in enumerate(((sx + 3.0, sy - 1.6, 0.8), (sx + 4.4, sy - 2.8, 1.0))):
            c.ellipse((x, y), r, r * 0.8, 's')
            c.dot(x - 0.2, y - 0.2, 'S', only='s')
    if p["stars"] >= 0:                                            # dazed
        for k in range(3):
            a = p["stars"] + k * 2 * math.pi / 3
            x, y = hx0 + 1.0 + math.cos(a) * 3.6, hy0 - 4.4 + math.sin(a) * 1.0
            c.capsule((x - 0.9, y), (x + 0.9, y), 0.3, 'y')
            c.capsule((x, y - 0.9), (x, y + 0.9), 0.3, 'y')
            c.dot(x, y, 'g')
    c.outline()
    return c.rows()


def charger_hd_frames():
    # the 1x choreography verbatim: enemies40.charger_frames() builds these
    # same dicts (0-5 patrol, 6-8 wind-up TELL, 9-12 charge, 13-14 dazed)
    walk = [dict(gait=2 * math.pi * i / 6) for i in range(6)]
    wind = [
        dict(dy=0.4, head=1.0, crest=3.6, crest_ang=-30.0, paw=0.4, lift=1.6),
        dict(dy=0.8, head=1.8, crest=5.2, crest_ang=-14.0, crest_ch='y', paw=1.0,
             lift=0.4, dust=2),
        dict(dy=1.2, head=2.4, crest=7.6, crest_ang=-4.0, crest_ch='y', eye='E',
             paw=0.2, lift=1.4, dust=3),
    ]
    run = [dict(gait=2 * math.pi * i / 4, stride=1.6, head=1.6, crest=3.0,
                crest_ang=-70.0, crest_ch='y', dy=0.2) for i in range(4)]
    daze = [dict(dy=0.6, head=-1.0, crest=1.2, stars=k * math.pi / 3) for k in range(2)]
    return [charger_hd(p) for p in walk + wind + run + daze]


# ================================================================= dropper
# THE HOLLOW TICK, 32x32, the 14x12 box at (9, 8).
# TELL -- letting go, as at 1x: legs off the ceiling pair by pair, the body
# swinging, the eyes going red.
DROPPER = dict(e40.DROPPER)
DROPPER.update({
    'S': ("stone", 6),           # specular on the scute
    'e': ("stone", 1),           # pits, seam shadows
    'W': ("metal", 6),           # eye catch-light
    'R': ("ember", 6),           # hot eye core
    'j': ("stone", 5),           # leg joints
    'c': ("metal", 5),           # claws
    'x': ("metal", 4),           # mouthpart shade
})


def _tick_body_hd(c, cx, cy, hang, eye_ch, sw=0.0):
    if hang:
        c.ellipse((cx, cy), 7.0, 5.4, 'a')
        c.poly([(cx - 6.4, cy + 1.6), (cx + sw * 0.6, cy + 11.0), (cx + 6.4, cy + 1.6)], 'a')
        c.ellipse((cx + sw * 0.3, cy + 6.4), 4.0, 3.6, 'a')
        c.ellipse((cx - 0.4, cy + 1.6), 2.6, 4.2, 'A')
        c.ellipse((cx - 1.0, cy + 0.4), 0.9, 1.6, 'S', only='A')
        # plate seams: fine ink with a shadowed lip, the 1x courses
        for pts in (((cx - 5.0, cy + 3.0), (cx, cy + 4.6), (cx + 5.0, cy + 3.0)),
                    ((cx - 3.4, cy + 7.6), (cx, cy + 8.6), (cx + 3.4, cy + 7.6))):
            c.stroke([(x, y + 0.5) for x, y in pts], 'e', only='aA')
            c.stroke(list(pts), 'd', only='aAS')
        c.stroke([(cx - 6.0, cy - 0.8), (cx - 2.2, cy - 3.2), (cx + 2.2, cy - 3.2),
                  (cx + 6.0, cy - 0.8)], 'd', only='a')                    # shoulder plate
        c.scatter(26, (cx - 6.5, cy - 4.5, cx + 6.5, cy + 10.5), 'e', 'a', 41,
                  lip='A', lip_d=(1, 1))
        # mouthparts: a hypostome with barbs between two chelicerae
        mx = cx + sw * 0.6
        c.capsule((mx, cy + 10.6), (mx, cy + 12.8), 0.65, 'w', 0.4)
        for k in range(3):
            c.dot(mx - 0.2, cy + 11.0 + k * 0.5, 'x', only='w')
        for s in (-1, 1):
            c.capsule((mx + s * 0.9, cy + 10.4), (mx + s * 1.4, cy + 11.7), 0.4, 'w', 0.2)
        for ex in (-2.6, 2.6):
            e = (cx + ex + 0.5, cy - 1.7)
            c.ellipse(e, 0.85, 0.8, eye_ch)
            c.dot(e[0] + 0.2, e[1] + 0.2, 'R' if eye_ch == 'r' else 'k')
            c.dot(e[0] - 0.4, e[1] - 0.45, 'W')
    else:
        c.ellipse((cx, cy), 7.4, 5.4, 'a', clip=lambda x, y: y < cy + 3.6)
        c.ellipse((cx - 0.8, cy - 1.4), 4.0, 2.2, 'A')
        c.ellipse((cx - 2.0, cy - 2.4), 1.6, 0.7, 'S', only='A')
        pts = ((cx - 5.6, cy + 0.6), (cx, cy + 1.8), (cx + 5.6, cy + 0.6))
        c.stroke([(x, y + 0.5) for x, y in pts], 'e', only='aA')
        c.stroke(list(pts), 'd', only='aAS')
        c.scatter(18, (cx - 6.8, cy - 4.8, cx + 6.8, cy + 3.4), 'e', 'a', 43,
                  lip='A', lip_d=(1, 1))
        c.ellipse((cx + 6.0, cy + 2.4), 2.0, 1.6, 'a')
        c.capsule((cx + 7.4, cy + 2.8), (cx + 8.6, cy + 3.6), 0.6, 'w', 0.3)
        c.capsule((cx + 7.0, cy + 3.4), (cx + 8.2, cy + 4.4), 0.4, 'w', 0.2)
        c.dot(cx + 7.6, cy + 3.0, 'x', only='w')
        for x in (cx + 5.6, cx + 3.6):
            c.ellipse((x + 0.4, cy + 2.0), 0.75, 0.7, eye_ch)
            c.dot(x + 0.6, cy + 2.2, 'k')
            c.dot(x + 0.1, cy + 1.6, 'W')


def _tick_leg(c, sh, tip, l1, l2, r0, r1, ch, bend):
    """A tick leg at HD: the 1x limb, a lit joint, two spines on the shin and
    a hooked claw at the tip."""
    kn = limb(c, sh, tip, l1, l2, r0, r1, ch, bend=bend)
    c.dot(kn[0] - 0.3, kn[1] - 0.3, 'j', only=ch)
    for f in (0.35, 0.65):
        x, y = lerp(kn[0], tip[0], f), lerp(kn[1], tip[1], f)
        dx, dy = tip[0] - kn[0], tip[1] - kn[1]
        L = math.hypot(dx, dy) or 1.0
        c.dot(x + dy / L * 0.7, y - dx / L * 0.7, 'k')
    dx, dy = tip[0] - kn[0], tip[1] - kn[1]
    L = math.hypot(dx, dy) or 1.0
    c.stroke([tip, (tip[0] + dx / L * 0.7 - dy / L * 0.4, tip[1] + dy / L * 0.7 + dx / L * 0.4)],
             'c')


def dropper_hd(state, k=0):
    c = HCanvas(32, 32)
    ceil = 8.0
    if state in ("cling", "tell"):
        sw = 0.0
        loose = set()
        eye_ch = 'y'
        drop = 0.0
        if state == "tell":
            sw = (-1.2, 1.2, -1.0, 1.4)[k]
            loose = ({0, 7}, {0, 7, 2}, {0, 7, 2, 5}, {0, 7, 2, 5, 3})[k]
            eye_ch = 'r' if k >= 1 else 'y'
            drop = (0.0, 0.4, 0.8, 1.2)[k]
        cx, cy = 15.5 + sw, 12.6 + drop
        for j in range(8):
            side = -1 if j < 4 else 1
            n = j if j < 4 else 7 - j
            sh = (cx + side * (2.0 + n * 1.2), cy - 2.0 + n * 0.8)
            ch = 'd' if n % 2 else 'l'
            if j in loose:
                tip = (sh[0] + side * (5.0 + n * 0.4), sh[1] + 3.0 + ((j + k) % 3) * 1.6)
                _tick_leg(c, sh, tip, 3.6, 3.8, 0.6, 0.45, ch, -side)
            else:
                tip = (15.5 + side * (3.6 + n * 2.9), ceil - 0.6)
                _tick_leg(c, sh, tip, 4.2 + n * 0.7, 3.8 + n * 0.5, 0.7, 0.5, ch, side)
        _tick_body_hd(c, cx, cy, 1, eye_ch, sw)
    elif state == "fall":
        cx, cy = 15.5, 13.0
        for j in range(8):
            side = -1 if j < 4 else 1
            n = j if j < 4 else 7 - j
            sh = (cx + side * (2.4 + n * 1.0), cy - 1.0 + n * 0.6)
            flail = math.sin(k * 2.4 + j) * 1.6
            tip = (sh[0] + side * (4.4 + n * 0.6), sh[1] - 4.0 + n * 1.2 + flail)
            _tick_leg(c, sh, tip, 3.4, 3.4, 0.6, 0.45, 'd' if n % 2 else 'l', side)
        _tick_body_hd(c, cx, cy, 1, 'r')
    else:
        fy = 19.6
        ph = 2 * math.pi * k / 6
        cx, cy = 15.0, 11.6 + 0.4 * abs(math.sin(ph))
        for j in range(4):
            for near in (False, True):
                hx = cx - 4.5 + j * 3.0 + (0.6 if near else 0.0)
                phase = ph + j * math.pi * 0.5 + (math.pi if near else 0.0)
                fx = hx + (j - 1.5) * 1.6 + 1.6 * math.cos(phase)
                lift = max(0.0, math.sin(phase)) * 1.6
                _tick_leg(c, (hx, cy + 2.6), (fx, fy - 0.5 - lift), 3.6, 4.0, 0.75, 0.55,
                          'l' if near else 'd', 1 if j >= 2 else -1)
        _tick_body_hd(c, cx, cy, 0, 'y')
    c.outline()
    return c.rows()


def dropper_hd_frames():
    return ([dropper_hd("cling")] + [dropper_hd("tell", k) for k in range(4)]
            + [dropper_hd("fall", k) for k in range(2)]
            + [dropper_hd("walk", k) for k in range(6)])


# ================================================================= flyer
# THE CANOPY WASP, 32x24, the 14x7 box at (9, 10). The body holds its line;
# only the wings move.
FLYER = dict(e40.FLYER)
FLYER.update({
    'v': ("metal", 2),           # wing veins
    'a': ("metal", 4),           # wing membrane, the clear outer half
    'Y': ("gold", 6),            # gloss on the abdomen
    'h': ("gold", 3),            # fuzz on the thorax
    'R': ("ember", 3),           # eye facets
    'W': ("metal", 6),           # catch-light
    'j': ("gold", 4),            # leg joints
})


def flyer_hd(i, n=6):
    c = HCanvas(32, 24)
    ph = 2 * math.pi * i / n
    ang = -70.0 + 95.0 * (0.5 - 0.5 * math.cos(ph))
    root = (18.6, 11.6)

    def wing(a, ln, wd, ch):
        tip = (root[0] + math.cos(math.radians(a + 180)) * ln * 0.9,
               root[1] + math.sin(math.radians(a + 180)) * ln * 0.9)
        mid = ((root[0] + tip[0]) / 2, (root[1] + tip[1]) / 2)
        c.ellipse(mid, ln * 0.5, wd, ch, ang=a)
        # the outer half is clearer membrane
        c.ellipse(((mid[0] + tip[0]) / 2, (mid[1] + tip[1]) / 2), ln * 0.26, wd * 0.62, 'a',
                  ang=a, only=ch)
        # veins: the leading edge, a radius and two cross veins
        c.capsule(root, tip, 0.42, 'W')
        r2 = math.radians(a + 180)
        ux, uy = math.cos(r2), math.sin(r2)
        nx, ny = -uy, ux
        p1 = (root[0] + ux * ln * 0.55 + nx * wd * 0.55, root[1] + uy * ln * 0.55 + ny * wd * 0.55)
        p2 = (root[0] + ux * ln * 0.8 + nx * wd * 0.35, root[1] + uy * ln * 0.8 + ny * wd * 0.35)
        c.stroke([root, p1, p2], 'v', only=ch + 'a')
        for f in (0.35, 0.62):
            q = (root[0] + ux * ln * f, root[1] + uy * ln * f)
            c.stroke([q, (q[0] + nx * wd * 0.9, q[1] + ny * wd * 0.9)], 'v', only=ch + 'a')

    wing(-ang * 0.15 + 150, 8.6, 2.0, 'A')
    for k in range(3):                                             # jointed legs
        pts = [(17.0 + k * 1.6, 14.0), (16.4 + k * 1.8, 16.6), (15.6 + k * 2.0, 18.4)]
        c.path(pts, 0.4, 'l', 0.3)
        c.dot(pts[1][0] - 0.2, pts[1][1] - 0.3, 'j', only='l')
        c.stroke([pts[2], (pts[2][0] - 0.6, pts[2][1] + 0.4)], 'l')
    # abdomen: lit bands with dark bands between, the curve of each band
    # following the body, a gloss along the top, and a sting
    c.ellipse((11.6, 13.6), 6.0, 3.6, 'y', ang=8.0)
    for bxp in (8.2, 11.0, 13.8):
        c.path([(bxp + 0.3, 10.0), (bxp - 0.4, 13.6), (bxp - 0.8, 17.2)], 0.62, 'o', only='y')
        c.stroke([(bxp + 0.9, 10.4), (bxp + 0.4, 13.6), (bxp + 0.0, 16.8)], 't', only='y')
    c.path([(8.4, 11.2), (11.4, 10.4), (14.4, 10.8)], 0.32, 'Y', only='yt')
    c.poly([(6.2, 13.2), (3.0, 16.4), (6.8, 15.2)], 'w')
    c.stroke([(6.0, 14.6), (4.0, 16.0)], 'A', only='w')
    c.capsule((14.6, 13.0), (16.8, 12.6), 0.9, 'k')
    # thorax: fuzzy, a scatter of darker hairs
    c.ellipse((18.8, 12.4), 2.8, 2.6, 't')
    c.scatter(14, (16.2, 10.0, 21.4, 15.0), 'h', 't', 51)
    c.ellipse((23.0, 12.8), 2.4, 2.3, 'o')
    # the compound eye: ember with a facet hatch and a catch-light
    c.ellipse((23.8, 12.0), 1.4, 1.6, 'r')
    for yy in range(4):
        for xx in range(3):
            if (xx + yy) % 2:
                c.dot(23.0 + xx * 0.55, 10.9 + yy * 0.55, 'R', only='r')
    c.dot(23.2, 11.0, 'W')
    c.capsule((25.0, 14.2), (26.2, 15.0), 0.5, 'o', 0.3)
    c.path([(23.4, 10.6), (25.0, 8.2), (27.6, 7.4)], 0.4, 'l', 0.3)        # antenna
    for f in (0.3, 0.55, 0.8):
        c.dot(lerp(25.0, 27.6, f), lerp(8.2, 7.4, f) - 0.2, 'j', only='l')
    wing(ang + 180, 10.4, 2.3, 'A')
    c.outline()
    return c.rows()


# ================================================================== sheets
def render(rows, mapping, rate=0.0):
    """Light and hand-AA one HD cell. Selout runs on the packed sheet."""
    img = kaya40.shade_hd(rows, mapping, rate=rate)
    kaya40._hand_aa(img)
    return img


def walker_cells():
    return [render(walker_hd(i), WALKER) for i in range(6)]


def jumper_cells():
    # 0 idle  1-2 the crouch (TELL)  3 air  4 land  5 air kick  6 recover
    return [render(jumper_hd(p), JUMPER)
            for p in (e40.J_IDLE, e40.J_CROUCH, e40.J_COIL, e40.J_AIR, e40.J_LAND,
                      e40.J_AIR2, e40.J_RECOVER)]


def shooter_cells():
    # 0 idle  1-3 the bloom opening (TELL)  4 spit  5-6 idle sway
    return [render(shooter_hd(p), SHOOTER)
            for p in (e40.S_IDLE, e40.S_STIR, e40.S_INHALE, e40.S_SWELL, e40.S_FIRE,
                      e40.S_SWAY_A, e40.S_SWAY_B)]


def swimmer_cells():
    return [render(swimmer_hd(i), SWIMMER) for i in range(6)]


def charger_cells():
    return [render(r, CHARGER) for r in charger_hd_frames()]


def dropper_cells():
    return [render(r, DROPPER) for r in dropper_hd_frames()]


def flyer_cells():
    return [render(flyer_hd(i), FLYER) for i in range(6)]


#: sheet name -> (builder, cell w, cell h) in WORLD units; the same cells and
#: frame orders as enemies40.SHEETS, which data/enemies/*.json index.
SHEETS = {
    "enemy_walker": (walker_cells, 32, 24),
    "enemy_jumper": (jumper_cells, 32, 32),
    "enemy_shooter": (shooter_cells, 32, 32),
    "enemy_swimmer": (swimmer_cells, 32, 24),
    "enemy_charger": (charger_cells, 32, 24),
    "enemy_dropper": (dropper_cells, 32, 32),
    "enemy_flyer": (flyer_cells, 32, 24),
}


def build_sheet(name):
    """Write one enemy sheet. Native at S when the sheet is in
    palette.HD_NATIVE (tools/art/hd_native/hdenemies.txt), else the 1x
    enemies40 sheet that publish_hd upscales. Returns the frame count."""
    if name not in palette.HD_NATIVE:
        return e40.build_sheet(name)
    fn, w, h = SHEETS[name]
    cells = fn()
    palette.sheet(name, cells, w * S, h * S, selout=True)
    return len(cells)
