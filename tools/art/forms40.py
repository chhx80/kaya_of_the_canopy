"""Kaya's three animal forms, redrawn to stand next to the 40 px Kaya.

The old frog, fish and bird were 16x16 hand-written grids from the first art
pass. Beside the 40 px puppet (tools/art/kaya40.py) they read as somebody else's
animals, so they are rebuilt the way she is: parts placed by coordinates,
rasterised into the character-grid format, inked, then lit by `auto_shade` with
her own settings and outlined by the sheet's selective outline.

Each one is HER, transformed, and carries her outfit so a player never wonders
whose frog that is:

  * frog -- her green top as the skin, her yellow shorts as the throat and
    belly, the bead necklace at the throat, and her straw hat, shrunk, between
    the eyes;
  * fish -- yellow body (the shorts), green back and fins (the top), the beads
    as a gill line, and the little hat riding on its head;
  * bird -- green body, yellow breast, red feet for the sandals, her long dark
    hair as the tail plumes, and the hat.

Collision does not change, so the drawing has to live with a small hitbox
(frog 12x11, fish 14x9, bird 12x9). Rules every frame keeps, asserted in
`frames_*()` and again by tests/test_forms40.gd against the shipped sheets:

  * nothing below the hitbox -- the feet ARE its bottom row (a frog on a floor,
    a beached fish, a perched bird all have rock right there);
  * at most `MAX_RISE` px above it, so every form still fits a one-tile (16 px)
    tunnel with the pixel of rounding spare kaya40 keeps for the same reason;
  * the frog's cling frames draw nothing outside the hitbox's columns, because
    a wall is flush with it there.

Sideways overhang past a wall, and a rise under a low ceiling while airborne,
are handled the way they are for her: the generator writes a `.bounds.json`
beside each sheet and the form's `pose` block hands it to src/player/kaya_pose.gd,
which nudges the drawn frame off the rock. tools/clipgate.sh --all-forms proves
it against every proof tape.
"""

import json
import math
import os

from PIL import Image

from . import palette

# char -> (ramp, base level), the same materials and levels as kaya40.MAT so a
# frog's green is literally the green of her top.
MAT = {
    'g': ("cloth", 2.9), 'G': ("cloth", 1.9),      # her top: skin, back, fins
    'd': ("cloth", 1.4),                            # spots, far limbs' shadow
    'y': ("gold", 5.0), 'Y': ("gold", 3.9),         # her shorts: belly, body
    'a': ("straw", 3.6), 'A': ("straw", 2.4),       # the hat
    'n': ("dirt", 1.8),                             # hat ribbon
    'b': ("ember", 4.8),                            # beads
    'r': ("ember", 3.0), 'R': ("ember", 2.0),       # sandals: bird feet, tongue
    'h': ("hair", 2.6), 'H': ("hair", 1.5),         # her hair: the bird's tail
    'w': ("metal", 6.0),                            # eye white
    'e': ("hair", 1.6),                             # iris
}

# Every form keeps this much headroom spare in a one-tile tunnel: 16 px of
# space, minus the pixel the rounded render position can add (see kaya40's
# STOOP_TOP), minus the hitbox height, is the most a frame may rise above it.
TUNNEL = 16
ROUNDING = 1


class Canvas:
    """kaya40.Canvas with its size as a parameter."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.g = [['.'] * w for _ in range(h)]

    def _set(self, x, y, ch):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.g[y][x] = ch

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.g[y][x]
        return '.'

    def capsule(self, a, b, r0, ch, r1=None):
        r1 = r0 if r1 is None else r1
        ax, ay = a
        bx, by = b
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy or 1e-9
        rr = max(r0, r1)
        for y in range(int(min(ay, by) - rr - 1), int(max(ay, by) + rr + 2)):
            for x in range(int(min(ax, bx) - rr - 1), int(max(ax, bx) + rr + 2)):
                px, py = x + 0.5, y + 0.5
                t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
                qx, qy = ax + t * dx, ay + t * dy
                r = r0 + (r1 - r0) * t
                if (px - qx) ** 2 + (py - qy) ** 2 <= r * r:
                    self._set(x, y, ch)

    def ellipse(self, c, rx, ry, ch, clip=None, rot=0.0):
        cx, cy = c
        cs, sn = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        rr = max(rx, ry)
        for y in range(int(cy - rr - 1), int(cy + rr + 2)):
            for x in range(int(cx - rr - 1), int(cx + rr + 2)):
                px, py = x + 0.5 - cx, y + 0.5 - cy
                u = px * cs + py * sn
                v = -px * sn + py * cs
                if (u / rx) ** 2 + (v / ry) ** 2 <= 1.0:
                    if clip is None or clip(x + 0.5, y + 0.5):
                        self._set(x, y, ch)

    def poly(self, pts, ch):
        """Filled polygon, pixel centres inside (even-odd)."""
        ys = [p[1] for p in pts]
        for y in range(int(min(ys)) - 1, int(max(ys)) + 2):
            py = y + 0.5
            xs = []
            for i in range(len(pts)):
                (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % len(pts)]
                if (y0 <= py < y1) or (y1 <= py < y0):
                    xs.append(x0 + (py - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for a, b in zip(xs[::2], xs[1::2]):
                for x in range(int(math.floor(a)), int(math.ceil(b)) + 1):
                    if a <= x + 0.5 <= b:
                        self._set(x, y, ch)

    def px(self, x, y, ch):
        self._set(int(math.floor(x)), int(math.floor(y)), ch)

    def outline(self):
        out = [row[:] for row in self.g]
        for y in range(self.h):
            for x in range(self.w):
                if self.g[y][x] != '.':
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.w and 0 <= ny < self.h and self.g[ny][nx] not in '.k':
                        out[y][x] = 'k'
                        break
        self.g = out

    def rows(self):
        return ["".join(r) for r in self.g]


# ===================================================================== HD
# docs/plan-hd.md step 2: the forms are drawn natively at ART_SCALE texels per
# world unit. `HDCanvas` takes the SAME world-unit coordinates the 1x Canvas
# takes and rasterises them S times as finely, so the poses, the silhouettes and
# every rule above are the 1x ones; `t()` and `stroke()` work in native texels
# for what only exists at this size (catch-lights, warts, scales, fin rays,
# feather rows, webbed toes). Each frame builder takes `hd=True` and adds those
# passes in its own `if hd:` blocks; with `hd=False` it is byte-for-byte the 1x
# drawing, which the checks still run on.
S = palette.ART_SCALE

# 1x materials plus the ones only 2x has room for (kaya40.MAT_HD's choices
# where the material is the same: her straw, ribbon, beads and eye).
MAT_HD = dict(MAT)
MAT_HD.update({
    'l': ("cloth", 4.3),                        # warts, ridge, toe pads, covert edges
    'f': ("cloth", 3.7),                        # web and fin membrane, lit
    'D': ("cloth", 0.7),                        # spot core, fin ray, feather split
    'F': ("cloth", 1.0),                        # ray on a dark fin
    'q': ("gold", 4.0),                         # throat fold, scale edge
    'Q': ("gold", 6.0),                         # belly sheen, scale glint
    'o': ("gold", 2.6),                         # scale edge on the flank
    'i': ("hair", 4.2), 'j': ("hair", 0.8),     # plume sheen, plume groove
    'x': ("straw", 5.6),                        # sunlit brim lip, beak ridge
    'v': ("straw", 2.2),                        # weave shadow
    'V': ("straw", 1.2),                        # brim underside, beak hook
    'K': ("straw", 0.6),                        # nostril, gape, claws
    'P': ("straw", 4.8),                        # upper mandible
    'N': ("dirt", 3.6),                         # ribbon highlight
    'B': ("ember", 6.0),                        # bead catch-light
    'E': ("hair", 0.2),                         # pupil
    'm': ("ember", 1.0),                        # inside the mouth
    'W': ("metal", 4.6),                        # teeth
})


def _hash(x, y, salt=0):
    """A fixed scatter for texture: the same frame always gets the same warts."""
    return ((x * 73856093) ^ (y * 19349663) ^ (salt * 83492791)) & 0xffff


class HDCanvas(Canvas):
    """A Canvas of `w`x`h` world units at `s` texels each. Shape calls take
    world units and return the set of texels they wrote, so a detail pass can
    work on exactly one part (one wing, one thigh) whatever else shares its
    material character."""

    def __init__(self, w, h, s=S, ceiling=None):
        self.s = s
        self.w, self.h = w * s, h * s
        self.g = [['.'] * self.w for _ in range(self.h)]
        self.ceiling = ceiling

    def _put(self, x, y, ch, only, got):
        if 0 <= x < self.w and 0 <= y < self.h and (only is None or self.g[y][x] in only):
            self.g[y][x] = ch
            got.add((x, y))

    def capsule(self, a, b, r0, ch, r1=None, only=None):
        s = self.s
        r1 = r0 if r1 is None else r1
        ax, ay, bx, by = a[0] * s, a[1] * s, b[0] * s, b[1] * s
        r0, r1 = r0 * s, r1 * s
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy or 1e-9
        rr = max(r0, r1)
        got = set()
        for y in range(int(min(ay, by) - rr - 1), int(max(ay, by) + rr + 2)):
            for x in range(int(min(ax, bx) - rr - 1), int(max(ax, bx) + rr + 2)):
                px, py = x + 0.5, y + 0.5
                t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
                qx, qy = ax + t * dx, ay + t * dy
                r = r0 + (r1 - r0) * t
                if (px - qx) ** 2 + (py - qy) ** 2 <= r * r:
                    self._put(x, y, ch, only, got)
        return got

    def ellipse(self, c, rx, ry, ch, clip=None, rot=0.0, only=None):
        s = self.s
        cx, cy, rx, ry = c[0] * s, c[1] * s, rx * s, ry * s
        cs, sn = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        rr = max(rx, ry)
        got = set()
        for y in range(int(cy - rr - 1), int(cy + rr + 2)):
            for x in range(int(cx - rr - 1), int(cx + rr + 2)):
                px, py = x + 0.5 - cx, y + 0.5 - cy
                u = px * cs + py * sn
                v = -px * sn + py * cs
                if (u / rx) ** 2 + (v / ry) ** 2 <= 1.0:
                    if clip is None or clip((x + 0.5) / s, (y + 0.5) / s):
                        self._put(x, y, ch, only, got)
        return got

    def poly(self, pts, ch, only=None):
        s = self.s
        pts = [(x * s, y * s) for x, y in pts]
        ys = [p[1] for p in pts]
        got = set()
        for y in range(int(min(ys)) - 1, int(max(ys)) + 2):
            py = y + 0.5
            xs = []
            for i in range(len(pts)):
                (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % len(pts)]
                if (y0 <= py < y1) or (y1 <= py < y0):
                    xs.append(x0 + (py - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for a, b in zip(xs[::2], xs[1::2]):
                for x in range(int(math.floor(a)), int(math.ceil(b)) + 1):
                    if a <= x + 0.5 <= b:
                        self._put(x, y, ch, only, got)
        return got

    def px(self, x, y, ch):
        """The whole world pixel, so a 1x stamp keeps its footprint."""
        X, Y = int(math.floor(x)) * self.s, int(math.floor(y)) * self.s
        for dy in range(self.s):
            for dx in range(self.s):
                self._set(X + dx, Y + dy, ch)

    def t(self, x, y, ch, only=None):
        """One native texel."""
        got = set()
        self._put(int(math.floor(x)), int(math.floor(y)), ch, only, got)
        return got

    def stroke(self, pts, ch, only=None):
        """A one-texel line through native points."""
        got = set()
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
            for k in range(n + 1):
                u = k / max(n, 1)
                got |= self.t(x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, ch, only)
        return got

    def T(self, p):
        """World point -> native texel coordinates."""
        return p[0] * self.s, p[1] * self.s

    def outline(self):
        """kaya40.HDCanvas's weighted line: one ink texel all round, a second
        on the shadow side (right and below), so the line is as heavy in world
        units as the 1x line where the form turns away from the light.

        With a `ceiling` (the highest world row the tunnel rule allows) the
        material is trimmed to start one texel under it, so the ink lands on
        that row and not above: a finer raster can put a texel of wing tip
        where the 1x one rounded it away."""
        if self.ceiling is not None:
            for y in range(min(self.h, self.ceiling * self.s + 1)):
                self.g[y] = ['.'] * self.w
        out = [row[:] for row in self.g]
        for y in range(self.h):
            for x in range(self.w):
                if self.g[y][x] != '.':
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if self.get(x + dx, y + dy) not in '.k':
                        out[y][x] = 'k'
                        break
        self.g = out
        out = [row[:] for row in self.g]
        for y in range(self.h):
            for x in range(self.w):
                if self.g[y][x] != '.':
                    continue
                for dx, dy in ((-1, 0), (0, -1)):
                    if (self.get(x + dx, y + dy) == 'k'
                            and self.get(x + 2 * dx, y + 2 * dy) not in '.k'):
                        out[y][x] = 'k'
                        break
        self.g = out


def _canvas(w, h, hd, box=None):
    """A 1x or HD canvas; `box` (ox, oy, w, h) sets the HD ceiling from the
    tunnel rule in the module docstring."""
    if not hd:
        return Canvas(w, h)
    top = None
    if box is not None and box[1] - (TUNNEL - ROUNDING - box[3]) > 0:
        top = box[1] - (TUNNEL - ROUNDING - box[3])
    return HDCanvas(w, h, ceiling=top)


def _is_hd(c):
    return getattr(c, 's', 1) > 1


def texture(c, cells, ch, salt=0, density=6, shadow='d'):
    """Raised bumps over one part: a lit texel with its shadow below-right
    (the light is palette.LIGHT, upper left), scattered at a fixed hash."""
    for (x, y) in sorted(cells):
        if c.get(x, y) != ch or _hash(x, y, salt) % 100 >= density:
            continue
        if c.get(x + 1, y + 1) == ch and c.get(x - 1, y) == ch:
            c.t(x, y, 'l')
            c.t(x + 1, y + 1, shadow)


def contour(c, cells, depth, ch, only, x_range=None, step_skip=0):
    """A line `depth` texels in from the top edge of `cells`, following it:
    a frog's dorsal ridge, a fish's back stripe."""
    cols = {}
    for x, y in cells:
        cols[x] = min(cols.get(x, y), y)
    for x in sorted(cols):
        if x_range and not (x_range[0] <= x <= x_range[1]):
            continue
        if step_skip and x % step_skip == 0:
            continue
        c.t(x, cols[x] + depth, ch, only)


def spot(c, x, y, r=0.9):
    """A frog spot. 1x: one dark pixel. 2x: an irregular blot with a darker
    core and a lit lip on its upper-left, as if the skin is slightly raised."""
    if not _is_hd(c):
        c.px(x, y, 'd')
        return
    got = c.ellipse((x + 0.5, y + 0.5), r, r * 0.8, 'd', only='g',
                    rot=(_hash(int(x * 7), int(y * 5)) % 60) - 30)
    X, Y = int(math.floor(x * c.s)), int(math.floor(y * c.s))
    c.t(X + 1, Y + 1, 'D', only='d')
    for (gx, gy) in sorted(got):
        if c.get(gx - 1, gy - 1) == 'g':
            c.t(gx - 1, gy - 1, 'l')
            break


def bead(c, x, y):
    """One bead of her necklace. 2x: a round bead with a catch-light."""
    if not _is_hd(c):
        c.px(x, y, 'b')
        return
    X, Y = int(math.floor(x * c.s)), int(math.floor(y * c.s))
    for dx, dy, ch in ((0, 0, 'B'), (1, 0, 'b'), (0, 1, 'b'), (1, 1, 'R')):
        c.t(X + dx, Y + dy, ch)


def fan(c, heel, tips, r=0.42, web='f', toe='g', pad='l'):
    """A webbed foot: membrane between the toes, each toe a one-texel rib
    ending in a round pad. World coordinates; `tips` fan out from `heel`."""
    c.poly([heel] + list(tips), web)
    for tp in tips:
        c.capsule(heel, tp, r, toe)
        X, Y = c.T(tp)
        c.t(X, Y, pad)


def ray_fan(c, cells, base, ends, ray, membrane=None, edge_frac=0.62):
    """Fin rays: one-texel lines from `base` to each point of `ends` (world),
    drawn only over the fin's own `cells`; the outer part of the membrane
    between them is lit, so the fin reads thin and translucent at its edge."""
    bx, by = c.T(base)
    far = max(math.hypot(x - bx, y - by) for x, y in cells) if cells else 1.0
    if membrane:
        for (x, y) in cells:
            if math.hypot(x + 0.5 - bx, y + 0.5 - by) > far * edge_frac:
                c.t(x, y, membrane, only=c.get(x, y))
    only = "".join(sorted({c.get(x, y) for x, y in cells}))
    for e in ends:
        ex, ey = c.T(e)
        pts = [(bx, by), (ex, ey)]
        for (x, y) in _line(pts):
            if (x, y) in cells:
                c.t(x, y, ray, only=only)


def _line(pts):
    out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for k in range(n + 1):
            u = k / max(n, 1)
            out.append((int(math.floor(x0 + (x1 - x0) * u)), int(math.floor(y0 + (y1 - y0) * u))))
    return out


def feathers(c, cells, root, tip, sep, covert='l', notch=True, spacing=3):
    """Feather rows over one wing's `cells`. Along the wing from `root` to
    `tip` (world): the inner third is coverts, short scalloped rows with lit
    edges; the rest is flight feathers, split lengthwise every `spacing`
    texels by `sep`; and with `notch` the outer edge is fingered, a texel cut
    between feather tips, so the silhouette only ever loses texels."""
    rx, ry = c.T(root)
    tx, ty = c.T(tip)
    L = math.hypot(tx - rx, ty - ry) or 1.0
    ax, ay = (tx - rx) / L, (ty - ry) / L
    nx, ny = -ay, ax
    own = {}
    for (x, y) in cells:
        own[(x, y)] = c.get(x, y)
    for (x, y), ch in sorted(own.items()):
        if c.get(x, y) != ch:
            continue
        px_, py_ = x + 0.5 - rx, y + 0.5 - ry
        s = (px_ * ax + py_ * ay) / L
        t = px_ * nx + py_ * ny
        if s < 0.34:
            row = int(math.floor(s * L / 2.5))
            if int(math.floor(t + row * 1.5)) % 3 == 0:
                c.t(x, y, covert, only=ch)
        elif int(math.floor(t)) % spacing == 0:
            c.t(x, y, sep, only=ch)
    if notch:
        for (x, y), ch in sorted(own.items()):
            if c.get(x, y) == '.':
                continue
            px_, py_ = x + 0.5 - rx, y + 0.5 - ry
            s = (px_ * ax + py_ * ay) / L
            t = px_ * nx + py_ * ny
            edge = any(c.get(x + dx, y + dy) == '.' for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if edge and s > 0.55 and int(math.floor(t)) % spacing == 0:
                c.t(x, y, '.')


# ------------------------------------------------------------- shared parts
def hat(c, x, y, half=4, tilt=0, under=True):
    """Her straw hat, shrunk to a stamp, because at this size every pixel of it
    is a feature: a two-pixel crown, the dark ribbon, a brim `2*half+1` wide
    with a lit top, and a shadowed underside narrower than the brim. (x, y) is
    the brim's centre pixel. `tilt` 1 cocks the front (+x) end of the brim up a
    pixel and the back end down, the way she tips it."""
    if _is_hd(c):
        return hat_hd(c, x, y, half, tilt, under)
    x, y = int(round(x)), int(round(y))
    for i in range(-half, half + 1):
        dy = 0
        if tilt and i >= half - 1:
            dy = -tilt
        elif tilt and i <= -half + 1:
            dy = tilt
        c._set(x + i, y + dy, 'a')
        if under and abs(i) <= half - 2:
            c._set(x + i, y + 1, 'A')
    for i in range(-2, 2):
        c._set(x + i, y - 1, 'n')
    for i in range(-2, 1):
        c._set(x + i, y - 2, 'a')


def eye(c, x, y, shut=False, lash=True, lid=True):
    """Her eye -- the one feature that survives the change, placed pixel by
    pixel as kaya40 places hers: the lid line, a white and a black pupil
    looking forward, and the lash flicking off the lid. (x, y) is the white."""
    if _is_hd(c):
        return eye_hd(c, x, y, shut, lash, lid)
    x, y = int(round(x)), int(round(y))
    if shut:
        c._set(x, y, 'k')
        c._set(x + 1, y, 'k')
        return
    if lid:
        c._set(x, y - 1, 'k')
        c._set(x + 1, y - 1, 'k')
    if lash:
        c._set(x + 2, y - 2, 'k')
    c._set(x, y, 'w')
    c._set(x + 1, y, 'k')


def hat_hd(c, x, y, half=4, tilt=0, under=True, look=1):
    """`hat()` in native texels, inside the stamp's own footprint: a woven
    crown with a rounded top, the ribbon band with a lit edge and a knot at the
    back, a brim two texels thick whose top is lit along the sunny half and
    weaves on its face, tilting smoothly instead of in one-pixel steps, and a
    one-texel deep underside. `look` -1 mirrors it (the cling faces left)."""
    s = c.s
    x, y = int(round(x)), int(round(y))
    L, R = (x - half) * s, (x + half + 1) * s - 1          # brim, texels
    CX = (x * s + (x + 1) * s - 1) / 2.0
    top = y * s

    def put(tx, ty, ch):
        if look < 0:
            tx = int(2 * CX - tx)
        c.t(tx, ty, ch)
    for X in range(L, R + 1):
        u = (X + 0.5 - CX) / ((R - L + 1) / 2.0)            # -1 .. 1 across
        dy = int(round(-tilt * s * max(0.0, abs(u) - 0.45) / 0.55 * (1 if u > 0 else -1)))
        end = X in (L, R)
        put(X, top + dy, 'x' if u < 0.1 and not end else 'a')
        if not end:
            put(X, top + dy + 1, 'v' if X % 3 == 0 else 'A')
        if under and abs(u) <= (half - 1.5) / (half + 0.5):
            put(X, top + dy + 2, 'V')
    bL, bR = (x - 2) * s, (x + 2) * s - 1                   # band
    for X in range(bL, bR + 1):
        put(X, top - 1, 'n')
        put(X, top - 2, 'N' if X > bL + 1 else 'n')
    put(bL - 1, top - 1, 'n')                               # knot at the back
    put(bL - 1, top, 'n')
    cL, cR = (x - 2) * s, (x + 1) * s - 1                   # crown
    for X in range(cL, cR + 1):
        put(X, top - 3, 'v' if (X + 1) % 3 == 0 else 'a')
        if cL < X < cR:
            put(X, top - 4, 'a' if X % 2 else 'x')


# Her eye at 2x, as kaya40._face_hd draws hers: a lid line, a lash flick, a
# white, an iris with a pupil and a catch-light. Offsets in texels from the
# white's top-left; mirrored for `look` -1.
_EYE_HD = ((0, -1, 'k'), (1, -1, 'k'), (2, -1, 'k'), (3, -1, 'k'), (4, -2, 'k'),
           (0, 0, 'w'), (1, 0, 'e'), (2, 0, 'E'), (3, 0, 'E'),
           (0, 1, 'w'), (1, 1, 'w'), (2, 1, 'e'), (3, 1, 'E'),
           (2, 0, 'w'))
_EYE_SHUT_HD = ((0, 0, 'k'), (1, 1, 'k'), (2, 1, 'k'), (3, 0, 'k'), (4, -1, 'k'))


def eye_hd(c, x, y, shut=False, lash=True, lid=True, look=1):
    s = c.s
    X, Y = int(math.floor(x)) * s, int(math.floor(y)) * s
    for dx, dy, ch in (_EYE_SHUT_HD if shut else _EYE_HD):
        if (dy < 0 and not lid and dx < 4) or (dx == 4 and not lash):
            continue
        c.t(X + dx if look > 0 else X + 3 - dx, Y + dy, ch)


def cells_hd(frames):
    """Light one set of HD frames the way kaya40.render_hd lights her: whole
    ramp steps, a two-texel rim and occlusion, hand-AA on the line. The
    sheet's selective outline runs later, in palette.sheet()."""
    from . import kaya40
    out = []
    for rows in frames:
        img = kaya40.shade_hd(rows, MAT_HD)
        kaya40._hand_aa(img)
        out.append(img)
    return out


def cells_of(frames, w, h):
    return [palette.auto_shade(r, MAT, rate=0.45, lit=0.9, dark=0.8) for r in frames]


# ===================================================================== frog
# Cell 24x16, facing right. The 12x11 hitbox is centred at the bottom: columns
# 6-17, rows 5-15, feet on row 15.
FROG_W, FROG_H = 24, 16
FROG_BOX = (6, 5, 12, 11)          # ox, oy, w, h -- data/forms/frog.json


def _frog(body_dy=0.0, tilt=0.0, puff=0.0, shut=False, tongue=0, hind="sit",
          front="sit", hat_tilt=0, head_dy=0.0, hd=False):
    """A frog in profile, sitting the way a frog sits: rump low over a big
    folded thigh, back sloping up to a head carried high, front legs straight
    under the chin. `body_dy` lowers it all (a crouch), `tilt` rotates the
    body nose-up in degrees, `puff` swells the throat; `hind`/`front` pick the
    leg layout of the beat.

    At 2x: warty skin with a lit dorsal ridge, blotched spots, a tympanum
    behind the eye, folds across the throat, banded thighs, webbed toes with
    pads, round beads, a nostril and the corner of the mouth."""
    c = _canvas(FROG_W, FROG_H, hd, FROG_BOX)
    by = 10.6 + body_dy
    t = math.radians(-tilt)

    def at(x, y):                      # body-space -> cell, about the hip
        dx, dy = x - 9.0, y - by
        return (9.0 + dx * math.cos(t) - dy * math.sin(t),
                by + dx * math.sin(t) + dy * math.cos(t))
    hx, hy = at(16.4, by - 2.2 + head_dy)
    # far legs, in shadow, behind everything
    if front == "sit":
        c.capsule(at(15.2, by + 0.6), (15.0, 15.0), 0.9, 'd')
    if hind == "sit":
        c.capsule((12.0, 15.0), (14.0, 15.0), 0.6, 'd')
    # torso and head
    skin = c.ellipse(at(11.6, by + 0.2), 6.0, 3.6, 'g', rot=-18.0 - tilt)
    skin = (skin or set()) | (c.ellipse((hx, hy), 3.9, 2.7, 'g', rot=-6.0 - tilt * 0.5) or set())
    # her yellow: the throat, and the belly along the bottom
    throat = c.ellipse((hx - 0.4, hy + 2.0 + puff * 0.3), 3.0 + puff * 0.5, 1.3 + puff * 0.7, 'y',
                       clip=lambda px, py: py > hy + 1.0)
    bx, bby = at(11.4, by + 2.6)
    c.ellipse((bx, bby), 4.6, 1.4, 'y', clip=lambda px, py: py > bby - 0.6)
    if hd:
        contour(c, skin, 3, 'l', only='g', x_range=(int(at(6.0, by)[0] * S), int((hx - 1.0) * S)),
                step_skip=5)
        texture(c, skin, 'g', salt=1, density=4)
        for k, (ty) in enumerate(sorted({y for _, y in throat})[1:4:2]):
            for (x, y) in sorted(throat):
                if y == ty and (x + k) % 4 != 0:
                    c.t(x, y, 'q', only='y')
    # spots down the back
    for sx, sy in ((10.0, by - 2.4), (12.6, by - 3.2), (7.4, by - 0.8)):
        spot(c, *at(sx, sy))
    # near hind leg
    if hind == "sit":
        thigh = c.ellipse(at(8.6, by + 1.6), 3.6, 2.6, 'g', rot=-25.0)
        c.capsule((6.0, 13.8), (5.6, 15.0), 0.8, 'g')
        if hd:
            _bands(c, thigh, -25.0)
            fan(c, (8.0, 15.0), ((12.4, 14.2), (13.2, 15.0)), r=0.4)
            c.capsule((5.6, 15.0), (11.4, 15.0), 0.7, 'g')
        else:
            c.capsule((5.6, 15.0), (12.6, 15.0), 0.7, 'g')
        c.px(*at(9.6, by + 0.6), 'd') if not hd else c.stroke(
            [c.T(at(9.0, by + 0.2)), c.T(at(10.4, by + 1.0))], 'd', only='g')   # knee crease
    elif hind == "kick":
        th = c.capsule(at(7.6, by + 0.6), at(3.4, by + 2.4), 1.7, 'g', 1.1)
        c.capsule(at(3.4, by + 2.4), at(0.8, by + 3.6), 1.0, 'g', 0.7)
        if hd:
            _bands(c, th, 20.0 - tilt)
            fan(c, at(0.8, by + 3.6), (at(-0.8, by + 2.6), at(-0.9, by + 3.6), at(-0.4, by + 4.3)))
        else:
            c.capsule(at(0.8, by + 3.6), at(-0.6, by + 3.2), 0.6, 'g')
    elif hind == "tuck":
        thigh = c.ellipse(at(8.8, by + 1.2), 3.6, 2.6, 'g', rot=-25.0)
        c.capsule(at(6.4, by + 3.2), at(11.6, by + 3.6), 0.7, 'g')
        if hd:
            _bands(c, thigh, -25.0)
            fan(c, at(10.4, by + 3.5), (at(12.2, by + 3.0), at(12.4, by + 3.9)), r=0.4)
    elif hind == "trail":
        th = c.capsule(at(7.6, by + 0.8), at(3.6, by + 1.6), 1.6, 'g', 1.0)
        c.capsule(at(3.6, by + 1.6), at(4.6, by + 4.2), 0.9, 'g', 0.7)
        if hd:
            _bands(c, th, 10.0 - tilt)
            fan(c, at(4.4, by + 3.6), (at(3.6, by + 4.6), at(4.6, by + 4.9), at(5.6, by + 4.5)))
    # near front leg
    if front == "sit":
        c.capsule(at(16.2, by + 0.6), (17.2, 14.6), 1.0, 'g', 0.8)
        if hd:
            fan(c, (17.2, 15.0), ((19.4, 14.4), (19.8, 15.1)), r=0.4)
            c.capsule((16.6, 15.0), (18.4, 15.0), 0.6, 'g')
        else:
            c.capsule((16.6, 15.0), (19.6, 15.0), 0.6, 'g')
    elif front == "reach":
        c.capsule(at(16.0, by + 1.0), at(19.6, by + 2.6), 0.9, 'g', 0.7)
        if hd:
            fan(c, at(19.4, by + 2.5), (at(21.4, by + 1.8), at(21.6, by + 2.6), at(21.0, by + 3.2)))
        else:
            c.capsule(at(19.6, by + 2.6), at(21.2, by + 2.4), 0.6, 'g')
    elif front == "down":
        c.capsule(at(16.0, by + 1.0), at(17.4, by + 4.4), 0.9, 'g', 0.7)
        if hd:
            fan(c, at(17.4, by + 4.2), (at(19.0, by + 3.9), at(19.4, by + 4.6)), r=0.4)
        else:
            c.capsule(at(17.0, by + 4.4), at(19.2, by + 4.4), 0.6, 'g')
    # the eye bump on the crown, her eye in it; mouth; beads on the throat
    ebx, eby = hx + 1.2, hy - 1.8
    c.ellipse((ebx, eby), 1.9, 1.6, 'g')
    if hd:                             # tympanum: a ring behind the eye
        c.ellipse((hx - 0.9, hy + 0.1), 1.0, 0.9, 'd', only='gl')
        c.ellipse((hx - 0.9, hy + 0.1), 0.55, 0.5, 'f', only='d')
    eye(c, ebx - 0.6, eby + 0.2, shut=shut)
    c.capsule((hx - 0.4, hy + 1.0), (hx + 3.2, hy + 0.6), 0.3, 'k')
    if hd:
        X, Y = c.T((hx - 0.4, hy + 1.0))
        c.t(X - 1, Y - 1, 'k')                               # the mouth's corner
        nx_, ny_ = c.T((hx + 2.6, hy - 0.5))
        c.t(nx_, ny_, 'D', only='gl')                        # nostril
    for k in range(3):
        bead(c, hx - 1.8 + k * 1.4, hy + 2.3 + puff * 0.8)
    if tongue:
        c.capsule((hx + 3.8, hy + 0.9), (hx + 3.8 + tongue, hy + 1.4), 0.5, 'r')
        if hd:
            c.ellipse((hx + 3.9 + tongue, hy + 1.45), 0.75, 0.65, 'r')
            X, Y = c.T((hx + 3.6 + tongue, hy + 1.1))
            c.t(X, Y, 'B')
    # the hat, on the back of the head behind the eye bump
    hat(c, hx - 3.4, hy - 2.4, half=3, tilt=hat_tilt)
    c.outline()
    return c.rows()


def _bands(c, cells, rot):
    """Bands across a frog's thigh, as on a real tree frog: stripes at right
    angles to the bone, two texels wide every six, a step darker than the skin
    and only on the lower half of the leg, where the back does not cover it."""
    if not cells:
        return
    a = math.radians(rot)
    ux, uy = math.cos(a), math.sin(a)
    mid = sum(y for _, y in cells) / len(cells)
    for (x, y) in sorted(cells):
        u = (x + 0.5) * ux + (y + 0.5) * uy
        if y >= mid - 1 and int(math.floor(u)) % 6 in (0, 1) and c.get(x, y) == 'g':
            c.t(x, y, 'G')


# The cling, placed pixel by pixel: twelve columns is the hitbox's width, and at
# that size the eye, the brim and the toes on the rock each need a pixel chosen
# rather than rasterised. Columns 0-11 here are cell columns 6-17.
_CLING = [
    "....kkk.....",
    "...kaaak....",
    "..knnnnnk...",
    ".kaaaaaaak..",
    "kgkwAAAggk..",
    "kgggggggggkk",
    ".kkkkgggdggk",
    "..kbybygggk.",
    "..kyyyyggdgk",
    "..kyyyyyggkk",
    "..kyyyyygggk",
    "...kyyyyggk.",
    "...kyyygggkk",
    "....kkkkkkk.",
]


def _frog_cling(breathe=0, hd=False):
    """Stuck to a wall in mid-air. The game draws this beat with the frame's
    FRONT to the wall -- the render facing still points the way she leapt; the
    clip gate's tapes show it at both walls, flipped and not -- so the toes are
    on the right-hand edge and the head is turned back over the shoulder to look
    out along the wall. Every pixel, ink included, is inside the hitbox's
    columns: the wall is flush with the hitbox, and should the facing ever catch
    up mid-cling the other side would be the wall. `breathe` swells the belly."""
    if hd:
        return _frog_cling_hd(breathe)
    rows = [r[:] for r in _CLING]
    if breathe:
        rows[7] = "..kbybyyggk."
        rows[11] = "...kyyyyygk."
    ox = FROG_BOX[0]
    top = FROG_H - len(rows)
    out = ['.' * FROG_W for _ in range(top)]
    for r in rows:
        out.append('.' * ox + r + '.' * (FROG_W - ox - len(r)))
    return out


def _frog_cling_hd(breathe=0):
    """The cling at 2x, from shapes rather than the 1x grid, laid out as the
    grid lays it out (hat on top, the eye looking out to the left, her yellow
    belly to the room, the green back and the toes against the wall on the
    right) and held two texels inside the hitbox's columns so the weighted
    line is inside them too."""
    c = _canvas(FROG_W, FROG_H, True, FROG_BOX)
    lo, hi = FROG_BOX[0] + 0.55, FROG_BOX[0] + FROG_BOX[2] - 1.05   # material, world x
    clip = lambda x, y: lo <= x <= hi                             # noqa: E731
    # the hind leg folded up against the wall, under the body
    thigh = c.ellipse((14.6, 13.4), 2.5, 2.1, 'g', clip=clip)
    _bands(c, thigh, 70.0)
    body = c.ellipse((12.2, 11.4), 4.4, 3.9, 'g', clip=clip)
    c.ellipse((11.0, 12.0 + breathe * 0.2), 3.3 + breathe * 0.35, 3.3, 'y',
              clip=lambda x, y: clip(x, y) and x < 13.4 + breathe * 0.3)
    head = c.ellipse((11.6, 7.8), 4.4, 2.0, 'g', clip=clip)
    c.ellipse((9.2, 7.0), 1.8, 1.5, 'g', clip=clip)              # the eye bump
    texture(c, body | head, 'g', salt=3, density=4)
    c.ellipse((13.8, 7.8), 0.9, 0.8, 'd', only='gl')             # tympanum
    c.ellipse((13.8, 7.8), 0.45, 0.4, 'f', only='d')
    spot(c, 14.6, 10.4)
    spot(c, 15.2, 12.0, r=0.7)
    c.stroke([c.T((7.6, 8.7)), c.T((12.0, 9.1))], 'k')           # mouth
    for k in range(3):
        bead(c, 8.2 + k * 1.3, 9.4 + (0.3 if k == 1 else 0.0))
    for k in range(2):                                           # throat folds
        Y = int((10.8 + k * 1.2) * S)
        for X in range(int(8.2 * S), int(12.4 * S)):
            if (X + k) % 4:
                c.t(X, Y, 'q', only='y')
    # toes against the wall: three splayed pads at the right edge
    for ty in (8.6, 11.0, 14.6):
        fan(c, (hi - 1.6, ty), ((hi - 0.1, ty - 0.6), (hi - 0.1, ty + 0.5)), r=0.38)
    c.capsule((13.2, 9.6), (hi - 1.4, 8.8), 0.7, 'g')            # the arm up to them
    eye_hd(c, 8.6, 7.0, look=-1)
    hat_hd(c, 11.6, 5.0, half=3, look=-1)
    c.outline()
    return c.rows()


def _frog_shaft(stretch=False, hd=False):
    """The frog in a one-tile shaft, where a 16 px gap holds a 12 px hitbox and
    no sideways nudge can clear the leap's legs: drawn from behind and a little
    above, climbing -- legs folded under (or pushed straight down mid-kick),
    arms up, the hat on the back of the head. At most `NARROW_W` px wide, the
    same answer kaya40 gives her with the slung hat."""
    c = _canvas(FROG_W, FROG_H, hd, FROG_BOX)
    cx = 12.0
    top = 7.2 if stretch else 8.4
    back = c.ellipse((cx, 11.0 + (0 if stretch else 0.6)), 4.2, 3.6 if not stretch else 4.0, 'g')
    if hd:
        texture(c, back, 'g', salt=5, density=4)
        c.stroke([c.T((cx - 1.6, 8.6)), c.T((cx - 2.2, 13.4))], 'l', only='g')   # dorsal ridges
        c.stroke([c.T((cx + 1.6, 8.6)), c.T((cx + 2.2, 13.4))], 'l', only='g')
    if stretch:                                   # kicked down, toes splayed
        for sgn in (-1, 1):
            leg = c.capsule((cx + sgn * 2.4, 13.0), (cx + sgn * 3.4, 15.0), 1.0, 'g', 0.7)
            arm = c.capsule((cx + sgn * 3.0, 9.0), (cx + sgn * 5.0, 5.6), 0.8, 'g', 0.6)
            if hd:
                _bands(c, leg, 60.0 * sgn)
                fan(c, (cx + sgn * 4.6, 6.4), ((cx + sgn * 4.4, 4.9), (cx + sgn * 5.5, 5.0)),
                    r=0.38)
                fan(c, (cx + sgn * 3.3, 14.6), ((cx + sgn * 2.7, 15.4), (cx + sgn * 4.2, 15.4)),
                    r=0.38)
    else:                                         # folded, a ball on the wall-kick
        for sgn in (-1, 1):
            th = c.ellipse((cx + sgn * 3.6, 13.2), 2.2, 1.8, 'g')
            c.capsule((cx + sgn * 3.4, 15.0), (cx + sgn * 1.4, 15.0), 0.6, 'g')
            c.capsule((cx + sgn * 3.4, 10.0), (cx + sgn * 5.2, 8.0), 0.8, 'g', 0.6)
            if hd:
                _bands(c, th, 75.0 * sgn)
                fan(c, (cx + sgn * 4.8, 8.6), ((cx + sgn * 4.7, 7.3), (cx + sgn * 5.7, 7.6)),
                    r=0.38)
    for sx, sy in ((cx - 1.6, 11.0), (cx + 1.4, 12.4), (cx - 0.2, 13.6)):
        spot(c, sx, sy)                           # spots down the back
    head = c.ellipse((cx, top), 3.0, 2.2, 'g')    # head, from behind
    c.ellipse((cx - 2.2, top - 1.6), 1.4, 1.2, 'g')
    c.ellipse((cx + 2.2, top - 1.6), 1.4, 1.2, 'g')   # the two eye bumps
    if hd:
        texture(c, head, 'g', salt=6, density=4)
        for sgn in (-1, 1):                       # the eyes' backs catch the light
            X, Y = c.T((cx + sgn * 2.2 - 0.4, top - 2.2))
            c.t(X, Y, 'l')
            c.t(X + 1, Y, 'l')
    bead(c, cx - 1.0, top + 1.6)
    bead(c, cx + 0.6, top + 1.8)                  # the necklace's clasp
    hat(c, cx, top - 0.4, half=3, under=False)
    c.outline()
    return c.rows()


def frog_frames(hd=False):
    """0 idle, 1 breathe, 2 crouch (also the turn frame), 3 leap (also the
    wall-kick flash), 4 reach, 5 cling, 6 apex tuck, 7 tongue-blink idle,
    8 cling breathe, 9 shaft leap, 10 shaft tuck -- the order
    data/forms/frog.json indexes."""
    return [
        _frog(hd=hd),
        _frog(puff=1.0, hd=hd),
        _frog(body_dy=1.2, tilt=-6.0, head_dy=0.6, hd=hd),
        _frog(body_dy=-0.2, tilt=14.0, hind="kick", front="reach", hat_tilt=1, hd=hd),
        _frog(body_dy=-0.6, tilt=-14.0, hind="trail", front="down", hd=hd),
        _frog_cling(hd=hd),
        _frog(body_dy=-0.6, tilt=6.0, hind="tuck", front="down", hd=hd),
        _frog(shut=True, tongue=2, hd=hd),
        _frog_cling(breathe=1.0, hd=hd),
        _frog_shaft(stretch=True, hd=hd),
        _frog_shaft(hd=hd),
    ]


FROG_CLING = (5, 8)
# Frames for a one-tile shaft (added after the original nine, so every index
# frog.json already used still means what it meant).
FROG_NARROW = (9, 10)
NARROW_W = 16


# ===================================================================== fish
# Cell 24x14, facing right. The 14x9 hitbox: columns 5-18, rows 5-13.
FISH_W, FISH_H = 24, 14
FISH_BOX = (5, 5, 14, 9)


def _fish(tail=0.0, mouth=0.0, tilt=0.0, fin=0.0, flop=False, hd=False):
    """`tail` -1..1 swings the tail fan down..up; `mouth` opens the bite;
    `tilt` rotates the body (degrees, nose up positive).

    At 2x: overlapping scales on the yellow flank, a lateral line, rays in
    every fin with a lit, thin outer edge, a gill cover with her beads on it,
    a lip, and teeth in the bite."""
    c = _canvas(FISH_W, FISH_H, hd, FISH_BOX)
    cx, cy = 12.0, 9.6
    t = math.radians(-tilt)

    def rot(x, y):
        dx, dy = x - cx, y - cy
        return (cx + dx * math.cos(t) - dy * math.sin(t),
                cy + dx * math.sin(t) + dy * math.cos(t))
    # tail fan: green, the base at the peduncle, two lobes
    base = rot(5.0, cy)
    tip_u = rot(1.0, cy - 3.6 - tail * 1.4)
    tip_d = rot(1.0, cy + 3.0 - tail * 1.4)
    notch = rot(2.6, cy - tail * 1.2)
    tail_px = c.poly([base, tip_u, notch, tip_d], 'G')
    # dorsal fin (green, her top) and the far pectoral
    d0, d1, d2 = rot(8.6, cy - 3.4), rot(11.6, cy - 6.6 - fin), rot(14.0, cy - 3.6)
    dorsal = c.poly([d0, d1, d2], 'G')
    if hd:
        ends = [(tip_u[0] + (notch[0] - tip_u[0]) * k / 3.0,
                 tip_u[1] + (notch[1] - tip_u[1]) * k / 3.0) for k in range(4)]
        ends += [(notch[0] + (tip_d[0] - notch[0]) * k / 3.0,
                  notch[1] + (tip_d[1] - notch[1]) * k / 3.0) for k in range(1, 4)]
        ray_fan(c, tail_px, rot(5.6, cy), ends, 'F', membrane='g')
        ray_fan(c, dorsal, rot(11.2, cy - 2.0),
                [(d0[0] + (d1[0] - d0[0]) * k / 3.0, d0[1] + (d1[1] - d0[1]) * k / 3.0)
                 for k in range(1, 4)]
                + [(d1[0] + (d2[0] - d1[0]) * k / 3.0, d1[1] + (d2[1] - d1[1]) * k / 3.0)
                   for k in range(1, 3)], 'F', membrane='g', edge_frac=0.7)
    # body: yellow, nose to the right
    flank = c.ellipse((cx, cy), 7.4, 3.7, 'Y', rot=-tilt)
    c.ellipse(rot(13.0, cy + 1.6), 5.4, 1.8, 'y', rot=-tilt)      # belly
    back = c.ellipse(rot(11.0, cy - 2.4), 5.6, 1.4, 'g', rot=-tilt)      # green back
    if hd:
        _scales(c, flank, rot, cx, cy, t, nose=14.6)
        texture(c, back, 'g', salt=7, density=5)
        for k in range(14):                                       # lateral line
            X, Y = c.T(rot(5.8 + k * 0.62, cy - 0.5 - 0.35 * math.sin(k * 0.45)))
            c.t(X, Y, 'o' if k % 2 else 'Q', only='Yoq')
    # gill line, her beads along it
    if hd:
        for k in range(9):                                        # the gill cover
            a = -1.15 + k * 0.29
            X, Y = c.T(rot(15.6 - 1.4 * math.cos(a) + 0.4, cy + 2.6 * math.sin(a)))
            c.t(X, Y, 'q', only='Yyg')
            c.t(X + 1, Y, 'Q', only='Yy')
    for k, gy in enumerate((-1.6, 0.2, 2.0)):
        gx, gy2 = rot(15.2 - abs(gy) * 0.3, cy + gy)
        if hd:
            bead(c, gx, gy2) if k != 1 else c.t(*c.T((gx, gy2)), 'R')
        else:
            c.px(gx, gy2, 'b' if k != 1 else 'R')
    # near pectoral fin
    p0, p1 = rot(13.0, cy + 1.0), rot(10.2 + fin * 0.6, cy + 3.0)
    pect = c.capsule(p0, p1, 0.9, 'g', 0.6)
    if hd:
        c.ellipse(p1, 0.9, 0.7, 'g')
        ray_fan(c, pect, p0, [(p1[0] + dx, p1[1] + dy) for dx, dy in
                              ((-0.8, -0.6), (-1.0, 0.2), (-0.4, 0.9))], 'G', membrane='f',
                edge_frac=0.45)
    # eye and mouth
    ex, ey = rot(16.4, cy - 0.8)
    if hd:                                                    # the eye's socket
        c.ellipse((math.floor(ex) + 1.0, math.floor(ey) + 0.6), 1.3, 1.15, 'q', only='Yy')
    eye(c, ex, ey, shut=flop)
    if mouth > 0:
        m0 = rot(19.4, cy + 0.4)
        c.capsule(m0, rot(16.6, cy + 0.9), 0.4, 'k')
        c.poly([rot(17.4, cy + 0.6), rot(20.2, cy - 0.8 - mouth),
                rot(20.2, cy + 1.6 + mouth * 0.6)], '.')
        c.px(*rot(18.6, cy + 1.6), 'r')
        if hd:                                                # teeth on both jaws
            for p in (rot(19.2, cy - 0.1), rot(18.4, cy + 0.3), rot(19.0, cy + 1.6)):
                X, Y = c.T(p)
                c.t(X, Y, 'W')
            X, Y = c.T(rot(18.2, cy + 1.2))
            c.t(X, Y, 'm')
    else:
        c.capsule(rot(18.6, cy + 1.0), rot(17.4, cy + 1.2), 0.3, 'k')
        if hd:                                                # the lip
            X, Y = c.T(rot(18.9, cy + 0.5))
            c.t(X, Y, 'Q', only='Yy')
    # the hat rides on the head, just behind the eye
    hx, hy = rot(14.0, cy - 3.6)
    hat(c, hx, hy, half=3, tilt=1 if tilt > 2 else 0)
    c.outline()
    return c.rows()


def _scales(c, cells, rot, cx, cy, t, nose):
    """Scales over the flank: staggered rows of small cupped arcs, in fish
    space so they turn with the body. Not on the head (body-space x past
    `nose`); on the paler belly only a faint stitch every other row."""
    ct, st = math.cos(-t), math.sin(-t)
    for (x, y) in sorted(cells):
        here = c.get(x, y)
        if here not in 'Yy':
            continue
        wx, wy = (x + 0.5) / c.s - cx, (y + 0.5) / c.s - cy
        u = wx * ct - wy * st + cx                     # undo the tilt
        v = wx * st + wy * ct
        if u > nose - abs(v) * 0.3:
            continue
        U, V = u * c.s, v * c.s
        row = int(math.floor(V / 3.0))
        a = (U + (row % 2) * 2.5) % 5.0
        b = V - row * 3.0
        if here == 'Y' and ((b >= 2.0 and 1.0 <= a < 4.0) or (b < 2.0 and a < 1.0)):
            c.t(x, y, 'o')
        elif here == 'y' and b >= 2.0 and 2.0 <= a < 3.0 and row % 2:
            c.t(x, y, 'q')


def _fish_shaft(curl=0.0, hd=False):
    """The fish in a one-tile shaft: bent into a C with the tail swept up over
    its back, so it fits 16 px with its hat on. `curl` flicks the tail."""
    c = _canvas(FISH_W, FISH_H, hd, FISH_BOX)
    cx, cy = 12.0, 9.8
    tail_pts = [(8.0, cy - 1.0), (6.2 - curl, 4.0), (9.6, 6.0 + curl), (11.0, 3.2 - curl * 0.6)]
    tl = c.poly(tail_pts, 'G')                               # tail, up over the back
    if hd:
        ray_fan(c, tl, (8.4, cy - 1.4), [tail_pts[1], (8.0, 5.0 + curl * 0.5), tail_pts[2],
                                         (10.2, 4.6), tail_pts[3]], 'F', membrane='g')
    flank = c.ellipse((cx, cy), 5.6, 3.6, 'Y')
    c.ellipse((cx + 1.2, cy + 1.6), 4.0, 1.7, 'y')
    back = c.ellipse((cx - 0.6, cy - 2.2), 4.0, 1.3, 'g')
    pect = c.capsule((cx + 1.4, cy + 1.0), (cx - 1.0, cy + 2.8), 0.8, 'g', 0.6)
    if hd:
        _scales(c, flank, lambda x, y: (x, y), cx, cy, 0.0, nose=cx + 2.4)
        texture(c, back, 'g', salt=8, density=5)
        ray_fan(c, pect, (cx + 1.4, cy + 1.0), [(cx - 1.6, cy + 2.4), (cx - 1.2, cy + 3.3)],
                'G', membrane='f')
        for k in range(7):
            a = -1.1 + k * 0.36
            X, Y = c.T((cx + 3.4 - 1.2 * math.cos(a), cy + 2.4 * math.sin(a)))
            c.t(X, Y, 'q', only='Yyg')
    bead(c, cx + 3.0, cy - 1.0)
    bead(c, cx + 3.0, cy + 1.4)
    if hd:
        c.ellipse((cx + 4.6, cy - 0.0), 1.3, 1.15, 'q', only='Yy')
    eye(c, cx + 3.6, cy - 0.6)
    c.capsule((cx + 5.0, cy + 1.0), (cx + 4.2, cy + 1.2), 0.3, 'k')
    hat(c, cx + 2.0, cy - 4.0, half=3)
    c.outline()
    return c.rows()


def fish_frames(hd=False):
    """0-3 the swim beat (tail mid, up, mid, down), 4 bite, 5 flop, 6-7 the
    curled shaft swim -- the order data/forms/fish.json indexes. Facing right, which `facing == 1`
    draws."""
    return [
        _fish(tail=0.0, hd=hd),
        _fish(tail=1.0, fin=0.6, hd=hd),
        _fish(tail=0.2, fin=0.3, hd=hd),
        _fish(tail=-1.0, fin=-0.4, hd=hd),
        _fish(mouth=1.0, tail=-0.4, tilt=4.0, hd=hd),
        _fish(tail=1.0, tilt=-10.0, flop=True, hd=hd),
        _fish_shaft(hd=hd),
        _fish_shaft(curl=1.0, hd=hd),
    ]


FISH_NARROW = (6, 7)


# ===================================================================== bird
# Cell 24x16, facing right. The 12x9 hitbox: columns 6-17, rows 7-15.
BIRD_W, BIRD_H = 24, 16
BIRD_BOX = (6, 7, 12, 9)


def _bird(wing="fold", feet="perch", tail_dy=0.0, head_dx=0.0, head_dy=0.0,
          body_dy=0.0, tilt_head=0.0, ruffle=False, bank=0, hd=False):
    """At 2x: the tail plumes as strands of her hair with a sheen and a
    groove, feather rows on every wing (scalloped coverts, split flight
    feathers, fingered tips), soft chevrons on the breast and back, a two-part
    beak with a lit ridge, a nostril and a hooked tip, and scaled red legs
    with toes and claws."""
    c = _canvas(BIRD_W, BIRD_H, hd, BIRD_BOX)
    by = 11.4 + body_dy
    hx, hy = 16.4 + head_dx, 8.0 + head_dy + body_dy
    # tail: her long dark hair, three plumes swept back
    for k, (dy, ln) in enumerate(((-0.6, 7.0), (0.6, 7.8), (1.6, 6.2))):
        a = (9.0, by + dy * 0.5)
        b = (9.0 - ln, by + 1.2 + dy + tail_dy)
        plume = c.capsule(a, b, 1.1 if k == 1 else 0.9, 'H' if k != 1 else 'h', 0.6)
        if hd:
            _plume(c, plume, a, b, 'H' if k != 1 else 'h')
    # far wing behind the body
    if wing in ("up", "mid_up"):
        tip = (8.0, 1.2) if wing == "up" else (5.6, 5.0)
        far = c.poly([(10.0, by - 2.0), tip, (13.6, by - 2.6)], 'G')
        if hd:
            feathers(c, far, (11.6, by - 2.4), tip, 'F', covert='g')
    # feet: the sandals' red
    if feet == "perch":
        legs = c.capsule((11.2, by + 2.4), (11.0, 15.0), 0.6, 'r') or set()
        legs |= c.capsule((13.4, by + 2.4), (13.6, 15.0), 0.6, 'R') or set()
        if hd:
            _scutes(c, legs)
            _toes(c, (11.0, 15.0), 'r')
            _toes(c, (13.6, 15.0), 'R')
        else:
            c.capsule((10.4, 15.0), (12.4, 15.0), 0.5, 'r')
            c.capsule((13.2, 15.0), (15.0, 15.0), 0.5, 'R')
    elif feet == "tuck":
        c.capsule((11.6, by + 3.0), (9.8, by + 3.6), 0.6, 'r')
        if hd:
            X, Y = c.T((9.6, by + 3.5))
            c.t(X, Y, 'K')
            c.t(X, Y + 1, 'K')
    # body: green, yellow breast
    body = c.ellipse((12.0, by), 5.0, 3.4, 'g', rot=-12.0)
    breast = c.ellipse((14.0, by + 1.2), 3.0, 2.2, 'y', rot=-20.0)
    if hd:
        _chevrons(c, body, 'g', 'G', 4, 3)
        _chevrons(c, breast, 'y', 'q', 3, 3, off=1)
    # head
    head = c.ellipse((hx, hy), 2.9, 2.7, 'g')
    c.ellipse((hx + 0.6, hy + 1.8), 1.8, 1.0, 'y', clip=lambda px, py: py > hy + 1.0)
    if hd:
        texture(c, head, 'g', salt=11, density=4, shadow='G')
    # beak: straw, short and hooked
    beak = c.poly([(hx + 2.4, hy - 0.4), (hx + 5.0, hy + 0.6 + tilt_head * 0.3),
                   (hx + 2.4, hy + 1.6)], 'a')
    c.px(hx + 3.0, hy + 0.8, 'A')
    if hd:
        _beak(c, beak, hx, hy, tilt_head)
    eye(c, hx + 0.6, hy - 0.2)
    bead(c, hx - 0.6, hy + 1.8)
    bead(c, hx + 0.6, hy + 2.6)                                    # necklace
    # near wing
    if wing == "fold":
        w = c.ellipse((10.8, by - 0.6), 4.0, 2.0, 'G', rot=-10.0)
        c.capsule((7.6, by + 0.2), (12.8, by - 1.8), 0.5, 'g')
        if hd:
            feathers(c, w, (13.6, by - 1.2), (6.8, by + 0.2), 'F', covert='g', notch=False)
        if ruffle:
            c.px(9.0, by - 1.6, 'g')
    elif wing == "up":
        w = c.poly([(9.0, by - 1.0), (6.4, 1.0), (9.0, 2.4), (13.4, by - 2.2)], 'g')
        c.capsule((9.2, 2.6), (12.0, by - 2.2), 0.4, 'G')
        if hd:
            feathers(c, w, (11.4, by - 1.6), (7.2, 1.4), 'D')
    elif wing == "mid_up":
        w = c.poly([(8.6, by - 0.8), (2.4, 4.4), (5.4, 6.6), (13.2, by - 1.8)], 'g')
        c.capsule((3.4, 5.4), (10.0, by - 1.2), 0.4, 'G')
        if hd:
            feathers(c, w, (11.0, by - 1.3), (3.0, 5.0), 'D')
    elif wing == "down":
        w = c.poly([(9.0, by - 1.4), (13.6, by - 2.2), (11.6, 15.0), (8.4, 14.2)], 'g')
        c.capsule((9.6, by), (9.4, 14.0), 0.4, 'G')
        if hd:
            feathers(c, w, (11.2, by - 1.8), (10.0, 14.6), 'D')
    elif wing == "mid_down":
        w = c.poly([(8.6, by - 1.2), (13.4, by - 2.0), (5.0, 14.4), (2.6, 12.2)], 'g')
        c.capsule((9.0, by), (4.0, 13.2), 0.4, 'G')
        if hd:
            feathers(c, w, (11.0, by - 1.6), (3.8, 13.4), 'D')
    elif wing == "glide":
        # spread, seen edge-on from the side: a long flat blade over the back
        w = c.poly([(7.0, by - 1.4), (1.6, by - 3.6 - (0.8 if ruffle else 0.0)),
                    (4.0, by - 0.6), (13.6, by - 1.2)], 'g')
        w2 = c.poly([(11.0, by - 2.2), (20.6, by - 4.4), (15.0, by - 0.8)], 'G')
        if hd:
            feathers(c, w, (12.0, by - 1.2), (1.8, by - 3.4), 'D', spacing=2)
            feathers(c, w2, (12.0, by - 1.8), (20.2, by - 4.2), 'F', covert='g', spacing=2)
        if ruffle:
            c.px(3.0, by - 2.0, 'G')
    elif wing == "bank":
        # banking: the near wing swept down toward us, the far one high
        w2 = c.poly([(9.4, by - 1.6), (8.4, 1.6 + bank), (12.6, by - 2.6)], 'G')
        w = c.poly([(10.0, by), (15.0, by - 1.0), (18.6, 14.0 - bank), (12.0, 14.2)], 'g')
        if hd:
            feathers(c, w2, (11.0, by - 2.0), (8.6, 2.0 + bank), 'F', covert='g')
            feathers(c, w, (12.4, by - 0.4), (16.4, 14.0 - bank * 0.5), 'D')
    hat(c, hx - 1.4, hy - 2.6, half=3, tilt=1 if tilt_head else 0)
    c.outline()
    return c.rows()


def _plume(c, cells, a, b, ch):
    """A tail plume as a lock of her hair: a groove down the middle and a
    sheen along the upper edge, as kaya40._hair_strands does for her."""
    (ax, ay), (bx, by) = c.T(a), c.T(b)
    c.stroke([(ax - 2, ay + 0.5), (bx + 1, by)], 'j', only=ch)
    for (x, y) in sorted(cells):
        if c.get(x, y) == ch and c.get(x, y - 1) not in (ch, 'j', 'i') and x % 3:
            c.t(x, y + 1, 'i', only=ch)


def _chevrons(c, cells, ch, mark, w, h, off=0):
    """Soft feather chevrons over a body part: a small V every `w` texels in
    staggered rows `h` apart, a single ramp step from the ground."""
    for (x, y) in sorted(cells):
        if c.get(x, y) != ch:
            continue
        row = (y + off) // h
        a = (x + (row % 2) * (w // 2)) % w
        if (y + off) % h == h - 1 and a == 1 or (y + off) % h == h - 2 and a in (0, 2):
            c.t(x, y, mark)


def _beak(c, cells, hx, hy, tilt_head):
    """Upper mandible lit along its ridge, a short gape line toward the tip,
    a nostril, and a hooked tip one step darker."""
    top = {}
    for (x, y) in cells:
        top[x] = min(top.get(x, y), y)
    xs = sorted(top)
    if not xs:
        return
    X1, Y1 = c.T((hx + 4.2, hy + 0.7 + tilt_head * 0.3))
    for (x, y) in sorted(cells):
        if y < Y1:
            c.t(x, y, 'P', only='aA')
    for x in xs[:-1]:
        c.t(x, top[x], 'x', only='aP')
    c.stroke([(X1 - 3, Y1 - 0.4), (X1, Y1)], 'V', only='aA')           # gape
    c.t(xs[-1], top[xs[-1]], 'A', only='ax')                          # the hook
    nx_, ny_ = c.T((hx + 2.9, hy - 0.1))
    c.t(nx_, ny_ + 1, 'K', only='ax')                                 # nostril


def _scutes(c, cells):
    """Scales down a bird's leg: every other texel row a step darker."""
    for (x, y) in sorted(cells):
        if y % 2 == 0 and c.get(x, y) == 'r':
            c.t(x, y, 'R')


def _toes(c, foot, ch):
    """Two toes forward, one back, a dark claw on each, gripping the perch
    along the hitbox's bottom row."""
    fx, fy = foot
    c.capsule((fx - 0.2, fy), (fx + 1.6, fy), 0.45, ch)
    c.capsule((fx - 0.2, fy), (fx - 1.0, fy), 0.45, ch)
    X, Y = c.T((fx + 1.6, fy))
    c.t(X + 1, Y, 'K')
    c.t(X + 1, Y - 1, 'K')
    X, Y = c.T((fx - 1.0, fy))
    c.t(X - 1, Y, 'K')


def bird_frames(hd=False):
    """0-3 the flap beat (up, mid, down, mid), 4 glide, 5 perch, 6 glide ruffle,
    7 perch head-tilt, 8-9 the banking turn pair -- the order data/forms/bird.json
    indexes."""
    return [
        _bird(wing="up", feet="tuck", tail_dy=-0.6, hd=hd),
        _bird(wing="mid_up", feet="tuck", hd=hd),
        _bird(wing="down", feet="tuck", tail_dy=0.8, body_dy=-1.0, hd=hd),
        _bird(wing="mid_down", feet="tuck", tail_dy=0.4, body_dy=-0.6, hd=hd),
        _bird(wing="glide", feet="tuck", body_dy=-0.4, hd=hd),
        _bird(hd=hd),
        _bird(wing="glide", feet="tuck", body_dy=-0.4, tail_dy=0.6, ruffle=True, hd=hd),
        _bird(head_dy=0.6, head_dx=-0.4, tilt_head=1.0, ruffle=True, hd=hd),
        _bird(wing="bank", feet="tuck", bank=0, hd=hd),
        _bird(wing="bank", feet="tuck", bank=2, head_dx=-0.6, tail_dy=0.6, hd=hd),
    ]


# ================================================================== checks
def _opaque(rows):
    return [(x, y) for y, r in enumerate(rows) for x, ch in enumerate(r) if ch != '.']


def check(name, frames, box, wall_frames=(), narrow=()):
    """The rules in the module docstring, on the ASCII before lighting."""
    ox, oy, bw, bh = box
    max_rise = TUNNEL - ROUNDING - bh
    for i, rows in enumerate(frames):
        pts = _opaque(rows)
        assert pts, "%s frame %d is empty" % (name, i)
        bottom = max(y for _, y in pts)
        top = min(y for _, y in pts)
        assert bottom <= oy + bh - 1, "%s frame %d draws below its hitbox (row %d)" % (
            name, i, bottom)
        assert oy - top <= max_rise, "%s frame %d rises %d px, max %d" % (
            name, i, oy - top, max_rise)
    for i in wall_frames:
        xs = [x for x, _ in _opaque(frames[i])]
        assert min(xs) >= ox and max(xs) <= ox + bw - 1, (
            "%s cling frame %d leaves the hitbox columns (%d..%d)" % (name, i, min(xs), max(xs)))
    for i in narrow:
        xs = [x for x, _ in _opaque(frames[i])]
        assert max(xs) - min(xs) + 1 <= NARROW_W, "%s narrow frame %d is %d px wide" % (
            name, i, max(xs) - min(xs) + 1)


def world_mask(rows, s=S):
    """HD rows as the 1x rows the rules are written for: a world unit is drawn
    if ANY of its texels is -- the same reading tools/clipgate/clipgate.gd and
    KayaPose.bounds() take of a 2x sheet."""
    h, w = len(rows) // s, len(rows[0]) // s
    return ["".join('k' if any(rows[y * s + dy][x * s + dx] != '.'
                               for dy in range(s) for dx in range(s)) else '.'
                    for x in range(w)) for y in range(h)]


def check_hd(name, frames, box, wall_frames=(), narrow=()):
    check(name, [world_mask(f) for f in frames], box, wall_frames, narrow)


def frames_frog():
    f = frog_frames()
    check("frog", f, FROG_BOX, FROG_CLING, FROG_NARROW)
    return f


def frames_fish():
    f = fish_frames()
    check("fish", f, FISH_BOX, (), FISH_NARROW)
    return f


def frames_bird():
    f = bird_frames()
    check("bird", f, BIRD_BOX)
    return f


def frog_cells():
    return cells_of(frames_frog(), FROG_W, FROG_H)


def frog_cells_hd():
    f = frog_frames(hd=True)
    check_hd("frog", f, FROG_BOX, FROG_CLING, FROG_NARROW)
    return cells_hd(f)


def fish_cells():
    return cells_of(frames_fish(), FISH_W, FISH_H)


def fish_cells_hd():
    f = fish_frames(hd=True)
    check_hd("fish", f, FISH_BOX, (), FISH_NARROW)
    return cells_hd(f)


def bird_cells():
    return cells_of(frames_bird(), BIRD_W, BIRD_H)


def bird_cells_hd():
    f = bird_frames(hd=True)
    check_hd("bird", f, BIRD_BOX)
    return cells_hd(f)


def write_bounds(sheet_path, w, h):
    """Per frame, per row, the first and last opaque column of the SHIPPED sheet
    -- the same file kaya40.write_bounds() writes for her, read by
    src/player/kaya_pose.gd through the form's `pose.bounds`. `w`x`h` is the
    frame in world units; a sheet drawn at k texels per unit is measured in
    texels and says `"scale": k`, which KayaPose.bounds() folds back into world
    rows (a unit is drawn if any of its texels is, as the clip gate reads it)."""
    img = Image.open(sheet_path).convert("RGBA")
    k = img.height // h
    tw, th = w * k, h * k
    out_frames = []
    for f in range(img.width // tw):
        rows = []
        for y in range(th):
            xs = [x for x in range(tw) if img.getpixel((f * tw + x, y))[3] > 0]
            rows.append([xs[0], xs[-1]] if xs else [-1, -1])
        out_frames.append(rows)
    name = os.path.basename(sheet_path)
    out = {"_comment": "Generated by tools/art/forms40.py from %s. Do not edit." % name,
           "frame_w": w, "frame_h": h}
    if k > 1:
        out["scale"] = k
    out["rows"] = out_frames
    path = os.path.splitext(sheet_path)[0] + ".bounds.json"
    with open(path, "w") as fh:
        json.dump(out, fh, separators=(",", ":"))
        fh.write("\n")


def preview(path, scale=4):
    """A review sheet: the three forms at `scale`, each over a dark swatch."""
    sets = []
    for name, fn, box, wall, w, h in (
            ("frog", frog_frames, FROG_BOX, FROG_CLING, FROG_W, FROG_H),
            ("fish", fish_frames, FISH_BOX, (), FISH_W, FISH_H),
            ("bird", bird_frames, BIRD_BOX, (), BIRD_W, BIRD_H)):
        fr = fn()
        try:
            check(name, fr, box, wall, {"frog": FROG_NARROW, "fish": FISH_NARROW}.get(name, ()))
        except AssertionError as e:
            print("CHECK:", e)
        sets.append((cells_of(fr, w, h), w, h))
    W = max(len(cs) * (w + 2) for cs, w, _ in sets)
    H = sum(h + 2 for _, _, h in sets)
    img = Image.new("RGBA", (W, H), (0x1c, 0x22, 0x22, 255))
    y = 0
    for cs, w, h in sets:
        strip = Image.new("RGBA", (len(cs) * w, h), (0, 0, 0, 0))
        for i, cimg in enumerate(cs):
            strip.alpha_composite(cimg, (i * w, 0))
        palette.selective_outline(strip)
        for i in range(len(cs)):
            img.alpha_composite(strip.crop((i * w, 0, (i + 1) * w, h)), (i * (w + 2), y))
        y += h + 2
    img.resize((W * scale, H * scale), Image.NEAREST).save(path)
