"""HD pass, area "back": the small sheets drawn natively at ART_SCALE --
pickups, props and the particle atlas (docs/plan-hd.md step 2).

At one pixel per world unit these were ASCII grids lit by `auto_shade`: a gem
was nine pixels of cyan with a white corner, a key a ring and two teeth. At 2x
each one is drawn as an object. The footprints (where each item sits in its
16x16 world cell, how wide, how tall) are the 1x ones, because the HUD lays
hearts 11 units apart and the triggers centre their sprites on the cell; what
changes is what is inside the footprint:

  * cut facets on the gem, a gloss on the heart, keys with a bevelled bow,
    a collar and two bits;
  * a carved door with mouldings, grain and a boss; a gold gateway with a
    leaf ring and an orb; a switch with a stud and a lit plate; pads with an
    inlaid emblem per form; stone arches laid in voussoirs.

The lighting is the look sample's (tools/art/kaya40.py `shade_hd`): whole ramp
steps, no Bayer, a weighted ink line (one texel on the lit side, two on the
shadow side, i.e. the old one-unit line where the shadow falls), and the
stair-step corners of the ink taken down to the darkest step of the material
they hug (`_hand_aa`).
"""
import math

from PIL import Image

from .palette import ART_SCALE, INK, LIGHT, step

K = ART_SCALE
CELL = 16                      # world units per pickup/prop cell
T = CELL * K                   # texels per cell

_L = (LIGHT[0] / math.sqrt(2.0), LIGHT[1] / math.sqrt(2.0))   # toward the light


class Cell:
    """One 16x16 world cell at K texels per unit. Texels hold (ramp, level),
    the string "ink", or None."""

    def __init__(self, w=T, h=T):
        self.w, self.h = w, h
        self.px = [[None] * w for _ in range(h)]

    def inside(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h

    def put(self, x, y, ramp, level):
        if self.inside(x, y):
            self.px[y][x] = (ramp, level)

    def ink(self, x, y):
        if self.inside(x, y):
            self.px[y][x] = "ink"

    def filled(self, x, y):
        return self.inside(x, y) and self.px[y][x] is not None

    def material(self, x, y):
        return self.inside(x, y) and self.px[y][x] not in (None, "ink")

    def outline(self, heavy=True):
        """Ink around every filled texel: one texel all round, and a second
        on the shadow side (down and right of the silhouette)."""
        ring = []
        for y in range(self.h):
            for x in range(self.w):
                if self.px[y][x] is not None:
                    continue
                n4 = [self.material(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
                if any(n4):
                    ring.append((x, y))
        for (x, y) in ring:
            self.px[y][x] = "ink"
        if heavy:
            more = []
            for y in range(self.h):
                for x in range(self.w):
                    if self.px[y][x] is None and (self.px[y][x - 1] == "ink" if x else False) \
                            and self.material(x - 2, y):
                        more.append((x, y))
                    elif self.px[y][x] is None and y and self.px[y - 1][x] == "ink" \
                            and self.material(x, y - 2):
                        more.append((x, y))
            for (x, y) in more:
                self.px[y][x] = "ink"

    def hand_aa(self):
        """Stair-step corners of the outer ink line become the darkest step of
        the material they hug, so a curve reads as a curve at 2x."""
        out = []
        for y in range(self.h):
            for x in range(self.w):
                if self.px[y][x] != "ink":
                    continue
                empty = [not self.filled(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
                mats = [self.px[y + dy][x + dx] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                        if self.material(x + dx, y + dy)]
                if sum(empty) == 2 and len(mats) == 2 and not (empty[0] and empty[1]) \
                        and not (empty[2] and empty[3]):
                    out.append((x, y, mats[0][0]))
        for (x, y, ramp) in out:
            self.px[y][x] = (ramp, 0)

    def image(self):
        img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        for y in range(self.h):
            for x in range(self.w):
                e = self.px[y][x]
                if e is None:
                    continue
                if e == "ink":
                    img.putpixel((x, y), INK + (255,))
                else:
                    img.putpixel((x, y), step(e[0], e[1]) + (255,))
        return img


# ---------------------------------------------------------------- geometry
def _distance(mask, w, h, cap=12):
    """Chamfer distance (texels) from every inside texel to the outside."""
    big = 999
    d = [[(big if mask[y][x] else 0) for x in range(w)] for y in range(h)]
    for _ in range(2):
        for y in range(h):
            for x in range(w):
                if d[y][x]:
                    for dx, dy, c in ((-1, 0, 2), (0, -1, 2), (-1, -1, 3), (1, -1, 3)):
                        nx, ny = x + dx, y + dy
                        v = d[ny][nx] if 0 <= nx < w and 0 <= ny < h else 0
                        d[y][x] = min(d[y][x], v + c)
        for y in range(h - 1, -1, -1):
            for x in range(w - 1, -1, -1):
                if d[y][x]:
                    for dx, dy, c in ((1, 0, 2), (0, 1, 2), (1, 1, 3), (-1, 1, 3)):
                        nx, ny = x + dx, y + dy
                        v = d[ny][nx] if 0 <= nx < w and 0 <= ny < h else 0
                        d[y][x] = min(d[y][x], v + c)
    return [[min(cap, v / 2.0) for v in row] for row in d]


def pillow(c, mask, ramp, base, span=1.6, depth=6.0, spec=None, rim=True):
    """Shade a region as a soft rounded volume: a height field from the
    distance to its edge, lit from the upper left, quantised to whole steps.
    `spec` is (ramp, level) for the hottest texels, or None."""
    w, h = c.w, c.h
    dist = _distance(mask, w, h, cap=depth)
    height = [[math.sqrt(dist[y][x] / depth) if mask[y][x] else 0.0 for x in range(w)]
              for y in range(h)]
    for y in range(h):
        for x in range(w):
            if not mask[y][x]:
                continue
            gx = (height[y][min(w - 1, x + 1)] - height[y][max(0, x - 1)]) * 0.5
            gy = (height[min(h - 1, y + 1)][x] - height[max(0, y - 1)][x]) * 0.5
            nz = 0.35
            n = math.sqrt(gx * gx + gy * gy + nz * nz)
            lam = (-gx * _L[0] - gy * _L[1]) / n          # facing the light
            lvl = base + span * lam * 1.6 + 0.35 * (height[y][x] - 0.6)
            if rim and dist[y][x] <= 1.0 and lam < -0.05:
                lvl -= 0.6
            if spec and lam > 0.62 and 0.25 < height[y][x] < 0.85:
                c.put(x, y, spec[0], spec[1])
                continue
            c.put(x, y, ramp, round(lvl))


def _mask(w, h, fn):
    return [[bool(fn(x + 0.5, y + 0.5)) for x in range(w)] for y in range(h)]


def _poly(pts):
    def inside(x, y):
        n = len(pts)
        j = n - 1
        on = False
        for i in range(n):
            xi, yi = pts[i]
            xj, yj = pts[j]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                on = not on
            j = i
        return on
    return inside


# ---------------------------------------------------------------- pickups
def gem():
    """A brilliant cut: a bright table, crown facets lit on the left and
    shadowed on the right, a girdle line, a pavilion fanning to the culet with
    a streak of reflected light, and a four-point glint on the table."""
    c = Cell()
    outline = _poly([(10, 6), (18, 6), (24, 12), (24, 14), (14.5, 24.5), (4, 14), (4, 12)])
    for y in range(T):
        for x in range(T):
            fx, fy = x + 0.5, y + 0.5
            if not outline(fx, fy):
                continue
            if fy < 12:                                 # crown
                hw = 4 + (fy - 6) * (10.0 / 6.0)
                u = (fx - 14) / hw
                if fy < 9.5 and abs(fx - 14) < 4.0 + (fy - 6) * 0.4:
                    lvl = 6 if fy < 7 else 5            # table
                elif u < -0.55:
                    lvl = 6 if fy < 9 else 5
                elif u < 0:
                    lvl = 5
                elif u < 0.55:
                    lvl = 5
                else:
                    lvl = 4
            elif fy < 14:                               # girdle
                lvl = 5 if fx < 14 else 4
                if fy < 13 and fx < 10:
                    lvl = 5
            else:                                       # pavilion
                u = (fx - 14.5) / max(0.5, (24.5 - fy) * (10.0 / 10.5))
                if u < -0.55:
                    lvl = 5
                elif u < -0.08:
                    lvl = 5
                elif u < 0.4:
                    lvl = 4
                else:
                    lvl = 3
                if abs(u + 0.08) < 0.06 or abs(u - 0.4) < 0.06:
                    lvl -= 1                            # the pavilion's facet lines
                if abs(u + 0.32) < 0.07 and fy < 21:
                    lvl = 6                             # reflected streak
            c.put(x, y, "water", lvl)
    # facet edges: lighter lines where two facets meet on the lit side
    for (x, y) in ((9, 9), (8, 10), (7, 11), (19, 9), (20, 10)):
        c.put(x, y, "water", 6 if x < 14 else 4)
    for x in range(5, 24):
        c.put(x, 12, "water", 5 if x < 14 else 4)
    # the glint: metal's top step, a four-point star on the table's left
    for (dx, dy) in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1), (-2, 0), (0, -2)):
        c.put(11 + dx, 8 + dy, "metal", 6 if abs(dx) + abs(dy) <= 1 else 5)
    c.outline()
    c.hand_aa()
    return c.image()


def heart():
    """A glossy heart: rounded lobes, a crease down the middle, a crescent of
    gloss on the left lobe and a smaller one on the right, and the colour
    deepening toward the point."""
    c = Cell()

    def f(x, y):
        # the classic implicit heart, fitted to the 1x footprint: 26 texels
        # wide from x 0, lobes topping out at y 6, the point at y 27
        nx = (x - 13.0) / 11.4
        ny = -(y - 18.2) / 9.8
        return (nx * nx + ny * ny - 1) ** 3 - nx * nx * ny ** 3 <= 0
    m = _mask(T, T, f)
    pillow(c, m, "ember", 2.8, span=1.3, depth=7.0)
    for y in range(T):
        for x in range(T):
            if m[y][x] and y > 21 and c.material(x, y):
                ramp, lvl = c.px[y][x]
                c.px[y][x] = (ramp, max(1, lvl - 1))      # deeper toward the point
    for y in range(9, 12):                                # the crease under the cusp
        if m[y][13]:
            c.put(13, y, "ember", 2)
            c.put(14, y, "ember", 3)
    for (x, y) in ((4, 12), (4, 11), (5, 10), (6, 9), (7, 9), (5, 11)):
        c.put(x, y, "metal", 6)                           # gloss, left lobe
    for (x, y) in ((8, 9), (6, 12)):
        c.put(x, y, "ember", 6)
    for (x, y) in ((18, 9), (19, 9), (17, 10)):
        c.put(x, y, "ember", 5)                           # and the right
    c.outline()
    c.hand_aa()
    return c.image()


def key(ramp, base):
    """A key: a bevelled ring bow with a lozenge cut through it, a collar,
    a shank with a lit edge, and two bits with a notch between them."""
    c = Cell()

    def bow(x, y):
        d = math.hypot(x - 12.0, y - 11.0)
        return 2.6 < d <= 6.6
    def shank(x, y):
        return 10 <= x <= 14 and 16 <= y <= 29.5
    def collar(x, y):
        return 9 <= x <= 15 and 17 <= y <= 19
    def bits(x, y):
        return (14 <= x <= 19 and 22 <= y <= 24.5) or (14 <= x <= 17.5 and 26 <= y <= 28.5)
    m = _mask(T, T, lambda x, y: bow(x, y) or shank(x, y) or collar(x, y) or bits(x, y))
    pillow(c, m, ramp, base, span=1.2, depth=3.0, spec=(ramp, 6))
    for y in range(17, 29):                               # the shank's lit edge
        if c.material(10, y):
            c.put(10, y, ramp, min(6, round(base + 1.2)))
    for x in range(9, 16):                                # collar grooves
        c.put(x, 17, ramp, round(base + 1))
        c.put(x, 19, ramp, round(base - 1.2))
    c.put(17, 25, ramp, round(base - 1.4))                # notch shadow
    for (x, y) in ((9, 7), (8, 8), (7, 9)):                # bow highlight
        c.put(x, y, ramp, 6)
    c.outline()
    c.hand_aa()
    return c.image()


def pickup_cells():
    """The pickups sheet's cells: gem, heart, yellow, red and cyan key (the
    frame order src/ui/hud.gd and src/world/triggers/pickup.gd read)."""
    return [gem(), heart(), key("gold", 4.6), key("ember", 3.6), key("water", 5.0)]


# ---------------------------------------------------------------- props
def _wood_grain(x, y, seed):
    return (math.sin(y * 0.9 + 2.2 * math.sin(x * 0.31 + seed) + seed) > 0.86)


def _door_frame(c, inner_fill):
    """The outer two mouldings shared by the open and closed door: ink edge,
    a frame with a lit top-left bevel and a shadowed bottom-right, and a
    second rebate inside it."""
    for y in range(T):
        for x in range(T):
            e = min(x, y, T - 1 - x, T - 1 - y)
            if e < 2:
                c.ink(x, y)
                continue
            lit = (x <= y and x + y < T) or (y < x and x + y < T - 1)     # top or left half
            if e < 4:
                lvl = 5 if (e == 2 and (y < T / 2.0 if y <= x else x < T / 2.0) and lit) else (4 if lit else 2)
                if e == 3:
                    lvl = 4 if lit else 1
            elif e < 7:
                lvl = 3 if _wood_grain(x, y, 1.3) else 4
                if e == 6:
                    lvl = 1 if lit else 4                 # the rebate's inner edge
            else:
                inner_fill(x, y, e)
                continue
            c.put(x, y, "wood", lvl)
    for (x, y) in ((4, 4), (27, 4), (4, 27), (27, 27)):    # nail heads
        c.put(x, y, "gold", 5)
        c.put(x + 1, y + 1, "gold", 2)


def door_closed():
    def fill(x, y, e):
        # a raised field inside a sunk moulding, and a gold boss in the middle
        lit = x + y < T - 1
        if e < 9:
            lvl = 2 if e == 7 else (3 if not lit else 2)
            if e == 8:
                lvl = 4 if lit else 2
        else:
            lvl = 3 if _wood_grain(x, y, 4.1) else 4
            if e == 9:
                lvl = 5 if lit else 3
        c.put(x, y, "wood", lvl)
    c = Cell()
    _door_frame(c, fill)
    m = _mask(T, T, lambda x, y: math.hypot(x - 16, y - 16) <= 3.6)
    pillow(c, m, "gold", 4.4, span=1.2, depth=3.0, spec=("gold", 6), rim=False)
    for (x, y) in ((13, 18), (14, 19), (15, 19), (16, 19), (17, 19), (18, 18), (19, 17)):
        c.put(x, y, "gold", 2)
    return c.image()


def door_open():
    def fill(x, y, e):
        if e < 8:
            c.ink(x, y)
            return
        # the dark beyond: a sliver of jamb light on the left, the floor a
        # step brighter than the void above it
        lvl = 0
        if x <= 9:
            lvl = 1
        if y >= T - 11:
            lvl = 1 if (x + y) % 2 or y >= T - 10 else 0
        c.put(x, y, "water", lvl)
    c = Cell()
    _door_frame(c, fill)
    return c.image()


def exit_totem():
    """The level exit: a gold ring with carved notches, an inner bronze
    band, a ring of leaves, a green field and an orb with a highlight."""
    c = Cell()
    cx, cy = 15.5, 14.5
    for y in range(T):
        for x in range(T):
            fx, fy = x + 0.5, y + 0.5
            d = math.hypot(fx - cx, fy - cy)
            a = math.degrees(math.atan2(fy - cy, fx - cx))
            facing = -((fx - cx) * _L[0] * -1 + (fy - cy) * _L[1] * -1) / max(0.5, d)
            if d > 14.0:
                continue
            if d > 12.0:
                lvl = 5 if facing < -0.2 else (4 if facing < 0.4 else 3)
                if d > 13.3:
                    lvl -= 1
                if (a % 30.0) < 4.0:
                    lvl = 2                                 # notches
                c.put(x, y, "gold", lvl)
            elif d > 10.4:
                c.put(x, y, "gold", 3 if facing < 0 else 2)
            elif d > 8.4:
                leaf = ((a + 360) % 24.0) / 24.0
                lvl = 5 if leaf < 0.45 else (4 if leaf < 0.8 else 2)
                c.put(x, y, "grass", lvl)
            else:
                lvl = 2 if (int(a + 360) // 45) % 2 else 3
                if d > 7.6:
                    lvl = 1
                c.put(x, y, "grass", lvl)
    m = _mask(T, T, lambda x, y: math.hypot(x - 13.0, y - 12.5) <= 3.4)
    pillow(c, m, "water", 4.8, span=1.0, depth=3.0, spec=("metal", 6), rim=False)
    c.outline()
    c.hand_aa()
    return c.image()


def switch(on):
    """A floor switch. Off: a steel dome on its plate with a stud on top and
    a groove round its waist. On: pressed flush, its two gold bands lit."""
    c = Cell()
    if not on:
        dome = _mask(T, T, lambda x, y: ((x - 12.5) / 8.5) ** 2 + ((y - 21.0) / 9.0) ** 2 <= 1
                     and y < 21.0)
        pillow(c, dome, "metal", 4.2, span=1.3, depth=5.0, spec=("metal", 6))
        for x in range(4, 22):
            if c.material(x, 17):
                c.put(x, 17, "metal", 2)                    # the groove
                c.put(x, 18, "metal", 4 if x < 13 else 3)
        stud = _mask(T, T, lambda x, y: math.hypot(x - 12.5, y - 12.2) <= 1.6)
        pillow(c, stud, "gold", 4.6, span=1.0, depth=2.0, rim=False)
        for y in range(21, 25):
            for x in range(4, 22):
                lvl = 4 if y == 21 else (3 if y < 24 else 2)
                if x == 4:
                    lvl = 4
                c.put(x, y, "metal", lvl)
    else:
        for y in range(16, 25):
            for x in range(6 if y < 18 else 4, (20 if y < 18 else 22)):
                if y in (18, 19) or y in (22,):
                    lvl = 5 if y in (18, 22) else 4
                    c.put(x, y, "gold", lvl if x > 5 else lvl + 1)
                else:
                    lvl = 4 if y in (16, 20) else (3 if y < 24 else 2)
                    c.put(x, y, "metal", lvl)
        for x in (8, 12, 16):
            c.put(x, 18, "gold", 6)
    c.outline()
    c.hand_aa()
    return c.image()


def pad(ramp, top_ramp, motif):
    """A transformation pad: a low plinth with a lit lip and an inlaid emblem
    of its form -- a lily leaf for the frog, a wave for the fish, a feather
    for the bird -- set between two polished studs."""
    c = Cell()
    body, lip = {"grass": (2.4, 4.2), "water": (3.4, 5.4), "metal": (3.6, 6.0)}[ramp]
    for y in range(18, 30):
        x0 = 2 if y > 19 else 4
        for x in range(x0, T - x0):
            if y < 20:
                lvl = round(lip) if y == 18 else round(lip - 1)
            else:
                lvl = round(body) + (1 if x < 4 else 0) - (1 if y > 27 else 0)
            c.put(x, y, ramp if y >= 20 else top_ramp, lvl)
    for sx in (6, 25):                                    # the studs
        m = _mask(T, T, lambda x, y, sx=sx: math.hypot(x - sx, y - 23.5) <= 1.8)
        pillow(c, m, top_ramp, lip - 1.0, span=1.0, depth=2.0, rim=False)
        c.put(sx - 1, 22, "metal", 6)
    hi, lo = min(6, round(lip)), max(0, round(body) - 2)
    for y in range(20, 29):
        for x in range(9, 23):
            fx, fy = x + 0.5 - 16.0, y + 0.5 - 24.0
            lvl = None
            if motif == "leaf":                           # a lily leaf with its midrib
                hw = 3.2 * math.sin(math.pi * (fx + 6.5) / 13.0) if abs(fx) < 6.5 else -1
                if abs(fy) <= hw:
                    lvl = lo if abs(fy) < 0.5 else (hi if fy < 0 else hi - 1)
                    if fy > 0 and ((fx - fy) % 3.0) < 0.6:
                        lvl = hi - 2                      # veins on the shaded half
            elif motif == "wave":                         # two crests rolling right
                wy = 1.6 * math.sin(fx * 0.9)
                if abs(fy - wy) < 1.0 and abs(fx) < 5.6:
                    lvl = hi
                elif abs(fy - wy - 1.4) < 0.6 and abs(fx) < 5.6:
                    lvl = lo
            else:                                         # a feather, quill to tip
                u = (fx + 6.0) / 12.0                     # 0 quill .. 1 tip
                if 0 <= u <= 1:
                    axis = 2.0 - u * 4.0                  # rising to the right
                    w = fy - axis
                    hw = 2.6 * math.sin(math.pi * min(1.0, u * 1.15)) if u > 0.12 else 0.5
                    if abs(w) < 0.5:
                        lvl = lo                          # the shaft
                    elif abs(w) <= hw:
                        lvl = hi if w < 0 else hi - 1
                        if ((fx * 1.0 + abs(w) * 1.3) % 2.2) < 0.55:
                            lvl -= 2                      # the barbs
            if lvl is not None:
                c.put(x, y, top_ramp, max(0, lvl))
    c.outline()
    c.hand_aa()
    return c.image()


def arch(state):
    """A hub door: a stone arch laid in blocks with a keystone, round a
    doorway that shows its state -- a timber door with a gold lock and a
    keyhole (locked), the dark with the door ajar (open), or a green seal
    with a white star (cleared)."""
    c = Cell()
    for y in range(T - 2):
        for x in range(T):
            # the 1x silhouette: a lintel with its top corners stepped in
            if (y < 2 and not 4 <= x < 28) or (y < 4 and not 2 <= x < 30) \
                    or (y < 6 and x >= 30):
                continue
            if 6 <= x <= 25 and 6 <= y <= 25:
                continue
            lit = x + y < T
            lvl = 4 if lit else 3
            if y < 6:                                         # the lintel, in voussoirs
                if 13 <= x <= 18:
                    lvl = 5 if x < 16 else 4                  # keystone
                    if x in (13, 18):
                        lvl = 2
                elif (x % 6) == 1:
                    lvl = 2
                if y == 5:
                    lvl = 2                                   # its shadow on the jambs
            else:                                             # the jambs, in courses
                m = (y - 6) % 6
                if m == 5:
                    lvl = 2
                elif m == 0:
                    lvl = 5 if lit else 4
                if (x in (3, 28)) and m != 5:
                    lvl = 3 if lit else 2                     # the moulding line
            # the silhouette's own edge: lit on top and left, dark on the right
            top = (y < 2) or (y < 4 and x in (2, 3, 28, 29)) or (y < 6 and x in (0, 1))
            if top or x in (0, 1) and y >= 6:
                lvl = 6 if (y == 0 or x == 0 or (y < 4 and x in (2,)) or (y < 6 and x == 0)) else 5
            if x >= 30 and y >= 6:
                lvl = 2
            c.put(x, y, "metal", lvl)
    for x in range(T):
        c.ink(x, T - 2)
        c.ink(x, T - 1)
    for y in range(6, 27):
        for x in range(6, 27):
            if x in (6, 7) or y in (6, 7) or x in (25, 26) or y in (25, 26):
                c.ink(x, y)
    for y in range(8, 25):
        for x in range(8, 25):
            fx, fy = x + 0.5, y + 0.5
            if state == "locked":
                lvl = 3 if _wood_grain(x, y * 0.3, 2.7) else 4
                if x in (8, 9) or y in (8, 9):
                    lvl = 2
                if abs(fx - 16.5) < 0.7:
                    lvl = 2                                   # the two leaves of the door
                c.put(x, y, "wood", lvl)
            elif state == "open":
                lvl = 0 if y < 21 else 1
                if 8 <= x <= 11:
                    c.put(x, y, "wood", 3 if x < 10 else 2)  # the door, swung in
                    continue
                c.put(x, y, "water", lvl + (1 if x == 12 else 0))
            else:
                d = math.hypot(fx - 16.5, fy - 16.5)
                lvl = 2 if d > 6.5 else (3 if d > 5.5 else 4)
                c.put(x, y, "grass", lvl)
    if state == "locked":
        m = _mask(T, T, lambda x, y: 13.5 <= x <= 19.5 and 14 <= y <= 20)
        pillow(c, m, "gold", 4.4, span=1.2, depth=2.0, spec=("gold", 6), rim=False)
        for (x, y) in ((16, 16), (16, 17), (16, 18), (15, 18), (17, 18)):
            c.ink(x, y)                                       # the keyhole
    elif state == "cleared":
        for r in range(0, 5):
            for (dx, dy) in ((r, 0), (-r, 0), (0, r), (0, -r)):
                c.put(16 + dx, 16 + dy, "metal", 6 if r < 3 else 5)
        for (dx, dy) in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            c.put(16 + dx, 16 + dy, "metal", 5)
    c.hand_aa()
    return c.image()


def prop_cells():
    """The props sheet's cells, in the 1x frame order: door closed/open, the
    exit totem, switch off/on, the frog/fish/bird pads, arch locked/open/
    cleared."""
    return [door_closed(), door_open(), exit_totem(), switch(False), switch(True),
            pad("grass", "grass", "leaf"), pad("water", "water", "wave"),
            pad("metal", "metal", "feather"),
            arch("locked"), arch("open"), arch("cleared")]


# ---------------------------------------------------------------- particles
# 8x8 world cells, so 16x16 texels; drawn in tools/gen_fx.py's own PAL (it
# carries the soft-alpha variants the particles fade with). Each row keeps the
# 1x frame's footprint and timing; at 2x the shapes are made of smaller marks
# -- a dust puff is several puffs, a spark has a hot core and thin rays, a
# leaf has a midrib.
P = 8 * K


def _blank():
    return [['.'] * P for _ in range(P)]


def _disc(g, cx, cy, r, ch, soft=None):
    for y in range(P):
        for x in range(P):
            d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            if d <= r:
                g[y][x] = ch
            elif soft and d <= r + 0.8 and g[y][x] == '.':
                g[y][x] = soft


def _dust(f, kick=False):
    g = _blank()
    spread = [2.5, 4.5, 6.0, 7.0][f]
    puffs = [(-1.0, 0.0), (1.0, -0.4), (0.0, -1.0), (-0.6, 0.8), (0.9, 0.7), (0.0, 0.0)]
    rad = [2.2, 2.4, 1.8, 0.9][f]
    cy = 7.0 if not kick else 6.0
    for i, (dx, dy) in enumerate(puffs):
        if f == 3 and i % 2:
            continue
        x, y = 7.0 + dx * spread, cy + dy * spread * 0.6 - f * 0.6
        if f < 2:
            _disc(g, x, y, rad, 'a', soft='A')
            _disc(g, x - 0.6, y - 0.6, rad * 0.55, 'w')
        elif f == 2:
            _disc(g, x, y, rad, 'A')
            _disc(g, x - 0.4, y - 0.4, rad * 0.5, 'W')
        else:
            _disc(g, x, y, rad, 'A')
    if kick and f < 3:
        for i in range(8):
            a = math.radians(i * 45 + 22)
            r = 3.0 + f * 2.2
            x, y = int(7.5 + math.cos(a) * r), int(7 + math.sin(a) * r * 0.8)
            if 0 <= x < P and 0 <= y < P:
                g[y][x] = 'd' if f < 2 else 'A'
    return g


def _spark(f):
    g = _blank()
    if f < 2:
        n = 4 if f == 0 else 8
        L = 7 if f == 0 else 6
        for i in range(n):
            a = math.radians(i * 360.0 / n)
            for k in range(1, L * 2):
                r = k / 2.0
                x, y = int(7.5 + math.cos(a) * r), int(7.5 + math.sin(a) * r)
                if 0 <= x < P and 0 <= y < P:
                    g[y][x] = 'w' if r < 1.5 else ('y' if r < L * 0.7 else 'o')
        _disc(g, 7.5, 7.5, 1.6 if f == 0 else 1.2, 'w')
    elif f == 2:
        for (x, y, ch) in ((6, 6, 'y'), (7, 6, 'o'), (6, 7, 'w'), (7, 7, 'y'), (5, 7, 'o'),
                           (8, 8, 'o'), (1, 1, 'o'), (14, 1, 'o'), (1, 13, 'o'), (14, 13, 'o'),
                           (2, 2, 'o'), (13, 12, 'o')):
            g[y][x] = ch
    else:
        for (x, y, ch) in ((7, 7, 'o'), (8, 7, 'y'), (5, 3, 'o'), (10, 10, 'o'), (11, 11, 'o')):
            g[y][x] = ch
    return g


def _shimmer(f):
    g = _blank()
    arm = [2, 4, 6, 5][f]
    cx, cy = 8, 7
    for k in range(1, arm + 1):
        ch = 'c' if k < arm - 1 or f < 2 else 'C'
        if f == 3 and k < 2:
            continue
        for (dx, dy) in ((k, 0), (-k, 0), (0, k), (0, -k)):
            g[cy + dy][cx + dx] = ch
    if f < 3:
        g[cy][cx] = 'w'
        if f >= 1:
            for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                g[cy + dy][cx + dx] = 'w'
    if f >= 1:
        for (dx, dy) in ((1, 1), (-1, -1), (1, -1), (-1, 1)):
            g[cy + dy * (f + 1)][cx + dx * (f + 1)] = 'C'
    return g


def _scatter(f):
    g = _blank()

    def leaf(x0, y0, ang, L):
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        for y in range(P):
            for x in range(P):
                dx, dy = x + 0.5 - x0, y + 0.5 - y0
                u, w = dx * ca + dy * sa, -dx * sa + dy * ca
                if 0 <= u <= L and abs(w) <= 1.6 * math.sin(math.pi * u / L):
                    g[y][x] = 'g' if (abs(w) < 0.5 or w > 0) else 'G'

    def chip(x0, y0, s, ch):
        for (dx, dy) in ((0, 0), (1, 0), (0, 1), (1, 1), (2, 0))[:s]:
            if 0 <= x0 + dx < P and 0 <= y0 + dy < P:
                g[y0 + dy][x0 + dx] = ch
    t = f * 1.6
    if f < 3:
        leaf(3 - t * 0.6, 4 - t * 0.5, 30 + f * 50, 6 - f)
    if f < 2:
        leaf(9 + t, 9 + t * 0.6, 200 + f * 70, 5)
    chip(int(12 + t * 0.6), int(4 - t * 0.4), 5 - f, 'k')
    chip(int(8 + t * 0.3), int(10 + t), 4 - f, 'm')
    if f >= 1:
        chip(int(14 - f), int(9 + f * 1.5), 2, 'g')
        chip(int(4 + f), int(13 - f), 2, 'k')
    return g


def _scuff(f):
    g = _blank()
    n = [10, 8, 4, 2][f]
    for i in range(n):
        x = 2 + int(i * 11.0 / max(1, n - 1)) + (f if i % 2 else 0)
        y = 12 + (i % 2) - (1 if f > 1 and i % 3 == 0 else 0)
        if x < P:
            g[y][x] = 'd' if (f < 2 and 2 < i < n - 3) else 'a'
            if f == 0 and i % 2 == 0 and x + 1 < P:
                g[y][x + 1] = 'd'
    if f < 2:
        for x in range(3 + f * 2, 12 - f * 2):
            g[13][x] = 'd' if x % 3 else 'a'
    return g


def _splash(f):
    g = _blank()
    r = [3.0, 5.0, 6.5, 7.2][f]
    for i in range(16):
        a = math.radians(i * 22.5 + (11 if f % 2 else 0))
        x, y = int(8 + math.cos(a) * r), int(8 + math.sin(a) * r)
        if 0 <= x < P and 0 <= y < P and (f < 2 or i % 2 == 0):
            g[y][x] = 'c' if f < 2 else 'C'
            if f < 2 and y + 1 < P:
                g[y + 1][x] = 'C'
    if f < 2:
        _disc(g, 8, 8, 2.2 - f * 0.6, 'C')
        _disc(g, 7.3, 7.3, 1.0, 'w')
    else:
        for (x, y) in ((3, 6 + f), (12, 7 + f), (8, 3 + f * 2)):
            if 0 <= y < P:
                g[y][x] = 'c'
                if y - 1 >= 0:
                    g[y - 1][x] = 'w' if f == 2 else 'C'
    return g


def particle_rows():
    """The seven particle rows, four frames each, as 16x16 rows of PAL keys:

      0 landing dust: a puff that spreads and thins
      1 blade impact spark: a hot star that collapses to embers
      2 gem shimmer: a four-point twinkle that opens and closes
      3 enemy death scatter: shell chips and leaf litter
      4 turn scuff: a low heel-streak, spawned when RenderFacingFSM enters
        TURN on the ground (docs/plan-art-motion.md phase A)
      5 takeoff kick: a brighter, wider dust, on the tick a jump leaves the
        ground (vel.y < 0), not on a walk off a ledge
      6 surface-break splash: cyan, not off-white, so it reads as water;
        spawned by form_fish.gd as the fish breaks the surface (phase B)
    """
    return [[_dust(f) for f in range(4)], [_spark(f) for f in range(4)],
            [_shimmer(f) for f in range(4)], [_scatter(f) for f in range(4)],
            [_scuff(f) for f in range(4)], [_dust(f, kick=True) for f in range(4)],
            [_splash(f) for f in range(4)]]


def particles(pal):
    rows = particle_rows()
    img = Image.new("RGBA", (P * 4, P * len(rows)), (0, 0, 0, 0))
    for ry, row in enumerate(rows):
        for fx, frame in enumerate(row):
            for y, line in enumerate(frame):
                for x, ch in enumerate(line):
                    if ch != '.':
                        img.putpixel((fx * P + x, ry * P + y), pal[ch])
    return img
