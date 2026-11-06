"""The enemies and the five bosses at Kaya's level of detail (refit phase 3).

The 40 px Kaya (tools/art/kaya40.py) made the 16 px enemies look pasted in
from an older game. This module redraws all seven and the five bosses the way
she is drawn: posed parts -- ellipses, tapered capsules, polygons -- placed
by a handful of numbers per frame, rasterised into the shared character-grid
format, lit by `palette.auto_shade` and inked by the sheet's selective
outline. A pose is data; a new frame is a dict, not a new drawing.

Two rules this module exists to keep, and they matter more than beauty:

**Collision never changes.** Every hitbox in data/enemies/*.json is exactly
what it was. The bigger frame is anchored on the unchanged box by a separate
`render` block (`ox`/`oy`: where the box sits inside the frame), which
src/enemies/enemy_base.gd reads in place of the hitbox's own anchor. The
*body mass* of every animal is drawn inside its box, give or take a few
pixels; only thin parts that a player would not aim a blade at -- antennae,
tusks, petals, fins, crests, wing tips, a lure -- reach past it. A hurtbox
bigger than the animal, or an animal much bigger than its hurtbox, is the
unfairness the Grove Warden's docstring (tools/art/sprites.py) records.

**Telegraphs get clearer, never buried.** Each tell is named on the builder
that draws it and is drawn as a change of *silhouette* first and of value
second, so it reads at 1x across a screen:

  charger   the bristle crest stands up in three escalating beats, the head
            drops, a forehoof paws the dirt and the eye goes red
  jumper    the hind knees fold up above the body and the back spines rise
  shooter   the petals flare open and the throat lights up
  dropper   legs let go of the ceiling one by one and the eyes go red
  bosses    each boss's existing tell (see the builders) carried to 64 px

Every sheet faces right, as `Enemy._update_anim()` assumes (`flip_h` when
`facing < 0`). `SHEETS` is the contract with data/enemies/*.json: cell size,
render anchor and the frame order each JSON's `anim` block indexes.
"""

import math

from . import palette


# ====================================================================== canvas
class Canvas:
    """A character grid with the primitives the puppets are built from."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.g = [['.'] * w for _ in range(h)]

    def set(self, x, y, ch):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.g[y][x] = ch

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.g[y][x]
        return '.'

    def px(self, x, y, ch):
        self.set(int(math.floor(x)), int(math.floor(y)), ch)

    def capsule(self, a, b, r0, ch, r1=None, only=None):
        """Every pixel whose centre lies within the (tapering) radius of the
        segment a-b. `only`, if given, limits painting to cells already holding
        one of those characters (a stripe painted onto a body)."""
        r1 = r0 if r1 is None else r1
        ax, ay = a
        bx, by = b
        dx, dy = bx - ax, by - ay
        l2 = dx * dx + dy * dy or 1e-9
        rr = max(r0, r1)
        for y in range(int(min(ay, by) - rr - 1), int(max(ay, by) + rr + 2)):
            for x in range(int(min(ax, bx) - rr - 1), int(max(ax, bx) + rr + 2)):
                px, py = x + 0.5, y + 0.5
                t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
                qx, qy = ax + t * dx, ay + t * dy
                r = r0 + (r1 - r0) * t
                if (px - qx) ** 2 + (py - qy) ** 2 <= r * r:
                    if only is None or self.get(x, y) in only:
                        self.set(x, y, ch)

    def path(self, pts, r0, ch, r1=None, only=None):
        """A tapered stroke through several points."""
        r1 = r0 if r1 is None else r1
        n = len(pts) - 1
        for i in range(n):
            ra = r0 + (r1 - r0) * i / n
            rb = r0 + (r1 - r0) * (i + 1) / n
            self.capsule(pts[i], pts[i + 1], ra, ch, rb, only=only)

    def ellipse(self, c, rx, ry, ch, ang=0.0, clip=None, only=None):
        """Filled ellipse, optionally rotated by `ang` degrees (clockwise, y
        down) and clipped by `clip(x, y) -> bool` on pixel centres."""
        cx, cy = c
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        rr = max(rx, ry)
        for y in range(int(cy - rr - 1), int(cy + rr + 2)):
            for x in range(int(cx - rr - 1), int(cx + rr + 2)):
                px, py = x + 0.5 - cx, y + 0.5 - cy
                u = px * ca + py * sa
                v = -px * sa + py * ca
                if (u / rx) ** 2 + (v / ry) ** 2 <= 1.0:
                    if clip is None or clip(x + 0.5, y + 0.5):
                        if only is None or self.get(x, y) in only:
                            self.set(x, y, ch)

    def poly(self, pts, ch, only=None):
        """Filled polygon (even-odd rule on pixel centres)."""
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        for y in range(int(min(ys)) - 1, int(max(ys)) + 2):
            for x in range(int(min(xs)) - 1, int(max(xs)) + 2):
                px, py = x + 0.5, y + 0.5
                inside = False
                j = len(pts) - 1
                for i in range(len(pts)):
                    xi, yi = pts[i]
                    xj, yj = pts[j]
                    if (yi > py) != (yj > py):
                        if px < (xj - xi) * (py - yi) / (yj - yi) + xi:
                            inside = not inside
                    j = i
                if inside and (only is None or self.get(x, y) in only):
                    self.set(x, y, ch)

    def spike(self, base, ang, length, width, ch):
        """A thorn: a triangle from a base point, `ang` degrees from straight
        up (positive leans toward +x)."""
        bx, by = base
        ux, uy = math.sin(math.radians(ang)), -math.cos(math.radians(ang))
        nx, ny = -uy, ux
        self.poly([(bx - nx * width, by - ny * width),
                   (bx + ux * length, by + uy * length),
                   (bx + nx * width, by + ny * width)], ch)

    def outline(self, ink='k'):
        """One pixel of ink around the whole silhouette (4-connected), the pass
        every sprite in tools/art ends on; selout softens it later."""
        out = [row[:] for row in self.g]
        for y in range(self.h):
            for x in range(self.w):
                if self.g[y][x] != '.':
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.w and 0 <= ny < self.h and \
                            self.g[ny][nx] not in '.' + ink:
                        out[y][x] = ink
                        break
        self.g = out

    def rows(self):
        return ["".join(r) for r in self.g]


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_pose(a, b, t):
    """Interpolate two pose dicts key by key (numbers only; the rest from a)."""
    out = dict(a)
    for k, v in b.items():
        if isinstance(v, (int, float)) and isinstance(a.get(k), (int, float)):
            out[k] = lerp(a[k], v, t)
    return out


def limb(c, root, foot, l1, l2, r0, r1, ch, bend=1):
    """Two-bone IK, the same solve as Kaya's leg: the knee bends toward
    `bend` (+1 forward / -1 back of the line root->foot)."""
    dx, dy = foot[0] - root[0], foot[1] - root[1]
    reach = math.hypot(dx, dy)
    if reach >= l1 + l2 - 0.05:
        k = (root[0] + dx * l1 / (l1 + l2), root[1] + dy * l1 / (l1 + l2))
    else:
        a = math.atan2(dy, dx)
        cos_k = (l1 * l1 + reach * reach - l2 * l2) / (2 * l1 * max(reach, 1e-6))
        ka = a - (1 if bend >= 0 else -1) * math.acos(max(-1.0, min(1.0, cos_k)))
        k = (root[0] + math.cos(ka) * l1, root[1] + math.sin(ka) * l1)
    c.capsule(root, k, r0, ch, (r0 + r1) * 0.5)
    c.capsule(k, foot, (r0 + r1) * 0.5, ch, r1)
    return k


def polar(c, r, ang):
    """`ang` degrees from straight up, clockwise."""
    return (c[0] + math.sin(math.radians(ang)) * r,
            c[1] - math.cos(math.radians(ang)) * r)


# ================================================================ the seven
# ---------------------------------------------------------------- walker
# THE BARK BEETLE (data/enemies/walker.json). Purple, as it always was --
# the seven enemies are kept apart by colour and this is the purple one.
# 32x24, the 14x11 box at (9, 13): the shell sits on it, the head and the
# antennae lead out of it. Six legs walk an alternating tripod.
WALKER = {
    'p': ("purple", 3), 'P': ("purple", 2),    # elytra / far side
    'L': ("purple", 5),                          # the shine on the elytra
    'h': ("purple", 2),                          # head and pronotum
    'q': ("purple", 4), 'Q': ("purple", 2),    # near / far legs
    'r': ("ember", 4),                           # eyes
    'm': ("gold", 3),                            # mandibles
    'd': ("purple", 4),                          # shell punctures, lit
}


def walker(i, n=6):
    c = Canvas(32, 24)
    fy = 23.6                              # the floor, just under row 23
    ph = 2 * math.pi * i / n
    bob = 0.5 * abs(math.sin(ph))
    sy = 13.8 - bob

    def leg(hip, base_x, phase, ch, reach=1.0):
        s = math.sin(ph + phase)
        fx = base_x + 2.2 * math.cos(ph + phase)
        lift = max(0.0, s) * 2.2
        limb(c, hip, (fx, fy - 0.4 - lift), 4.4 * reach, 4.8 * reach, 0.8, 0.6, ch,
             bend=-1 if fx < hip[0] else 1)

    # far legs first (one tripod's phase), then body, then near legs
    for hx, bx, p in ((12.5, 9.5, 0.0), (16.0, 16.0, math.pi), (19.0, 22.5, 0.0)):
        leg((hx, sy + 3.0), bx, p + 0.3, 'Q')
    # antennae: elbowed, swaying with the gait
    sway = math.sin(ph) * 0.6
    for off, ch in ((0.0, 'Q'), (1.2, 'q')):
        e1 = (27.6 + off * 0.4, 11.2 - off * 0.3 + sway * 0.5)
        c.path([(24.6 + off * 0.3, sy - 0.4), e1, (30.4 + off * 0.3, 9.4 + sway - off * 0.6)],
               0.5, ch)
    # elytra: a dome with a flat belly, the seam and two rows of punctures
    c.ellipse((14.6, sy), 9.0, 6.3, 'p', clip=lambda x, y: y < sy + 4.6)
    c.ellipse((14.6, sy + 3.4), 8.4, 2.0, 'P')                    # belly shadow
    c.path([(9.0, sy - 3.8), (13.0, sy - 5.0), (17.0, sy - 4.8)], 0.7, 'L', only='p')
    c.path([(21.0, sy - 5.4), (15.0, sy - 5.9), (8.0, sy - 3.2), (5.9, sy + 1.0)],
           0.5, 'k', only='pP')                                  # seam
    for k in range(4):
        c.px(9.0 + k * 3.0, sy - 2.6 + (k % 2) * 0.4, 'd')
        c.px(10.4 + k * 3.0, sy + 0.4, 'd')
    # pronotum and head, split from the shell by an ink arc
    c.ellipse((22.4, sy + 0.4), 3.6, 3.9, 'h')
    c.path([(20.4, sy - 3.3), (19.4, sy + 0.2), (20.1, sy + 3.4)], 0.5, 'k')
    c.ellipse((25.6, sy + 2.0), 2.4, 2.3, 'h')
    c.px(26.2, sy + 0.9, 'r')
    c.px(25.2, sy + 0.9, 'r')                                     # eye
    jaw = 0.6 * math.sin(ph * 2)
    c.capsule((26.6, sy + 3.5), (28.6, sy + 3.2 - jaw), 0.55, 'm')
    c.capsule((26.4, sy + 3.9), (28.4, sy + 4.6 + jaw), 0.5, 'm')
    for hx, bx, p in ((11.0, 8.0, math.pi), (15.5, 16.5, 0.0), (19.5, 25.0, math.pi)):
        leg((hx, sy + 3.6), bx, p, 'q')
    c.outline()
    return c.rows()


# ---------------------------------------------------------------- jumper
# THE EMBER HOPPER (data/enemies/jumper.json). A spiny red flea-toad with
# grasshopper hind legs. 32x32, the 12x11 box at (10, 21).
#
# TELL -- the crouch. Frames 1 and 2 are the wind-up ("windup": [0, 1, 2]):
# the body sinks, and the hind knees fold *up past the top of the body*, the
# back spines stand up and go gold. The knees are the read: a sitting hopper
# has none above its back, a coiled one has two, and that silhouette change is
# big enough to read across a screen at 1x.
JUMPER = {
    'r': ("ember", 3), 'R': ("ember", 2),      # hide / far legs, belly
    'u': ("ember", 5),                           # lit back, near leg
    'y': ("gold", 5), 'o': ("gold", 4),        # spines: raised / resting
    'w': ("metal", 6),                           # eyes, fang
    'm': ("ember", 1),                           # mouth
}

J_IDLE = dict(by=25.4, rx=6.6, ry=5.0, knee=(10.6, 21.8), foot=(6.8, 31.0),
              spine=2.2, spine_ch='o', lid=0.0, kick=0.0, dust=0, front=1.0)
J_CROUCH = dict(J_IDLE, by=27.0, rx=7.0, ry=4.4, knee=(10.0, 19.6), foot=(6.0, 31.0),
                spine=3.4, spine_ch='y', lid=0.6)
J_COIL = dict(J_IDLE, by=28.2, rx=7.6, ry=3.7, knee=(9.6, 17.4), foot=(5.2, 31.0),
              spine=4.8, spine_ch='y', lid=1.0, dust=2)
J_AIR = dict(J_IDLE, by=22.4, rx=5.6, ry=5.6, knee=(10.0, 27.0), foot=(4.6, 31.0),
             spine=2.6, spine_ch='o', front=-1.0)
J_AIR2 = dict(J_AIR, knee=(9.0, 27.6), foot=(5.8, 30.6), spine=3.0, by=22.0)
J_LAND = dict(J_IDLE, by=28.4, rx=7.8, ry=3.6, knee=(9.0, 23.4), foot=(4.6, 31.0),
              spine=1.6, dust=3)
J_RECOVER = dict(J_IDLE, by=26.2, rx=7.0, ry=4.6, knee=(10.2, 21.0), foot=(6.4, 31.0))


def jumper(p):
    c = Canvas(32, 32)
    by, rx, ry = p["by"], p["rx"], p["ry"]
    bx = 16.0
    hip = (bx - 2.2, by + 0.8)
    # far hind leg, a step behind and dark
    k = (p["knee"][0] + 1.4, p["knee"][1] + 0.8)
    c.capsule((hip[0] + 1.0, hip[1]), k, 1.5, 'R', 1.1)
    c.capsule(k, (p["foot"][0] + 1.8, p["foot"][1]), 0.9, 'R', 0.6)
    # far front leg
    c.capsule((bx + 3.0, by + 2.0), (bx + 4.2 + p["front"], 31.0), 0.7, 'R')
    # spines along the back: a comb leaning back, the tell's second half
    for j, t in enumerate((-0.75, -0.4, -0.05, 0.3)):
        ang = math.degrees(t * 1.2)
        base = (bx + math.sin(t * 1.25) * rx * 0.9, by - math.cos(t * 1.25) * ry * 0.85)
        c.spike(base, ang - 22, p["spine"] + (0.6 if j in (1, 2) else 0.0), 1.1,
                p["spine_ch"])
    # the body
    c.ellipse((bx, by), rx, ry, 'r')
    c.ellipse((bx + 0.4, by + ry * 0.55), rx * 0.8, ry * 0.4, 'R')   # belly
    c.ellipse((bx - 1.0, by - ry * 0.45), rx * 0.55, ry * 0.35, 'u')  # lit back
    # eyes: two bulbs on top at the front, lidded as it coils
    for ex in (bx + 1.8, bx + 5.2):
        e = (ex, by - ry + 0.9)
        c.ellipse(e, 1.3, 1.4, 'w')
        c.px(e[0] + 0.3, e[1] + 0.1, 'k')
        if p["lid"] >= 0.5:
            c.px(e[0] - 1.0, e[1] - 1.0, 'r')
            c.px(e[0], e[1] - 1.0, 'r')
            c.px(e[0] + 0.9, e[1] - 1.0, 'r')
    # mouth: a wide grin with one fang
    my = by + 1.0
    c.capsule((bx + 2.0, my), (bx + rx - 0.4, my - 0.6), 0.5, 'm')
    c.px(bx + rx - 1.4, my + 0.4, 'w')
    # near front leg
    c.capsule((bx + 2.0, by + 2.4), (bx + 3.0 + p["front"], 31.0), 0.8, 'u')
    # near hind leg, the big one: thigh, the folded shin, a long foot
    c.capsule(hip, p["knee"], 2.8, 'u', 1.6)
    c.capsule(p["knee"], p["foot"], 1.0, 'r', 0.7)
    c.capsule(p["foot"], (p["foot"][0] - 2.0, p["foot"][1]), 0.6, 'r')
    for d in range(p["dust"]):
        c.px(4.0 + d * 2.6, 30.6 - (d % 2), 'o')
        c.px(26.5 - d * 2.2, 30.6 - ((d + 1) % 2), 'o')
    c.outline()
    return c.rows()


# ---------------------------------------------------------------- shooter
# THE SPITTING BLOOM (data/enemies/shooter.json). A purple flower on a green
# stem. 32x32, the 12x14 box at (10, 18): the head is in the box.
#
# TELL -- the bloom opens. "windup": [1, 2, 3] flare the petals out in three
# steps while the face swells and the throat lights from ink through ember to
# gold, so the last beat before the spit is the brightest thing on the plant.
SHOOTER = {
    'p': ("purple", 3), 'P': ("purple", 2),    # petals, lit / back row
    'w': ("metal", 5),                           # the face ring
    'y': ("gold", 5), 'Y': ("gold", 6),        # seed disc / throat at full
    'r': ("ember", 4),                           # throat, warming
    'm': ("ember", 0),                           # the mouth's dark
    'l': ("grass", 4), 'G': ("grass", 2),      # leaves / stem
    'g': ("foliage", 2),                         # roots
}

S_IDLE = dict(hx=16.6, hy=21.6, pr=4.2, plen=3.0, pw=1.9, face=2.8, mouth=0.0,
              throat='m', lean=0.0, leaf=0.0, spit=0)
S_SWAY_A = dict(S_IDLE, hx=16.0, hy=21.8, lean=-0.6, leaf=0.6)
S_SWAY_B = dict(S_IDLE, hx=17.2, hy=21.4, lean=0.6, leaf=-0.6)
S_STIR = dict(S_IDLE, hx=16.2, hy=21.0, pr=5.0, plen=3.6, pw=2.1, face=3.2, mouth=1.0,
              throat='m', lean=-0.8, leaf=0.6)
S_INHALE = dict(S_IDLE, hx=15.8, hy=20.6, pr=5.8, plen=4.4, pw=2.2, face=3.6, mouth=1.8,
                throat='r', lean=-1.4, leaf=1.0)
S_SWELL = dict(S_IDLE, hx=15.6, hy=20.4, pr=6.4, plen=5.4, pw=2.4, face=4.0, mouth=2.6,
               throat='Y', lean=-1.8, leaf=1.2)
S_FIRE = dict(S_IDLE, hx=18.0, hy=21.2, pr=6.0, plen=4.6, pw=2.0, face=3.8, mouth=3.0,
              throat='r', lean=1.6, leaf=-0.8, spit=1)


def shooter(p):
    c = Canvas(32, 32)
    hx, hy = p["hx"], p["hy"]
    # roots and the two big leaves
    c.ellipse((16.0, 31.0), 4.6, 1.4, 'g')
    for side in (-1, 1):
        tip = (16.0 + side * 8.6, 26.4 + p["leaf"] * side)
        mid = (16.0 + side * 4.6, 25.6 + p["leaf"] * side * 0.5)
        c.path([(16.0, 30.0), mid, tip], 1.7, 'l', 0.5)
        c.path([(16.0 + side * 1.0, 29.6), (mid[0], mid[1] + 0.6), tip], 0.45, 'G',
               only='l')                                         # midrib
    # stem: a curve from the root up under the head
    c.path([(16.0, 31.0), (16.0 - p["lean"] * 0.4, 28.0), (hx - p["lean"] * 0.3, hy + 3.0)],
           1.2, 'G', 1.0)
    # back row of petals, then the front row, both rotated with the lean
    # Each petal gets an ink edge of its own before the next is laid over it,
    # or eight overlapping ellipses in one material merge into a disc.
    n = 6
    for ch, r_mul, off in (('P', 1.1, 30.0), ('p', 1.0, 0.0)):
        for k in range(n):
            ang = k * 360.0 / n + off + p["lean"] * 6.0
            r = p["pr"] * r_mul
            ctr = polar((hx, hy), r * 0.45 + p["plen"] * 0.55, ang)
            c.ellipse(ctr, p["plen"] + 0.6, p["pw"] + 0.6, 'k', ang=ang - 90.0)
            c.ellipse(ctr, p["plen"], p["pw"], ch, ang=ang - 90.0)
    # the face: a white ring, the seed disc, and the mouth opening inside it
    fx = hx + 0.8                                                # three-quarter: it looks forward
    c.ellipse((fx, hy), p["face"], p["face"] * 0.95, 'w')
    c.ellipse((fx, hy), p["face"] - 0.9, (p["face"] - 0.9) * 0.95, 'y')
    if p["mouth"] > 0.0:
        c.ellipse((fx + 0.4, hy + 0.2), p["mouth"], p["mouth"] * 0.9, 'm')
        if p["throat"] != 'm':
            c.ellipse((fx + 0.4, hy + 0.3), p["mouth"] * 0.7, p["mouth"] * 0.65, 'r')
            c.ellipse((fx + 0.4, hy + 0.3), p["mouth"] * 0.4, p["mouth"] * 0.4,
                      p["throat"])
    else:
        c.capsule((fx - 0.8, hy + 0.6), (fx + 1.6, hy + 0.6), 0.5, 'm')   # shut
    if p["spit"]:
        c.ellipse((fx + p["mouth"] + 2.4, hy), 1.3, 1.1, 'p')
        c.px(fx + p["mouth"] + 4.6, hy - 1.0, 'p')
    c.outline()
    return c.rows()


# ---------------------------------------------------------------- swimmer
# THE RIVER PIRANHA (data/enemies/swimmer.json). Cyan back, a red belly, a
# jaw full of teeth. 32x24, the 14x9 box at (9, 8): the deep body is on the
# box, the tail and the fins are not.
SWIMMER = {
    'c': ("water", 5), 'C': ("water", 3),      # back / fins
    'b': ("water", 6),                           # flank shine
    'r': ("ember", 4),                           # belly
    'w': ("metal", 6),                           # teeth
    'y': ("gold", 5),                            # eye
    'm': ("ember", 1),                           # mouth
}


def swimmer(i, n=6):
    c = Canvas(32, 24)
    ph = 2 * math.pi * i / n
    tail = math.sin(ph) * 3.2
    bend = math.sin(ph - 0.9) * 0.8
    gape = max(0.0, math.sin(ph * 1.0 + 0.6)) * 1.6
    cx, cy = 16.6, 12.4 + bend * 0.3
    # tail fin: a fork behind the peduncle, swinging
    root = (cx - 8.8, cy + bend * 0.5)
    c.poly([root, (root[0] - 5.6, cy - 4.6 + tail), (root[0] - 3.6, cy + tail * 0.5),
            (root[0] - 5.6, cy + 4.6 + tail)], 'C')
    # dorsal and anal fins
    c.poly([(cx - 3.0, cy - 5.2), (cx - 5.6, cy - 8.4 + bend), (cx + 1.6, cy - 5.6)], 'C')
    c.poly([(cx - 3.6, cy + 5.0), (cx - 6.0, cy + 7.4 - bend), (cx - 0.4, cy + 5.4)], 'C')
    # the body: a deep oval, blunt at the head
    c.ellipse((cx, cy), 9.2, 5.8, 'c', clip=lambda x, y: x < cx + 6.6 or y > cy - 4.0)
    c.ellipse((cx + 4.0, cy + 0.6), 5.6, 5.0, 'c')
    c.ellipse((cx - 0.6, cy + 3.0), 7.2, 2.6, 'r', clip=lambda x, y: y > cy + 1.0)
    c.capsule((cx - 6.0, cy - 2.0), (cx + 3.0, cy - 3.2), 0.6, 'b')     # shine
    # gill line
    c.path([(cx + 3.2, cy - 3.4), (cx + 2.4, cy), (cx + 3.0, cy + 3.4)], 0.45, 'k')
    # mouth: an underslung jaw with a row of teeth each side of the gap
    jx, jy = cx + 9.2, cy + 2.0
    c.poly([(jx - 3.6, jy - 0.8), (jx + 0.4, jy - 1.4 - gape * 0.4),
            (jx + 0.6, jy + 1.0 + gape), (jx - 3.0, jy + 1.2)], 'm')
    for t in range(3):
        c.px(jx - 2.4 + t * 1.2, jy - 0.9 - gape * 0.2, 'w')
        c.px(jx - 2.0 + t * 1.2, jy + 0.6 + gape * 0.8, 'w')
    # pectoral fin, beating
    c.ellipse((cx + 1.0, cy + 1.4), 2.4, 1.0, 'C', ang=20 + math.sin(ph + 1.0) * 25)
    # the eye
    c.ellipse((cx + 5.8, cy - 1.6), 1.4, 1.4, 'y')
    c.px(cx + 6.2, cy - 1.6, 'k')
    c.outline()
    return c.rows()


# ---------------------------------------------------------------- charger
# THE THORN BOAR (data/enemies/charger.json). Brown hide, an ember bristle
# crest, white tusks. 32x24, the 14x11 box at (9, 13).
#
# TELL -- the wind-up, three escalating beats that "loop": false holds on the
# last: the head drops, a forehoof paws back, and the crest -- flat while it
# patrols -- stands up to more than twice its height and goes from ember to
# gold. The eye goes red on the last beat. Nothing in the patrol or the charge
# has a crest that tall, so the outline alone says "it is about to run".
CHARGER = {
    'm': ("dirt", 2), 'M': ("dirt", 4),        # hide / lit hide, snout
    'n': ("dirt", 1),                            # far legs, belly
    'h': ("dirt", 0),                            # hooves
    'r': ("ember", 3), 'y': ("gold", 5),       # crest: resting / raised
    'w': ("metal", 6),                           # tusks
    'e': ("gold", 5), 'E': ("ember", 5),       # eye: calm / about to go
    's': ("metal", 5),                           # dust, steam
}

C_BASE = dict(dy=0.0, head=0.0, crest=1.8, crest_ang=-58.0, crest_ch='r', eye='e',
              lift=0.0, paw=0.0, gait=None, stride=1.0, dust=0, stars=-1, sway=0.0)


def charger(p):
    p = dict(C_BASE, **p)
    c = Canvas(32, 24)
    fy = 23.4
    dy, hd = p["dy"], p["head"]
    bx, by = 14.4, 13.6 + dy
    g = p["gait"]

    def foot(base_x, phase, amp):
        if g is None:
            return base_x, 0.0
        return (base_x + amp * math.cos(g + phase),
                max(0.0, math.sin(g + phase)) * 2.0 * p["stride"])

    # far legs
    for hx, ph in ((9.0, math.pi), (19.0, 0.0)):
        fx, lift = foot(hx - 0.4, ph, 2.0 * p["stride"])
        c.capsule((hx, by + 2.0), (fx, fy - 0.6 - lift), 1.2, 'n', 0.9)
        c.px(fx, fy - 0.4 - lift, 'h')
    # crest: a row of bristles along the spine, flat or raised
    for k in range(7):
        t = k / 6.0
        base = (8.0 + t * 12.0, by - 5.4 + math.sin(t * math.pi) * -0.8)
        ln = p["crest"] * (0.7 + 0.5 * math.sin(t * math.pi))
        c.spike(base, p["crest_ang"] + (k % 2) * 6.0, ln, 0.9, p["crest_ch"])
    # tail
    c.path([(5.6, by - 1.4), (3.8, by - 2.6), (4.2, by - 0.4)], 0.55, 'm')
    # barrel and shoulder hump
    c.ellipse((bx, by), 9.2, 5.0, 'm')
    c.ellipse((bx + 4.6, by - 1.0), 5.0, 4.8, 'm')
    c.ellipse((bx - 0.6, by + 3.2), 7.0, 1.8, 'n')                 # belly shadow
    c.ellipse((bx + 3.0, by - 3.0), 4.0, 1.6, 'M')                 # lit shoulder
    # head: a wedge dropping to the snout; `head` drops it further
    hx0, hy0 = bx + 7.0, by - 1.4
    sx, sy = hx0 + 6.4, by + 3.0 + hd
    c.poly([(hx0 - 1.0, hy0 - 3.0), (hx0 + 2.6, hy0 - 2.4 + hd * 0.4), (sx + 0.4, sy - 1.6),
            (sx + 0.8, sy + 1.4), (hx0 + 1.6, sy + 1.8), (hx0 - 1.6, hy0 + 3.4)], 'm')
    c.ellipse((sx + 0.6, sy), 1.4, 1.7, 'M')                       # snout disc
    c.px(sx + 1.2, sy - 0.2, 'h')                                  # nostril
    # ear
    c.poly([(hx0 - 0.4, hy0 - 2.6), (hx0 - 2.4, hy0 - 6.4 + hd * 0.3), (hx0 + 1.6, hy0 - 2.8)],
           'M')
    # eye
    c.px(hx0 + 2.4, hy0 - 0.4 + hd * 0.5, p["eye"])
    c.px(hx0 + 1.4, hy0 - 0.4 + hd * 0.5, 'k')
    # tusk: curving up from the lower jaw past the snout
    c.path([(sx - 1.6, sy + 1.6), (sx + 0.6, sy + 2.0), (sx + 2.2, sy - 0.2)], 0.55, 'w')
    # near legs; a pawing forehoof lifts and drags back
    for hx, ph, near_front in ((10.4, 0.0, False), (20.0, math.pi, True)):
        fx, lift = foot(hx + 0.2, ph, 2.2 * p["stride"])
        if near_front and p["paw"] > 0.0:
            fx, lift = hx + 1.0 - p["paw"] * 2.6, p["lift"]
        c.capsule((hx, by + 1.6), (fx, fy - 0.8 - lift), 1.4, 'M', 1.0)
        c.capsule((fx, fy - 0.8 - lift), (fx + 0.6, fy - 0.3 - lift), 0.8, 'h')
    for d in range(p["dust"]):
        c.px(20.0 - d * 2.4, fy - 0.6 - (d % 2) * 1.2, 's')
    if p["dust"] >= 3:                                             # snorted steam
        c.px(sx + 3.0, sy - 1.6, 's')
        c.px(sx + 4.2, sy - 2.6, 's')
    if p["stars"] >= 0:                                            # dazed
        for k in range(3):
            a = p["stars"] + k * 2 * math.pi / 3
            c.px(hx0 + 1.0 + math.cos(a) * 3.6, hy0 - 4.4 + math.sin(a) * 1.0, 'y')
    c.outline()
    return c.rows()


def charger_frames():
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
    return [charger(p) for p in walk + wind + run + daze]


# ---------------------------------------------------------------- dropper
# THE HOLLOW TICK (data/enemies/dropper.json). Stone grey, eight legs. 32x32,
# the 14x12 box at (9, 8): clinging, the box's top is the ceiling's
# underside (src/enemies/dropper.gd lifts it there), so the legs hook into
# the rows above it; walking, the box's bottom is the floor.
#
# TELL -- letting go. "tell" is four frames in which the legs come off the
# ceiling one pair at a time and flail, the body swings, and the eyes go from
# gold to red. A clinging tick has all eight tips in the rock; a tick about to
# fall has half its legs in the air below the ceiling line.
DROPPER = {
    'a': ("stone", 3), 'A': ("stone", 5),      # carapace / the lit scute
    'd': ("stone", 2),                           # plate seams, far legs
    'l': ("stone", 4),                           # near legs
    'y': ("gold", 5), 'r': ("ember", 5),       # eyes: patient / letting go
    'w': ("metal", 6),                           # mouthparts
}


def _tick_body(c, cx, cy, hang, eye, sw=0.0):
    """Hanging (`hang` 1) the body is a teardrop under its shoulders; standing
    (`hang` 0) it is a dome over its legs."""
    if hang:
        c.ellipse((cx, cy), 7.0, 5.4, 'a')
        c.poly([(cx - 6.4, cy + 1.6), (cx + sw * 0.6, cy + 11.0), (cx + 6.4, cy + 1.6)], 'a')
        c.ellipse((cx + sw * 0.3, cy + 6.4), 4.0, 3.6, 'a')
        c.ellipse((cx - 0.4, cy + 1.6), 2.6, 4.2, 'A')            # the lit scute
        c.path([(cx - 5.0, cy + 3.0), (cx, cy + 4.6), (cx + 5.0, cy + 3.0)], 0.45, 'd',
               only='aA')
        c.path([(cx - 3.4, cy + 7.6), (cx, cy + 8.6), (cx + 3.4, cy + 7.6)], 0.45, 'd',
               only='aA')
        c.capsule((cx + sw * 0.6, cy + 10.8), (cx + sw * 0.6, cy + 12.4), 0.7, 'w')
        for ex in (-2.6, 2.6):
            c.px(cx + ex, cy - 2.2, eye)
    else:
        c.ellipse((cx, cy), 7.4, 5.4, 'a', clip=lambda x, y: y < cy + 3.6)
        c.ellipse((cx - 0.8, cy - 1.4), 4.0, 2.2, 'A')
        c.path([(cx - 5.6, cy + 0.6), (cx, cy + 1.8), (cx + 5.6, cy + 0.6)], 0.45, 'd',
               only='aA')
        c.ellipse((cx + 6.0, cy + 2.4), 2.0, 1.6, 'a')            # capitulum
        c.capsule((cx + 7.4, cy + 2.8), (cx + 8.6, cy + 3.6), 0.6, 'w')
        c.px(cx + 5.6, cy + 1.6, eye)
        c.px(cx + 3.6, cy + 1.2, eye)


def dropper(state, k=0):
    c = Canvas(32, 32)
    ceil = 8.0
    if state in ("cling", "tell"):
        sw = 0.0
        loose = set()
        eye = 'y'
        drop = 0.0
        if state == "tell":
            sw = (-1.2, 1.2, -1.0, 1.4)[k]
            loose = ({0, 7}, {0, 7, 2}, {0, 7, 2, 5}, {0, 7, 2, 5, 3})[k]
            eye = 'r' if k >= 1 else 'y'
            drop = (0.0, 0.4, 0.8, 1.2)[k]
        cx, cy = 15.5 + sw, 12.6 + drop
        # eight legs: shoulders on the upper body, tips in the rock above
        for j in range(8):
            side = -1 if j < 4 else 1
            n = j if j < 4 else 7 - j
            sh = (cx + side * (2.0 + n * 1.2), cy - 2.0 + n * 0.8)
            ch = 'd' if n % 2 else 'l'
            if j in loose:
                tip = (sh[0] + side * (5.0 + n * 0.4), sh[1] + 3.0 + ((j + k) % 3) * 1.6)
                limb(c, sh, tip, 3.6, 3.8, 0.6, 0.45, ch, bend=-side)
            else:
                tip = (15.5 + side * (3.6 + n * 2.9), ceil - 0.6)
                limb(c, sh, tip, 4.2 + n * 0.7, 3.8 + n * 0.5, 0.7, 0.5, ch, bend=side)
        _tick_body(c, cx, cy, 1, eye, sw)
    elif state == "fall":
        cx, cy = 15.5, 13.0
        for j in range(8):
            side = -1 if j < 4 else 1
            n = j if j < 4 else 7 - j
            sh = (cx + side * (2.4 + n * 1.0), cy - 1.0 + n * 0.6)
            flail = math.sin(k * 2.4 + j) * 1.6
            tip = (sh[0] + side * (4.4 + n * 0.6), sh[1] - 4.0 + n * 1.2 + flail)
            limb(c, sh, tip, 3.4, 3.4, 0.6, 0.45, 'd' if n % 2 else 'l', bend=side)
        _tick_body(c, cx, cy, 1, 'r')
    else:                                                          # walk
        fy = 19.6
        ph = 2 * math.pi * k / 6
        cx, cy = 15.0, 11.6 + 0.4 * abs(math.sin(ph))
        for j in range(4):
            for near in (False, True):
                hx = cx - 4.5 + j * 3.0 + (0.6 if near else 0.0)
                phase = ph + j * math.pi * 0.5 + (math.pi if near else 0.0)
                fx = hx + (j - 1.5) * 1.6 + 1.6 * math.cos(phase)
                lift = max(0.0, math.sin(phase)) * 1.6
                limb(c, (hx, cy + 2.6), (fx, fy - 0.5 - lift), 3.6, 4.0, 0.75, 0.55,
                     'l' if near else 'd', bend=1 if j >= 2 else -1)
        _tick_body(c, cx, cy, 0, 'y')
    c.outline()
    return c.rows()


def dropper_frames():
    return ([dropper("cling")] + [dropper("tell", k) for k in range(4)]
            + [dropper("fall", k) for k in range(2)]
            + [dropper("walk", k) for k in range(6)])


# ---------------------------------------------------------------- flyer
# THE CANOPY WASP (data/enemies/flyer.json). Gold and ink bands, an ember
# eye, glassy wings. 32x24, the 14x7 box at (9, 10). The body holds its line
# through all six beats -- only the wings move -- because the path is the
# threat (src/enemies/flyer.gd), not a lunge.
FLYER = {
    'y': ("gold", 5), 'o': ("gold", 3),        # bands: lit / dark
    't': ("gold", 4),                            # thorax
    'r': ("ember", 5),                           # eye
    'A': ("metal", 3), 'W': ("metal", 5),      # wing membrane / leading edge
    'w': ("metal", 6),                           # sting
    'l': ("gold", 2),                            # legs
}


def flyer(i, n=6):
    c = Canvas(32, 24)
    ph = 2 * math.pi * i / n
    ang = -70.0 + 95.0 * (0.5 - 0.5 * math.cos(ph))               # up .. down
    root = (18.6, 11.6)

    def wing(a, ln, wd, ch):
        tip = (root[0] + math.cos(math.radians(a + 180)) * ln * 0.9,
               root[1] + math.sin(math.radians(a + 180)) * ln * 0.9)
        mid = ((root[0] + tip[0]) / 2, (root[1] + tip[1]) / 2)
        c.ellipse(mid, ln * 0.5, wd, ch, ang=a)
        c.capsule(root, tip, 0.5, 'W')

    # far wing pair a beat behind, then the legs and body, then the near pair
    wing(-ang * 0.15 + 150, 8.6, 2.0, 'A')
    for k in range(3):
        c.path([(17.0 + k * 1.6, 14.0), (16.4 + k * 1.8, 16.6), (15.6 + k * 2.0, 18.4)],
               0.45, 'l')
    # abdomen: bands are ink stripes cut into it, a sting at the tail
    c.ellipse((11.6, 13.6), 6.0, 3.6, 'y', ang=8.0)
    for bxp in (8.2, 11.0, 13.8):
        c.capsule((bxp, 10.0), (bxp - 0.8, 17.2), 0.65, 'o', only='y')
    c.poly([(6.2, 13.2), (3.0, 16.4), (6.8, 15.2)], 'w')
    c.capsule((14.6, 13.0), (16.8, 12.6), 0.9, 'k')                # waist
    c.ellipse((18.8, 12.4), 2.8, 2.6, 't')
    c.ellipse((23.0, 12.8), 2.4, 2.3, 'o')                         # head
    c.ellipse((23.8, 12.0), 1.4, 1.6, 'r')                         # the compound eye
    c.capsule((25.0, 14.2), (26.2, 15.0), 0.5, 'o')                # mandible
    c.path([(23.4, 10.6), (25.0, 8.2), (27.6, 7.4)], 0.45, 'l')    # antenna
    wing(ang + 180, 10.4, 2.3, 'A')
    c.outline()
    return c.rows()


# ================================================================== sheets
def _lit(rows_list, mat, **kw):
    kw.setdefault("rate", 0)
    kw.setdefault("lit", 1)
    kw.setdefault("dark", 1)
    return [palette.auto_shade(r, mat, **kw) for r in rows_list]


def walker_cells():
    return _lit([walker(i) for i in range(6)], WALKER)


def jumper_cells():
    # 0 idle  1-2 the crouch (TELL)  3 air  4 land  5 air kick  6 recover
    return _lit([jumper(p) for p in (J_IDLE, J_CROUCH, J_COIL, J_AIR, J_LAND,
                                     J_AIR2, J_RECOVER)], JUMPER)


def shooter_cells():
    # 0 idle  1-3 the bloom opening (TELL)  4 spit  5-6 idle sway
    return _lit([shooter(p) for p in (S_IDLE, S_STIR, S_INHALE, S_SWELL, S_FIRE,
                                      S_SWAY_A, S_SWAY_B)], SHOOTER)


def swimmer_cells():
    return _lit([swimmer(i) for i in range(6)], SWIMMER)


def charger_cells():
    # 0-5 patrol  6-8 the wind-up (TELL)  9-12 the charge  13-14 dazed
    return _lit(charger_frames(), CHARGER)


def dropper_cells():
    # 0 cling  1-4 letting go (TELL)  5-6 falling  7-12 crawl
    return _lit(dropper_frames(), DROPPER)


def flyer_cells():
    return _lit([flyer(i) for i in range(6)], FLYER)


#: sheet name -> (builder, cell w, cell h, render ox, render oy). The anchor is
#: where the unchanged hitbox sits inside the cell; data/enemies/*.json's
#: `render` block carries the same two numbers, and tests/test_enemies40.gd
#: holds the two together.
SHEETS = {
    "enemy_walker": (walker_cells, 32, 24, 9, 13),
    "enemy_jumper": (jumper_cells, 32, 32, 10, 21),
    "enemy_shooter": (shooter_cells, 32, 32, 10, 18),
    "enemy_swimmer": (swimmer_cells, 32, 24, 9, 8),
    "enemy_charger": (charger_cells, 32, 24, 9, 13),
    "enemy_dropper": (dropper_cells, 32, 32, 9, 8),
    "enemy_flyer": (flyer_cells, 32, 24, 9, 10),
}


def build_sheet(name):
    """Write one sheet through `palette.sheet` (selout on, as every character
    sheet is) and return its frame count."""
    fn, w, h, _, _ = SHEETS[name]
    cells = fn()
    palette.sheet(name, cells, w, h, selout=True)
    return len(cells)


# ================================================================ the bosses
# Every boss sheet is 64x64 cells, ten poses per fight phase, three phases:
#
#   0 idle   1 walk A   2 walk B   3 windup: anticipation   4 windup: the
#   full gather (the TELL)   5 airborne   6 landing / slam   7 idle, breath
#   8 walk C (passing)   9 walk D (passing)
#
# phase 1 is frames 0-9, phase 2 is 10-19, phase 3 is 20-29, and
# data/enemies/<boss>.json names them `<pose>_p1/_p2/_p3` exactly as before
# (src/enemies/<boss>.gd picks the suffix): idle [0, 7], walk [1, 8, 2, 9],
# windup [3, 4] held on 4, air [5], land/hurt [6]. Only the frame lists and the
# cell grew; every timing the fight runs on is in the controller, not here.
#
# The 40x46 collision boxes sit at (12, 18) of the cell -- centred, feet on
# row 63 -- and the Grove Warden's 26x42 at (19, 22). Each builder draws the
# animal's *body* over that box (tests/test_enemies40.gd measures how much of
# the box every frame covers) and lets only the parts a player would not aim
# at -- crowns, crests, the lure, jaws, wing tips, legs -- reach outside it.
BW = BH = 64
BFLOOR = 63.4

POSE_NAMES = ["idle", "walk_a", "walk_b", "antic", "gather", "air", "land",
              "idle_b", "walk_c", "walk_d"]


def rotate_rows(rows, ang, cx, cy):
    """Rotate a character grid by `ang` degrees about (cx, cy), sampling each
    destination pixel from its source (inverse mapping, so no holes)."""
    h, w = len(rows), len(rows[0])
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    out = []
    for y in range(h):
        r = []
        for x in range(w):
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            sx = cx + dx * ca + dy * sa
            sy = cy - dx * sa + dy * ca
            ix, iy = int(math.floor(sx)), int(math.floor(sy))
            r.append(rows[iy][ix] if 0 <= ix < w and 0 <= iy < h else '.')
        out.append("".join(r))
    return out


def rim(c, body, ch, only_up=True):
    """Re-paint the top edge of everything in `body` (characters) with `ch`:
    the brightest pixels along a crown, which is how a boss *lights up*."""
    marks = []
    for y in range(c.h):
        for x in range(c.w):
            if c.g[y][x] in body and c.get(x, y - 1) not in body:
                marks.append((x, y))
            elif not only_up and c.g[y][x] in body and c.get(x - 1, y) not in body:
                marks.append((x, y))
    for x, y in marks:
        c.g[y][x] = ch


def dust(c, n, seed, ch, y=62.6, x0=6, x1=58):
    for k in range(n):
        t = ((k * 0.618 + seed * 0.37) % 1.0)
        c.px(x0 + t * (x1 - x0), y - (k % 3) * 1.4, ch)


def _boss_frames(make, phases, poses):
    return [make(ph, po) for ph in phases for po in poses]


# ---------------------------------------------------------------- grove
# THE GROVE WARDEN (jungle_5). Seen from the front, as it always was: a squat
# purple beetle-golem with a blue belly plate, white mandibles, a gold crown
# and six legs. Phases differ in silhouette (tools/art/sprites.py's rule):
#   STOMP  squat and heavy on six thick legs, crown held low
#   LEAP   up on long legs, the carapace split open on its flight wings
#   FURY   spines through the shoulders, ember in the cracks, jaw open, eyes
#          gone white
# TELL -- the slam crouch (windup, frames 3-4): the body drops five pixels,
# the legs splay out past the box, the crown rears and the mandibles open.
GROVE = {
    'p': ("purple", 3), 'P': ("purple", 4), 'd': ("purple", 1),
    'n': ("water", 3), 'N': ("water", 2),
    'o': ("gold", 3), 'y': ("gold", 5),
    'w': ("metal", 6), 'A': ("water", 3), 'a': ("water", 5),     # wing, veins
    'r': ("ember", 4), 'R': ("ember", 5),
}
GROVE_PHASES = [
    dict(lift=0, ab=(17.0, 12.0), th=(12.0, 8.0), hd=(9.0, 7.0), leg=2.4, legx=0.0,
         horn=8.0, hang=26.0, jaw=0.0, spines=0, cracks=0, wings=0, eye='y'),
    dict(lift=5, ab=(14.5, 10.5), th=(11.0, 7.5), hd=(8.6, 6.6), leg=1.8, legx=2.0,
         horn=11.0, hang=36.0, jaw=2.0, spines=0, cracks=0, wings=1, eye='y'),
    dict(lift=3, ab=(16.0, 11.5), th=(12.0, 8.0), hd=(9.6, 7.0), leg=2.0, legx=3.0,
         horn=13.0, hang=48.0, jaw=4.5, spines=1, cracks=1, wings=0, eye='w'),
]
GROVE_POSES = [
    dict(dy=0.0, step=0.0, sway=0.0, crouch=0.0, spread=1.0, jaw=0.0, rear=0.0, dust=0, breath=0.0),
    dict(dy=0.0, step=1.0, sway=-1.0, crouch=0.0, spread=1.0, jaw=0.0, rear=0.0, dust=0, breath=0.0),
    dict(dy=0.0, step=-1.0, sway=1.0, crouch=0.0, spread=1.0, jaw=0.0, rear=0.0, dust=0, breath=0.0),
    dict(dy=0.0, step=0.0, sway=0.0, crouch=2.0, spread=1.12, jaw=1.0, rear=8.0, dust=0, breath=0.0),
    dict(dy=0.0, step=0.0, sway=0.0, crouch=5.0, spread=1.32, jaw=3.0, rear=18.0, dust=2, breath=0.0),
    dict(dy=-1.0, step=0.0, sway=0.0, crouch=-2.0, spread=0.7, jaw=2.0, rear=10.0, dust=0, breath=0.0),
    dict(dy=0.0, step=0.0, sway=0.0, crouch=4.0, spread=1.5, jaw=2.0, rear=-6.0, dust=7, breath=0.0),
    dict(dy=-0.6, step=0.0, sway=0.0, crouch=0.0, spread=1.0, jaw=0.0, rear=0.0, dust=0, breath=0.7),
    dict(dy=-1.0, step=0.35, sway=-0.4, crouch=0.0, spread=1.0, jaw=0.0, rear=0.0, dust=0, breath=0.0),
    dict(dy=-1.0, step=-0.35, sway=0.4, crouch=0.0, spread=1.0, jaw=0.0, rear=0.0, dust=0, breath=0.0),
]


def grove(ph, po):
    c = Canvas(BW, BH)
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
            c.ellipse((cx + s * 15.0, tcy - 2.0), 5.6, 13.0, 'A', ang=s * 28.0)
            c.path([(cx + s * 6.0, tcy - 4.0), (cx + s * 18.0, tcy - 12.0),
                    (cx + s * 22.0, tcy + 4.0)], 0.5, 'a', only='A')
    # legs: three pairs off the abdomen's sides, feet on the floor
    for s in (-1, 1):
        up = max(0.0, po["step"] * s) * 3.0
        for k, (hy, fx) in enumerate(((-6.0, 3.0), (0.0, 6.0), (5.0, 9.0))):
            hip = (cx + s * (arx - 3.0), acy + hy)
            foot = (32.0 + s * (arx + fx * 0.6 + ph["legx"]) * po["spread"]
                    + po["step"] * s * (k - 1) * 0.8, BFLOOR - 0.8 - up)
            kn = limb(c, hip, foot, 7.0 + ph["lift"] * 0.6, 7.0 + ph["lift"] * 0.5,
                      ph["leg"], ph["leg"] * 0.6, 'd' if k == 1 else 'p', bend=s)
            c.capsule(foot, (foot[0] + s * 1.6, foot[1]), 0.8, 'o')      # claw
            c.px(kn[0], kn[1] - 1, 'P')
    # abdomen with its plate courses and the belly plate
    c.ellipse((cx, acy), arx, ary, 'p')
    for k in (1, 2):
        c.ellipse((cx, acy + 1.0), arx - k * 4.0, ary - k * 3.2, 'd',
                  clip=lambda x, y, k=k: True, only='p')
        c.ellipse((cx, acy + 1.0), arx - k * 4.0 - 0.9, ary - k * 3.2 - 0.9, 'p', only='d')
    c.ellipse((cx, acy + 2.0), arx * 0.55, ary * 0.6, 'n')
    c.ellipse((cx, acy + 2.6), arx * 0.4, ary * 0.42, 'N')
    for k in range(3):
        c.capsule((cx - arx * 0.45, acy - 2.0 + k * 3.4), (cx + arx * 0.45, acy - 2.0 + k * 3.4),
                  0.45, 'N', only='n')
    if ph["cracks"]:
        for pts in (((cx - 10, acy - 6), (cx - 6, acy - 1), (cx - 9, acy + 4)),
                    ((cx + 11, acy - 5), (cx + 7, acy + 1), (cx + 10, acy + 6))):
            c.path(list(pts), 0.8, 'r', only='pdP')
            c.path(list(pts), 0.4, 'R', only='r')
    # thorax and head, each set off by an ink arc
    c.ellipse((cx, tcy), ph["th"][0], ph["th"][1], 'p')
    c.path([(cx - ph["th"][0] + 1, tcy + 3), (cx, tcy + ph["th"][1] - 0.4),
            (cx + ph["th"][0] - 1, tcy + 3)], 0.5, 'k')
    c.ellipse((cx - 3.0, tcy - 3.0), 4.0, 2.0, 'P')
    if ph["spines"]:
        for s in (-1, 1):
            for k in range(5):
                c.spike((cx + s * (ph["th"][0] - 1.0 + k * 1.6), tcy - 2.0 + k * 2.6),
                        s * (40 + k * 12), 6.0 - k * 0.6, 1.3, 'r')
    hx, hy = ph["hd"]
    c.ellipse((cx, hcy), hx, hy, 'd')
    c.ellipse((cx, hcy - 1.0), hx - 1.4, hy - 1.6, 'p')
    # crown: two horns sweeping out and a short spike between, rearing with
    # the tell
    for s in (-1, 1):
        a = s * (ph["hang"] - po["rear"])
        root = (cx + s * 3.0, hcy - hy + 2.0)
        mid = polar(root, ph["horn"] * 0.55, a)
        tip = polar(mid, ph["horn"] * 0.55, a + s * 18.0)
        c.path([root, mid, tip], 1.6, 'o', 0.6)
        c.px(tip[0], tip[1], 'y')
    c.spike((cx, hcy - hy + 1.5), 0.0, 4.0 + po["rear"] * 0.12, 1.4, 'o')
    # eyes
    for s in (-1, 1):
        e = (cx + s * 4.0, hcy - 1.0)
        c.ellipse(e, 2.3, 2.1, ph["eye"])
        if ph["eye"] != 'w':
            c.ellipse((e[0] + s * 0.3, e[1] + 0.3), 0.9, 1.0, 'k')
    # mandibles: two white hooks under the head, opening with the jaw
    for s in (-1, 1):
        root = (cx + s * 3.0, hcy + hy - 2.0)
        tip = (cx + s * (3.0 + jaw * 0.9), hcy + hy + 7.0 + jaw * 0.3)
        c.path([root, (root[0] + s * (2.6 + jaw * 0.5), root[1] + 3.0), tip], 1.6, 'w', 0.6)
    if jaw > 2.0:
        c.ellipse((cx, hcy + hy + 1.0), 1.4 + jaw * 0.3, 1.2 + jaw * 0.25, 'k')
        if ph["cracks"]:
            c.ellipse((cx, hcy + hy + 1.2), 0.8 + jaw * 0.15, 0.6 + jaw * 0.12, 'r')
    dust(c, po["dust"], 1, 'o')
    c.outline()
    return c.rows()


# ---------------------------------------------------------------- tide maw
# THE TIDE MAW (ruins_5). An anglerfish: a trunk leaving the frame at the
# bottom-left, a blunt skull, a mouth that is half the animal, a lure.
# TELL -- the gape (as before): the jaws open from a crack at rest to wider
# than the skull on the strike frames, on the half of the animal Kaya faces,
# and the lure folds back down over the head through the windup. The lure's
# colour is the phase: cyan EBB, gold FLOOD, ember UNDERTOW.
TIDE = {
    'b': ("water", 4), 'c': ("water", 5), 'r': ("ember", 3),
    'B': ("water", 3), 'C': ("water", 4), 'E': ("ember", 2),        # jaw shade
    'n': ("water", 1), 'l': ("water", 6),
    'y': ("gold", 5), 'o': ("gold", 4),
    'w': ("metal", 6), 'a': ("metal", 5),
}
TIDE_PHASES = [
    dict(body='b', shade='B', lure='l', eye='l', jaw=27.0, gape=0.0, gills=0, barb=0),
    dict(body='c', shade='C', lure='y', eye='w', jaw=29.0, gape=1.4, gills=3, barb=0),
    dict(body='r', shade='E', lure='o', eye='y', jaw=31.0, gape=2.6, gills=4, barb=1),
]
TIDE_POSES = [
    dict(dy=0.0, gape=6.0, tilt=0.0, stalk=1.0, swing=0.0, breath=0.0),
    dict(dy=-1.0, gape=6.0, tilt=0.0, stalk=1.0, swing=1.4, breath=0.0),
    dict(dy=0.0, gape=5.0, tilt=1.4, stalk=0.95, swing=-1.4, breath=0.0),
    dict(dy=-2.6, gape=5.0, tilt=1.4, stalk=0.6, swing=-1.4, breath=0.0),
    dict(dy=-5.0, gape=5.0, tilt=1.4, stalk=0.28, swing=0.0, breath=0.0),
    dict(dy=-4.0, gape=17.0, tilt=-4.0, stalk=1.0, swing=2.6, breath=0.0),
    dict(dy=4.0, gape=13.0, tilt=5.0, stalk=0.9, swing=-2.6, breath=0.0),
    dict(dy=0.6, gape=6.6, tilt=0.4, stalk=1.0, swing=0.6, breath=0.8),
    dict(dy=-0.5, gape=5.6, tilt=0.6, stalk=1.0, swing=0.6, breath=0.0),
    dict(dy=0.5, gape=5.4, tilt=0.8, stalk=0.98, swing=-0.6, breath=0.0),
]


def tide_maw(ph, po):
    c = Canvas(BW, BH)
    dy = po["dy"]
    body, shade = ph["body"], ph["shade"]
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
    c.path([(16.0, 27.0 + dy), (13.4, 35.0 + dy), (16.0, 44.0 + dy)], 0.55, 'k')  # operculum
    # mouth: cavity first, the two jaws over its edges
    ut = (hx + ph["jaw"], hy - 6.0 - gape * 0.55 + po["tilt"])
    lt = (hx + ph["jaw"] - 2.0, hy + 4.0 + gape * 0.45 + po["tilt"])
    c.poly([(hx - 2.0, hy - 1.0), ut, (ut[0] - 1.0, (ut[1] + lt[1]) / 2), lt], 'n')
    c.path([(hx - 6.0, hy - 6.0), ((hx + ut[0]) / 2, (hy - 6.0 + ut[1]) / 2 - 1.0), ut],
           5.0, body, 1.4)
    c.path([(hx - 4.0, hy + 5.0), ((hx + lt[0]) / 2, (hy + 6.0 + lt[1]) / 2 + 1.4), lt],
           5.4, shade, 1.6)
    # teeth: a comb on each jaw, pointing into the gap
    for k in range(7):
        t = 0.2 + k * 0.12
        u = (lerp(hx, ut[0], t), lerp(hy - 2.6, ut[1] + 1.0, t))
        l = (lerp(hx, lt[0], t), lerp(hy + 2.2, lt[1] - 1.2, t))
        ln = 2.6 + (k % 2) * 1.2
        c.capsule(u, (u[0] + 0.4, u[1] + ln), 0.55, 'w', 0.2)
        c.capsule(l, (l[0] - 0.4, l[1] - ln), 0.55, 'w', 0.2)
    # gill rakers
    for k in range(ph["gills"]):
        x = 18.0 + k * 2.4
        c.capsule((x, 37.0 + dy), (x - 1.4, 43.0 + dy), 0.5, 'n')
    # barbels, UNDERTOW only
    if ph["barb"]:
        for k in range(2):
            c.path([(hx + 6.0 + k * 4, hy + 8.0 + gape * 0.2), (hx + 2 + k * 3, hy + 15.0),
                    (hx - 6 + k * 2, hy + 20.0 - k * 2)], 0.6, 'o')
    # the eye: a block in an ink socket with a catchlight, no pupil
    c.ellipse((30.0, 28.0 + dy), 3.2, 3.0, 'k')
    c.ellipse((30.0, 28.0 + dy), 2.2, 2.0, ph["eye"])
    c.px(29.0, 27.0 + dy, 'w')
    # the lure: a stalk off the crown arcing up and forward over the mouth
    s = po["stalk"]
    root = (21.0, 26.0 + dy)
    p1 = (lerp(root[0], 24.0, s), lerp(root[1], 10.0 + dy * 0.5, s))
    p2 = (lerp(root[0] - 2, 38.0, s), lerp(root[1] - 4, 4.0 + dy * 0.5, s))
    bulb = (lerp(root[0] + 2, 47.0 + po["swing"], s), lerp(root[1] - 6, 11.0 + dy * 0.4, s))
    c.path([root, p1, p2, bulb], 1.1, shade, 0.6)
    c.ellipse(bulb, 3.4, 3.4, 'k')
    c.ellipse(bulb, 2.6, 2.6, ph["lure"])
    c.px(bulb[0] - 1.0, bulb[1] - 1.0, 'w')
    c.outline()
    return c.rows()


# ---------------------------------------------------------------- stormcrest
# THE STORMCREST (heights_5). A hook-beaked ridge raptor, drawn facing right
# like every other sheet (the 48 px sheet faced left, so it was drawn looking
# away from the player whenever it turned to face her).
# The fight's one idea -- it can only be hurt while it roosts -- is the art's
# one job, kept from the 48 px sheet:
#   * airborne (frame 5) is the only diagonal: the whole bird pitched
#     nose-down through 34 degrees with the legs tucked away;
#   * roosting is legs: every other frame stands on the floor row.
# TELL -- the gather (frames 3-4): the bird sinks on its legs, the wings come
# off the back and the crest fans out, so the launch is announced by the
# outline doubling in width before it leaves the floor.
STORM = {
    'a': ("stone", 3), 'A': ("stone", 5), 'd': ("stone", 1),
    'w': ("metal", 6), 'y': ("gold", 5), 'o': ("gold", 3),
    'r': ("ember", 4),
}
STORM_PHASES = [
    dict(body='a', belly='A', plume='w', eye='y', crest=9.0, fan=5, span=21.0, tail=14.0, ember=0),
    dict(body='A', belly='w', plume='y', eye='y', crest=12.0, fan=6, span=24.0, tail=17.0, ember=0),
    dict(body='d', belly='a', plume='o', eye='r', crest=15.0, fan=7, span=27.0, tail=20.0, ember=1),
]
STORM_POSES = [
    dict(dy=0.0, ang=0.0, open=0.0, step=0.0, fanned=0.0, legs=1, breath=0.0),
    dict(dy=1.0, ang=0.0, open=0.2, step=4.0, fanned=0.2, legs=1, breath=0.0),
    dict(dy=0.0, ang=0.0, open=0.3, step=-4.0, fanned=0.0, legs=1, breath=0.0),
    dict(dy=3.0, ang=0.0, open=0.45, step=-2.0, fanned=0.5, legs=1, breath=0.0),
    dict(dy=6.0, ang=0.0, open=0.7, step=0.0, fanned=1.0, legs=1, breath=0.0),
    dict(dy=-6.0, ang=34.0, open=1.0, step=0.0, fanned=0.6, legs=0, breath=0.0),
    dict(dy=3.0, ang=0.0, open=1.0, step=6.0, fanned=0.8, legs=1, breath=0.0),
    dict(dy=-0.5, ang=0.0, open=0.05, step=0.0, fanned=0.15, legs=1, breath=0.8),
    dict(dy=-1.0, ang=0.0, open=0.25, step=1.5, fanned=0.1, legs=1, breath=0.0),
    dict(dy=-1.0, ang=0.0, open=0.25, step=-1.5, fanned=0.1, legs=1, breath=0.0),
]


def stormcrest(ph, po):
    c = Canvas(BW, BH)
    body, belly, plume = ph["body"], ph["belly"], ph["plume"]
    dy = po["dy"]
    bx, by = 29.0, 37.0 + dy
    # legs first (straight to the grid; they do not rotate)
    legs = Canvas(BW, BH)
    if po["legs"]:
        for k, s in ((0, 1), (1, -1)):
            hip = (bx + 2.0 + k * 4.0, by + 9.0)
            foot = (bx + 3.0 + k * 4.0 + po["step"] * s * 0.6, BFLOOR - 1.4)
            limb(legs, hip, foot, 9.4, 9.8, 1.5, 1.0, 'o', bend=-1)
            for t in (-1, 0, 1):
                legs.capsule(foot, (foot[0] + 2.6 * t + 1.0, foot[1] + 0.8), 0.6, 'k')
    # tail: a wedge off the back, low, under the wing
    tl = ph["tail"]
    c.poly([(bx - 8.0, by - 2.0), (bx - 8.0 - tl, by + 4.0 - po["open"] * 3),
            (bx - 6.0 - tl * 0.9, by + 9.0), (bx - 6.0, by + 5.0)], plume)
    for k in range(3):
        c.capsule((bx - 8.0, by + 1.0 + k), (bx - 7.0 - tl * (0.7 + k * 0.08), by + 3.0 + k * 2.4),
                  0.45, body, only=plume)
    # the mass: an egg lying forward, the pale breast low and forward
    c.ellipse((bx, by), 15.0, 10.6 + po["breath"] * 0.4, body, ang=-8.0)
    c.ellipse((bx + 6.0, by + 3.0), 9.0, 7.0, belly, ang=-20.0)
    for k in range(4):                                             # breast barring
        c.path([(bx + 1.0 + k * 3.0, by + 0.0), (bx + 2.0 + k * 3.0, by + 3.0),
                (bx + 1.0 + k * 3.0, by + 6.0)], 0.45, body, only=belly)
    # head, beak, eye
    hx, hy = bx + 14.0, by - 11.0
    c.capsule((bx + 8.0, by - 4.0), (hx - 1.0, hy + 2.0), 5.0, body, 4.0)   # neck
    c.ellipse((hx, hy), 6.4, 5.8, body)
    c.ellipse((hx + 2.0, hy + 2.4), 4.0, 3.0, belly, only=body)
    c.poly([(hx + 4.0, hy - 2.6), (hx + 10.6, hy - 1.0), (hx + 12.0, hy + 2.6),
            (hx + 10.4, hy + 4.4), (hx + 9.8, hy + 1.6), (hx + 4.6, hy + 2.6)], 'y')
    c.capsule((hx + 5.0, hy + 0.6), (hx + 9.4, hy + 1.4), 0.45, 'o')          # gape line
    c.ellipse((hx + 2.4, hy - 1.4), 1.6, 1.5, ph["eye"])
    c.px(hx + 3.0, hy - 1.4, 'k')
    c.capsule((hx + 0.6, hy - 3.4), (hx + 4.2, hy - 3.0), 0.5, 'k')          # brow
    # crest: a fan of feathers off the crown, swept back
    fan = ph["fan"]
    for k in range(fan):
        t = k / max(1, fan - 1)
        a = -95.0 + t * (50.0 + 30.0 * po["fanned"])
        ln = ph["crest"] * (0.7 + 0.4 * math.sin(t * math.pi)) * (1.0 + 0.15 * po["fanned"])
        root = (hx - 2.0, hy - 3.0)
        tip = polar(root, ln, a)
        c.path([root, ((root[0] + tip[0]) / 2, (root[1] + tip[1]) / 2 - 1.0), tip], 1.3, plume, 0.5)
    # wing: folded along the back, or swung up and back with its primaries
    op = po["open"]
    sh = (bx + 6.0, by - 6.0)
    wa = lerp(-100.0, -20.0, op)                     # from straight back to raised
    span = ph["span"] * lerp(0.75, 1.0, op)
    tip = polar(sh, span, wa)
    c.path([sh, ((sh[0] + tip[0]) / 2, (sh[1] + tip[1]) / 2 + 2.0 - op * 3), tip],
           5.4, body, 2.4)
    for k in range(5):                                             # primaries
        t = 0.55 + k * 0.11
        root = (lerp(sh[0], tip[0], t), lerp(sh[1], tip[1], t) + 1.0)
        fa = wa + 180.0 - 40.0 + k * 10.0 - op * 40.0
        c.capsule(root, polar(root, 6.0 + k * 1.2, fa), 1.0, body, 0.5)
    for k in range(2):                                             # the bars
        t = 0.35 + k * 0.25
        a0 = (lerp(sh[0], tip[0], t) - 2.0, lerp(sh[1], tip[1], t) - 2.5)
        a1 = (lerp(sh[0], tip[0], t) + 2.0, lerp(sh[1], tip[1], t) + 2.5)
        c.capsule(a0, a1, 0.8, plume, only=body)
    if ph["ember"]:
        for k in range(3):
            c.capsule((bx - 8.0 + k * 5, by + 2.0 - k), (bx - 4.0 + k * 5, by + 6.0 - k), 0.6,
                      'r', only=body)
    rows = c.rows()
    if po["ang"]:
        rows = rotate_rows(rows, po["ang"], bx + 4.0, by)
    # composite the (unrotated) legs behind the body
    out = Canvas(BW, BH)
    for y in range(BH):
        for x in range(BW):
            ch = rows[y][x]
            out.g[y][x] = ch if ch != '.' else legs.g[y][x]
    out.outline()
    return out.rows()


# ---------------------------------------------------------------- brood queen
# THE BROOD QUEEN (deeps_5). A termite queen: an abdomen the size of the rest
# of her, a small armoured thorax, a head that is mostly mandibles.
# The brightness is the mechanic (src/enemies/brood_queen.gd fades her to
# `dark_alpha` whenever she is not attacking), so the four attack poses --
# anticipation, gather, charge, slam (frames 3-6) -- carry a rim of the
# brightest character along the abdomen's crown, the thorax plate and the
# jaws, and the crawl and idle beats carry none.
# TELL -- the gather: she rears, the abdomen arches up off the floor, the
# head draws back and the jaws open, and the rim lights before the strike.
# Body steps sit low on purpose: the attack poses' white rim has to be the
# brightest thing on her in every phase, and a pale abdomen lit two steps up
# by auto_shade() would be as bright as the rim (measured: tests/test_enemies40).
QUEEN = {
    'n': ("skin", 0), 'b': ("skin", 2), 'l': ("skin", 3),
    'a': ("stone", 3), 'A': ("stone", 4), 'w': ("metal", 6),
    'y': ("gold", 5), 'o': ("gold", 3), 'r': ("ember", 5), 'R': ("ember", 3),
}
QUEEN_PHASES = [
    dict(body='b', seg='n', glow='n', plate='a', jaw='a', split=None, blisters=0, spines=0, gape=3.0),
    dict(body='l', seg='b', glow='y', plate='A', jaw='y', split=None, blisters=3, spines=0, gape=5.0),
    dict(body='l', seg='b', glow='r', plate='y', jaw='r', split='r', blisters=3, spines=6, gape=8.0),
]
QUEEN_POSES = [
    dict(dy=0.0, arch=0.0, reach=0.0, legs=0, lit=0, dust=0, gape=0.0, breath=0.0),
    dict(dy=-0.6, arch=1.0, reach=1.0, legs=-1, lit=0, dust=0, gape=0.0, breath=0.0),
    dict(dy=0.0, arch=-0.6, reach=-0.6, legs=1, lit=0, dust=1, gape=0.0, breath=0.0),
    dict(dy=-1.4, arch=3.0, reach=-1.6, legs=1, lit=1, dust=2, gape=2.0, breath=0.0),
    dict(dy=-2.6, arch=5.6, reach=-3.0, legs=0, lit=1, dust=3, gape=4.0, breath=0.0),
    dict(dy=1.4, arch=-2.4, reach=4.0, legs=-1, lit=1, dust=6, gape=3.0, breath=0.0),
    dict(dy=2.4, arch=-3.4, reach=2.0, legs=1, lit=1, dust=9, gape=5.0, breath=0.0),
    dict(dy=-0.4, arch=0.6, reach=0.0, legs=0, lit=0, dust=0, gape=0.0, breath=0.8),
    dict(dy=-1.0, arch=0.4, reach=0.4, legs=0, lit=0, dust=0, gape=0.0, breath=0.0),
    dict(dy=-0.4, arch=-0.2, reach=-0.2, legs=0, lit=0, dust=1, gape=0.0, breath=0.0),
]


def brood_queen(ph, po):
    c = Canvas(BW, BH)
    body, seg = ph["body"], ph["seg"]
    ax, ay = 26.0, 44.0 + po["dy"] - po["arch"] * 0.5
    arx, ary = 21.0, 17.0 + po["arch"] * 0.5 + po["breath"]
    # ovipositor, off the bottom-left
    c.path([(10.0, 54.0 + po["dy"]), (2.0, 60.0), (-4.0, 63.0)], 5.0, body, 3.0)
    # legs under the thorax, behind it
    tx, ty = 47.0 + po["reach"] * 0.6, 49.0 + po["dy"]
    for k in range(3):
        hip = (tx - 4.0 + k * 4.0, ty + 3.0)
        off = po["legs"] * (1 if k % 2 else -1) * 2.0
        limb(c, hip, (hip[0] + 2.0 + off, BFLOOR - 1.0), 5.0, 6.0, 1.3, 0.8, 'a',
             bend=1 if k else -1)
    # abdomen: bands, the glow between them, blisters, the split
    c.ellipse((ax, ay), arx, ary, body)
    for k in range(5):                                             # dorsal tubercles
        t = 0.2 + k * 0.15
        bxp = ax - arx + t * 2 * arx
        top = ay - ary * math.sqrt(max(0.0, 1 - ((bxp - ax) / arx) ** 2))
        c.ellipse((bxp, top + 1.0), 2.6, 2.4, body)
    for k in range(6):
        bxp = ax - arx + 6.0 + k * 6.0
        c.path([(bxp + 1.6, ay - ary - 2.0), (bxp - 1.0, ay), (bxp + 1.6, ay + ary + 2.0)], 1.3,
               seg, only=body)
        if ph["glow"] != seg:
            c.path([(bxp + 1.6, ay - ary - 2.0), (bxp - 1.0, ay), (bxp + 1.6, ay + ary + 2.0)],
                   0.4, ph["glow"], only=seg)
    c.ellipse((ax + 2.0, ay + ary * 0.6), arx * 0.8, ary * 0.3, 'n' if body == 'b' else 'b',
              only=body)                                          # underside shadow
    for k in range(ph["blisters"]):
        c.ellipse((ax - 10.0 + k * 9.0, ay + ary * 0.55), 3.4, 2.6, 'w' if k == 1 else 'l')
        c.ellipse((ax - 10.0 + k * 9.0, ay + ary * 0.55), 3.4, 2.6, 'y', only='w')
    if ph["split"]:
        for k in range(4):
            bxp = ax - 12.0 + k * 7.0
            c.poly([(bxp - 1.6, ay - 9.0), (bxp + 3.0, ay - 3.0), (bxp + 0.4, ay + 2.0),
                    (bxp + 3.4, ay + 9.0), (bxp - 2.4, ay + 4.0), (bxp - 0.6, ay - 1.0)], 'R')
            c.poly([(bxp - 0.8, ay - 6.0), (bxp + 1.8, ay - 2.4), (bxp, ay + 2.0),
                    (bxp + 2.0, ay + 6.0), (bxp - 1.4, ay + 3.0), (bxp - 0.2, ay - 1.0)], 'r')
            c.capsule((bxp + 0.2, ay - 3.0), (bxp + 0.4, ay + 3.0), 0.4, 'y', only='r')
    for k in range(ph["spines"]):
        t = 0.15 + k * 0.13
        bxp = ax - arx + t * 2 * arx
        top = ay - ary * math.sqrt(max(0.0, 1 - ((bxp - ax) / arx) ** 2))
        c.spike((bxp, top + 1.0), -20.0 + k * 6, 5.0, 1.2, 'o')
    # thorax plate and head capsule
    c.ellipse((tx, ty - 1.0), 6.6, 6.0, ph["plate"])
    c.path([(tx - 5.0, ty - 2.0), (tx, ty + 0.4), (tx + 5.0, ty - 2.0)], 0.5, 'k')
    hx, hy = tx + 8.4 + po["reach"], ty - 1.0
    c.ellipse((hx, hy), 5.4, 5.0, ph["plate"])
    c.px(hx + 1.6, hy - 2.0, 'k')
    c.px(hx + 2.6, hy - 2.0, 'k')
    # mandibles: two sickles leaving the right of the frame, opening with gape
    g = ph["gape"] + po["gape"]
    for s in (-1, 1):
        root = (hx + 3.6, hy + 1.0 + s * 1.6)
        tip = (hx + 12.0, hy + 1.0 + s * (1.0 + g * 0.6) - 1.0)
        c.path([root, (hx + 9.0, hy + 1.0 + s * (2.6 + g * 0.5)), tip], 1.8, ph["jaw"], 0.5)
    if po["lit"]:
        # Two pixels deep: at 12 % alpha over a dark chamber a one-pixel rim
        # on a pale body is not there at all.
        lit_set = set((body, seg, ph["glow"], 'n', 'b', ph["plate"], ph["jaw"], 'l', 'o', 'R', 'r'))
        rim(c, lit_set, 'w')
        rim(c, lit_set, 'w')
    dust(c, po["dust"], 2, 'o', x0=20, x1=60)
    c.outline()
    return c.rows()


# ---------------------------------------------------------------- obsidian
# THE OBSIDIAN HEART (nest_5). A heart of black volcanic glass on four stubby
# glass roots, ember-lit from inside. The glass is the phase: SEALED is a
# closed stone with cold seams, INVERTED has split along them with gold light
# in the cracks and shards riding beside it, MOLTEN is a rind around a hole
# of fire.
# TELL -- the flare: on the four attack poses (3-6) the core is overdriven --
# bigger, a brighter colour, the cracks lit -- and on the gather the heart
# squats, throws its crown back and widens, so it brightens before it hits.
OBSIDIAN = {
    'g': ("purple", 0), 'G': ("purple", 2), 'h': ("water", 4),
    'w': ("metal", 6), 'o': ("gold", 3), 'y': ("gold", 5),
    'r': ("ember", 3), 'R': ("ember", 5),
}
OBS_PHASES = [
    dict(shell='g', seam='G', crack='h', core='o', rim='h', gape=1.4, core_r=5.0,
         crack_n=3, crack_w=0.6, shards=0),
    dict(shell='G', seam='h', crack='y', core='r', rim='w', gape=4.0, core_r=7.4,
         crack_n=5, crack_w=1.0, shards=3),
    dict(shell='g', seam='y', crack='R', core='y', rim='w', gape=7.0, core_r=8.8,
         crack_n=7, crack_w=1.5, shards=5),
]
OBS_POSES = [
    dict(dy=0.0, squash=0.0, lean=0.0, roots=0, flare=0.0, dust=0, breath=0.0),
    dict(dy=-1.0, squash=-0.4, lean=0.8, roots=-1, flare=0.0, dust=0, breath=0.0),
    dict(dy=0.0, squash=0.5, lean=-0.6, roots=1, flare=0.0, dust=1, breath=0.0),
    dict(dy=-1.0, squash=1.0, lean=-1.5, roots=1, flare=0.5, dust=2, breath=0.0),
    dict(dy=-2.0, squash=1.6, lean=-2.4, roots=0, flare=1.0, dust=3, breath=0.0),
    dict(dy=-4.0, squash=-1.8, lean=3.2, roots=1, flare=1.5, dust=5, breath=0.0),
    dict(dy=2.0, squash=2.4, lean=1.0, roots=-1, flare=2.0, dust=9, breath=0.0),
    dict(dy=-0.4, squash=0.2, lean=0.0, roots=0, flare=0.0, dust=0, breath=1.0),
    dict(dy=-1.2, squash=-0.1, lean=0.3, roots=0, flare=0.0, dust=0, breath=0.0),
    dict(dy=-0.6, squash=0.1, lean=-0.3, roots=0, flare=0.0, dust=0, breath=0.0),
]


def obsidian_heart(ph, po):
    c = Canvas(BW, BH)
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
        c.path([top, (cx + rx * 1.1, pt_y + 1.0), (cx + rx * 1.25 + 1.0, BFLOOR - 0.8 - lift)],
               2.6, ph["seam"] if k % 2 else ph["shell"], 1.6)
    # the heart: two lobes and the point, the crown leaned
    for s in (-1, 1):
        c.ellipse((cx + s * dxl + lean, lobe_y), r, r, ph["shell"])
    c.poly([(cx - dxl - r * 0.94 + lean, lobe_y + r * 0.34), (cx, pt_y + 1.0),
            (cx + dxl + r * 0.94 + lean, lobe_y + r * 0.34),
            (cx + lean, lobe_y)], ph["shell"])
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
    for k in range(ph["crack_n"]):
        a = -150.0 + k * 300.0 / max(1, ph["crack_n"] - 1) + (k % 2) * 9.0
        mid = polar(core, cr + 5.0, a + 8.0)
        tip = polar(core, cr + 15.0, a - 6.0)
        c.path([core, mid, tip], ph["crack_w"] + po["flare"] * 0.3, crack_ch, 0.4,
               only=(ph["shell"], ph["seam"]))
    for k in range(2):                                             # cold seams
        a = -60.0 + k * 140.0
        c.path([polar(core, cr + 2.0, a), polar(core, cr + 12.0, a + 15.0)], 0.5, ph["seam"],
               only=(ph["shell"],))
    c.ellipse(core, cr + 1.2, cr + 1.0, ph["seam"], only=(ph["shell"],))
    c.ellipse(core, cr, cr * 0.94, ph["core"])
    c.ellipse(core, cr * 0.55, cr * 0.5,
              'y' if po["flare"] >= 0.5 else ('R' if ph["core"] == 'r' else 'o'))
    if hot:
        c.ellipse(core, cr * 0.25, cr * 0.25, 'w')
    # the rim light along the crown
    rim(c, set((ph["shell"],)), ph["rim"])
    for k in range(ph["shards"]):
        a = -120.0 + k * 60.0
        p = polar((cx, lobe_y + 6.0), 27.0 + (k % 2) * 2.0, a + po["lean"] * 4.0)
        c.poly([(p[0] - 1.6, p[1]), (p[0], p[1] - 2.6), (p[0] + 1.8, p[1] + 0.4),
                (p[0] + 0.2, p[1] + 2.4)], ph["shell"])
        c.px(p[0], p[1] - 1.4, ph["rim"])
    dust(c, po["dust"], 3, 'G')
    c.outline()
    return c.rows()


def _boss_lit(rows_list, mat):
    return [palette.auto_shade(r, mat, depth=3, rate=1.0, lit=1.0, dark=1.0)
            for r in rows_list]


def grove_cells():
    return _boss_lit(_boss_frames(grove, GROVE_PHASES, GROVE_POSES), GROVE)


def tide_maw_cells():
    return _boss_lit(_boss_frames(tide_maw, TIDE_PHASES, TIDE_POSES), TIDE)


def stormcrest_cells():
    return _boss_lit(_boss_frames(stormcrest, STORM_PHASES, STORM_POSES), STORM)


def brood_queen_cells():
    return [palette.auto_shade(r, QUEEN, depth=2, rate=1.0, lit=1.0, dark=1.0)
            for r in _boss_frames(brood_queen, QUEEN_PHASES, QUEEN_POSES)]


def obsidian_heart_cells():
    return _boss_lit(_boss_frames(obsidian_heart, OBS_PHASES, OBS_POSES), OBSIDIAN)


SHEETS.update({
    "boss_grove": (grove_cells, BW, BH, 19, 22),
    "boss_tide_maw": (tide_maw_cells, BW, BH, 12, 18),
    "boss_stormcrest": (stormcrest_cells, BW, BH, 12, 18),
    "boss_brood_queen": (brood_queen_cells, BW, BH, 12, 18),
    "boss_obsidian_heart": (obsidian_heart_cells, BW, BH, 12, 18),
})
