"""2. SUNKEN RUINS (ids 220-231), drawn natively at 2x.

Started by the tileset agent (hdtiles) as the second worked example of
docs/hd-tiles-howto.md; the ruins agent owns this file from here on. Every id
of the world is registered at the bottom, so the whole world is native.

The world's rule from tiles.py still holds at 2x -- "a world must not swallow
the player": stone and water bulk sit in luma 40-92 (stone steps 1-3, water
1-3), the algae is held under 55 (foliage <= 3), and the only bright things
are a texel or two wide: a wet crest, a spine tip, a glint in a joint.
"""
import math
import random

from .hd_tilekit import (BIT_E, BIT_N, BIT_S, BIT_W, N, blob, clear, crack, decoration,
                         dresser, ellipse, fill, get, ink, leaf, level_of, new, pit,
                         put, put_c, shift, side_xy, tile, wave)
from .hd_tilekit import ACCENTS
from .hd_tiles_jungle import chip, crack_down


# ------------------------------------------------------------- masonry
def t_ruin_stone_hd(seed, algae=False):
    """Ashlar a century under water: t_stone_hd's half-offset coursing, but
    every joint holds standing water (dark, with a wet glint where it catches
    the light), the faces are held two steps down and pitted, water stains run
    down from the joints, and algae has taken the shaded foot of each block."""
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
                put(img, x, y, "water", 1.6 + (0.9 if (x * 5 + y * 3) % 17 == 0 else 0))
                continue
            k = (lx // 2, ly // 2, course)
            if k not in jit:
                jit[k] = rnd.uniform(-0.5, 0.5)
            lvl = 2.5 + jit[k] - (lx / 32.0 + ly / 16.0) * 0.4
            if ly == 1:
                lvl += 1.3
            elif ly == 2:
                lvl += 0.6
            elif ly == 15:
                lvl -= 1.3
            elif ly == 14:
                lvl -= 0.6
            if lx == 1:
                lvl += 0.8
            elif lx == 31:
                lvl -= 1.0
            put(img, x, y, "stone", lvl)
    for _ in range(6):                                   # pitting
        x, y = rnd.randrange(3, 29), rnd.randrange(3, 29)
        if y % 16 < 3 or y % 16 > 12:
            continue
        put(img, x, y, "stone", 1)
        put(img, x + 1, y, "stone", 1.4)
        put(img, x, y + 1, "stone", 3)
    for _ in range(3):                                   # stains run down from a joint
        x = rnd.randrange(2, 30)
        y0 = rnd.choice((1, 17))
        for k in range(rnd.randrange(4, 10)):
            shift(img, x, y0 + k, -1)
    for course in (0, 1):                                # algae in the shaded foot
        for _ in range(2):
            rx = rnd.uniform(2.5, 4.5)                   # kept inside the cell: the
            cx = rnd.uniform(rx + 1, N - rx - 1)         # variants sit side by side
            ellipse(img, "foliage", cx, course * 16 + 13.5, rx, 1.6, 1.4, wrap=False)
            put_c(img, int(cx), course * 16 + 12, "foliage", 2.2)
    crack(img, "stone", rnd.randrange(3, 14), rnd.randrange(4, 10), 10, 2.5, rnd)
    if algae:
        # The ledge-top read. Dark on purpose (foliage 1-3): a bright cap would
        # take the frog standing on it. The only bright thing is a broken wet
        # line along the crest, a texel deep.
        s = rnd.randrange(1 << 20)
        depth = []
        for x in range(N):
            env = math.sin(math.pi * (x + 0.5) / N)      # every variant meets at 5
            h = 5 + int(round(env * (1.5 * wave(x, s) + (0.8 if rnd.random() < 0.3 else 0))))
            for y in range(h):
                put_c(img, x, y, "foliage", 3.4 - y * 0.42)
            put_c(img, x, h, "foliage", 1.0)
            shift(img, x, h + 1, -1)
            depth.append(h)
        for _ in range(4):                               # fronds lying in the mat
            leaf(img, rnd.uniform(2, N - 6), rnd.uniform(1, 3), rnd.uniform(-0.3, 0.3),
                 rnd.uniform(5, 8), 1.2, "foliage", 2.6, wrap=False)
        x = 0
        while x < N:                                     # sun on the wet crest
            if rnd.random() < 0.18:
                for k in range(rnd.randrange(2, 5)):
                    put_c(img, x + k, 0, "water", 6)
                x += 6
            else:
                x += 1
        for _ in range(4):                               # strands down the face
            x = rnd.randrange(N)
            for k in range(rnd.randrange(3, 10)):
                put_c(img, x, depth[x] + k, "foliage", 2.4 - k * 0.18)
    return img


def t_ruin_wall_hd(seed):
    """Background masonry: the same building at the dark end of the ramp --
    a ghost of the coursing, half-offset joints, a drowned-green bloom."""
    rnd = random.Random(seed)
    img = fill(new(255), "stone", 0.85, rnd, grain=0.26)
    for y in (6, 22):
        for x in range(N):
            put(img, x, y, "stone", 0.3)
            put(img, x, y + 1, "stone", 1.6)
    for x, y0 in ((10, 8), (26, 24), (26, -8)):
        for y in range(y0, y0 + 14):
            put(img, x, y, "stone", 0.4)
            put(img, x + 1, y, "stone", 1.3)
    for _ in range(rnd.choice((1, 2))):                  # a drowned-green bloom, flat,
        rx, ry = rnd.uniform(6, 9), rnd.uniform(3.2, 4.6)  # inside the cell, its rim
        cx, cy = rnd.uniform(rx + 1, N - rx - 1), rnd.uniform(ry + 1, N - ry - 1)
        s = rnd.randrange(1 << 20)                       # lobed rather than oval

        def inside(x, y):
            a = math.atan2(y + 0.5 - cy, x + 0.5 - cx)
            lobe = 1 + 0.25 * wave(int((a + math.pi) / (2 * math.pi) * N), s)
            return ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= lobe
        for y in range(int(cy - ry - 2), int(cy + ry + 3)):
            for x in range(int(cx - rx - 2), int(cx + rx + 3)):
                if inside(x, y):                         # lit where it faces the light
                    put_c(img, x, y, "foliage", 1 if inside(x - 1, y - 1) else 2)
    for _ in range(12):
        put(img, rnd.randrange(N), rnd.randrange(N), "stone", rnd.choice((0, 2)))
    return img


#: the silt's laminae: (row, amplitude) -- uneven, so a wall of it does not
#: rule itself into a grid; every row is a wave on the tile's own period.
_SILT_BEDS = ((3, 1.4), (12, 2.0), (19, 1.2), (27, 1.8))


def t_ruin_silt_hd(seed):
    """Cold silt, the mud a flooded room collects, laid down in still water:
    soft laminae a world unit apart (a dark parting with the next bed's lit
    top under it), the warm earth showing only as a low lens of mud along a
    bed, one half-buried stone and a shell or two. Calm on purpose -- it is
    the fill under every ruins floor, so it is seen in whole walls.

    Its variants sit side by side at random, so nothing may cross the cell
    edge unless every variant agrees on it: each lamina meets the edge on
    its own row, and the objects are clipped inside the cell."""
    rnd = random.Random(seed)
    img = fill(new(255), "stone", 1.9, rnd, grain=0.18, cell=4)
    for row, amp in _SILT_BEDS:                          # laminae
        s = rnd.randrange(1 << 20)
        for x in range(N):
            env = math.sin(math.pi * (x + 0.5) / N)
            y = row + int(round(amp * env * (wave(x, s) * 0.6 + 0.6)))
            put(img, x, y, "stone", 1.2)
            put(img, x, y + 1, "stone", 2.6 if (x + row) % 9 >= 4 else 2.2)
    for _ in range(2):                                   # the mud, a lens along a bed
        row, _ = rnd.choice(_SILT_BEDS)
        cx = rnd.uniform(9, N - 9)
        rx = rnd.uniform(3.5, 5.5)
        ellipse(img, "dirt", cx, (row + 4.5) % N, rx, 1.3, 1, wrap=False)
        for x in range(int(cx - rx * 0.6), int(cx + rx * 0.6)):
            put_c(img, x, (row + 3) % N, "stone", 1.4)   # its shadowed upper lip
    x, y = rnd.uniform(6, 26), rnd.choice((8, 16, 24))   # a stone half in the mud
    blob(img, "stone", x, y, 2.6, 1.8, 2.2, lit=1.2, dark=1.0, shadow=0.8, wrap=False)
    for _ in range(2):                                   # shells: a lit arc, a dark mouth
        x, y = rnd.randrange(2, N - 5), rnd.choice((6, 9, 15, 23, 30))
        put_c(img, x, y, "stone", 3)
        put_c(img, x + 1, y - 1, "stone", 4)
        put_c(img, x + 2, y - 1, "stone", 4)
        put_c(img, x + 3, y, "stone", 3)
        put_c(img, x + 1, y, "stone", 1)
        put_c(img, x + 2, y, "stone", 1)
    return img


def t_ruin_column_hd(seed):
    """A fluted shaft standing in the drowned room: three broad flutes, each
    with a lit edge and a concave shade, a barrel falloff, the room's light
    on its left, its own cast shadow on the right, algae climbing it and one
    chipped drum joint. Tiles vertically."""
    rnd = random.Random(seed)
    img = fill(new(255), "water", 0.7, rnd, grain=0.2)
    x0, wdt = 8, 18
    for x in range(x0, x0 + wdt):
        t = (x - x0) / float(wdt - 1)
        f = ((x - x0) % 6) / 5.0
        for y in range(N):
            lvl = 2.3 + 1.0 - 2.3 * t
            lvl += 0.8 if f < 0.2 else (-1.2 if f > 0.9 else -0.2 + 0.3 * math.sin(math.pi * f))
            put(img, x, y, "stone", lvl + rnd.uniform(-0.15, 0.15))
    for y in range(N):
        ink(img, x0 + wdt, y)
        put(img, x0 + wdt + 1, y, "water", 0)
        put(img, x0 - 1, y, "stone", 3.2)
        put(img, x0 - 2, y, "water", 1.6)
    for _ in range(4):
        blob(img, "foliage", rnd.uniform(x0 + 2, x0 + wdt - 3), rnd.uniform(0, N),
             rnd.uniform(1.6, 3.0), rnd.uniform(1.6, 3.4), 1.2, lit=0.8, dark=0.5)
    y = rnd.randrange(N - 2)
    for x in range(x0, x0 + wdt):
        put(img, x, y, "stone", 0.7)
        put(img, x, y + 1, "stone", 3.4 if x < x0 + wdt * 0.6 else 2.4)
    return img


def t_ruin_slab_hd(seed):
    """One-way slab: a flag of masonry six texels thick with a lit arris, two
    joints between flags, algae hanging off its lip, and two corbels."""
    rnd = random.Random(seed)
    img = new(0)
    for x in range(N):
        for y, lvl in enumerate((4.6, 3.8, 3.2, 2.8, 2.3, 1.6)):
            put_c(img, x, y, "stone", lvl + (rnd.uniform(-0.3, 0.3) if y > 1 else 0))
        ink(img, x, 6)
    for sx in (8, 23):
        for y in range(6):
            put_c(img, sx, y, "stone", 1.0)
            put_c(img, sx + 1, y, "stone", 3.6 if y < 5 else 2.2)
    for _ in range(6):                                   # algae off the lip
        x = rnd.randrange(N)
        for k in range(rnd.randrange(2, 6)):
            put_c(img, x, 5 + k, "foliage", 2.6 - k * 0.3)
    for cx in (3, 24):                                   # corbels
        for k in range(5):
            for j in range(3 - k // 2):
                put_c(img, cx + k, 7 + j, "stone", 3.0 - k * 0.35 - j * 0.4)
    return img


def t_ruin_urchin_hd(seed):
    """The hazard: three urchins in the silt. Spines first, two texels at the
    root with a lit and a dark side and a pale tip; the body over them, purple
    with a ribbed test and one wet highlight."""
    rnd = random.Random(seed)
    img = new(0)

    def row(x, y, ramp, lvl):                            # wraps along the row only,
        if 0 <= y < N:                                   # so a run of them is one bed
            put(img, x, y, ramp, lvl)

    # Spines first, the body over their roots. Few and long, fanned evenly
    # over the upper half: ink_interactive outlines every one of them, so
    # spines closer than ~20 degrees merge into a dark mat (the first pass's
    # "busy"). Each is two texels at the root -- a lit upper side, a shaded
    # lower one -- narrowing to one, with a pale tip.
    urchins = ((6.0, 21.0, 5.2, 0), (16.5, 22.5, 4.4, 13), (26.5, 20.5, 5.6, -6))
    for cx, cy, r, turn in urchins:
        for i, ang in enumerate((228, 250, 270, 290, 312)):
            a = math.radians(ang + turn + rnd.randrange(-4, 5))
            ln = r + (5.0 if i in (0, 4) else 8.0) + rnd.uniform(0, 1.2)
            ux, uy = math.cos(a), math.sin(a)
            # a tapering wedge, rasterised by distance to its axis: clean
            # edges instead of a stepped line, lit on its up-left flank
            lit_side = 1 if (-uy * -0.7 + ux * -0.7) > 0 else -1
            for y in range(int(cy - ln - 2), int(cy + 3)):
                for x in range(int(cx - ln - 2), int(cx + ln + 3)):
                    px, py = x + 0.5 - cx, y + 0.5 - cy
                    t = px * ux + py * uy
                    if not r * 0.4 <= t <= ln:
                        continue
                    v = -px * uy + py * ux                  # signed distance off the axis
                    half = 1.5 * (1 - t / ln) + 0.25
                    if abs(v) > half:
                        continue
                    if t > ln - 1.6:
                        lvl = 5
                    elif v * lit_side > 0.2:
                        lvl = 3.8
                    elif v * lit_side < -0.4:
                        lvl = 1.6
                    else:
                        lvl = 2.8
                    row(x, y, "metal", lvl)
    for cx, cy, r, _ in urchins:
        for y in range(int(cy - r - 1), int(cy + r + 2)):   # the test: a lit dome
            for x in range(int(cx - r - 1), int(cx + r + 2)):
                dx, dy = (x + 0.5 - cx) / r, (y + 0.5 - cy) / (r * 0.86)
                d = dx * dx + dy * dy
                if d > 1:
                    continue
                v = 1.3 + (1 - d) * 1.4 - (dx + dy) * 1.0
                row(x, y, "purple", v)
        for j in range(6):                               # one row of tubercles
            a = math.radians(200 + j * 28)
            x, y = round(cx + math.cos(a) * r * 0.62), round(cy + math.sin(a) * r * 0.53)
            row(x, y, "purple", 4.6 if j < 3 else 3.6)
            row(x + 1, y + 1, "purple", 1.0)
        row(round(cx - r * 0.45), round(cy - r * 0.5), "water", 6)      # one wet glint
        row(round(cx - r * 0.45) + 1, round(cy - r * 0.5), "purple", 5)
    # The silt they are wedged in, a low mound over their feet.
    s = rnd.randrange(1 << 20)
    for x in range(N):
        top = 25 + int(round(1.2 * wave(x, s)))
        for y in range(top, 30):
            lvl = (2.8 if y == top else 2.0 if y == top + 1 else 1.4) + rnd.uniform(-0.25, 0.25)
            put_c(img, x, y, "dirt", lvl)
        if rnd.random() < 0.15:
            put_c(img, x, top, "stone", 4)               # a grain of shell
    return img


def t_ruin_grate_hd(seed):
    """An iron grate: square bars with a lit face and a shadow, a rivet at
    every crossing, rust blooming on the iron and algae in the squares."""
    rnd = random.Random(seed)
    img = fill(new(255), "water", 0.8, rnd, grain=0.2)
    for _ in range(4):
        blob(img, "foliage", rnd.uniform(0, N), rnd.uniform(0, N), rnd.uniform(2.4, 4),
             rnd.uniform(2, 3.4), 1.2, lit=0.6, dark=0.5)
    for i in (0, 11, 22):
        for y in range(N):
            put(img, i, y, "metal", 3.6)
            put(img, i + 1, y, "metal", 2.6)
            put(img, i + 2, y, "metal", 1.2)
        for x in range(N):
            put(img, x, i, "metal", 4.4)
            put(img, x, i + 1, "metal", 3.2)
            put(img, x, i + 2, "metal", 1.4)
    for i in (0, 11, 22):
        for j in (0, 11, 22):
            put(img, i, j, "metal", 5)
            put(img, i + 1, j + 1, "metal", 2)
            put(img, i + 2, j + 2, "metal", 1)
    # Rust. It starts where water stands, at a crossing, blooms over the
    # joint, and bleeds down the upright under it; elsewhere the iron is
    # pitted and a flake has come off showing the raw metal.
    crossings = [(i, j) for i in (0, 11, 22) for j in (0, 11, 22)]
    rnd.shuffle(crossings)
    for i, j in crossings[:4]:
        for dy in range(-1, 4):
            for dx in range(-1, 4):
                if abs(dx - 1) + abs(dy - 1) <= 2 + rnd.randrange(2):
                    put(img, i + dx, j + dy, "dirt", 3.4 if dx + dy < 2 else 2.4)
        put(img, i, j, "dirt", 4.6)
        put(img, i + 1, j, "ember", 3)                  # raw rust, a fleck
        run = rnd.randrange(5, 10)                       # the bleed down the upright
        for k in range(run):
            for dx, lvl in ((0, 3.4), (1, 2.6), (2, 1.4)):
                if dx == 0 or k < run - 2:
                    put(img, i + dx, j + 3 + k, "dirt", lvl - 0.15 * k)
        put(img, i + 1, j + 3 + run, "dirt", 1.4)        # a drip at its foot
    for _ in range(5):                                   # pitting on the bars
        b = rnd.choice((0, 11, 22))
        t = rnd.randrange(N)
        x, y = (b + rnd.randrange(2), t) if rnd.random() < 0.5 else (t, b + rnd.randrange(2))
        put(img, x, y, "metal", 1)
        put(img, x + 1, y + 1, "metal", 4)
    return img


def _kelp_x(y, ph):
    return 14 + 3.0 * math.sin(2 * math.pi * y / N + ph) + 1.0 * math.sin(4 * math.pi * y / N)


def t_kelp_hd(seed):
    """The climbable: a brown stipe (a lit shoulder, a body, a dark flank)
    wandering on a period of one tile so a column of it is one plant, ribbon
    blades off it in turn with a lit edge, and gas bladders."""
    rnd = random.Random(seed)
    img = new(0)
    ph = rnd.uniform(0, 2 * math.pi)
    for y in range(N):
        x = int(round(_kelp_x(y, ph)))
        for k, lvl in enumerate((3.8, 3.0, 2.2, 1.0)):
            put_c(img, x + k, y, "wood", lvl)
    for i, y in enumerate(range(2, N, 6)):
        x = _kelp_x(y, ph)
        left = i % 2 == 0
        ang = (math.pi - 0.35) if left else 0.35
        leaf(img, x + (0 if left else 3), y, ang, rnd.uniform(9, 12), 2.2, "foliage", 3.0,
             rib=0.6, rim=-1.4, wrap=False)
    for y in (5, 21):
        x = int(round(_kelp_x(y, ph))) - 2
        ellipse(img, "gold", x, y, 1.6, 1.6, 2.6, wrap=False)
        put_c(img, x - 1, y - 1, "gold", 4)
    return img


def t_ruin_algae_hd(seed):
    """Background algae mat, the flattest fill in the world: overlapping
    fronds a step apart, and cold light coming through it in patches."""
    rnd = random.Random(seed)
    img = fill(new(255), "foliage", 0.8, rnd, grain=0.2, cell=4)
    for _ in range(14):
        leaf(img, rnd.uniform(0, N), rnd.uniform(0, N), rnd.uniform(0, 2 * math.pi),
             rnd.uniform(6, 10), rnd.uniform(1.6, 2.6), "foliage", 1.2, rib=0.8, rim=-0.6)
    for _ in range(3):
        ellipse(img, "water", rnd.uniform(0, N), rnd.uniform(0, N), rnd.uniform(2.5, 4.5),
                rnd.uniform(1.4, 2.4), 1)
    return img


def t_ruin_cracked_hd(seed):
    """Breakable masonry that has already failed: a fracture right through
    it (inked, with a lit lower lip and a shadowed upper one), the course
    under it dropped, corners knocked off, and splinter cracks."""
    rnd = random.Random(seed)
    img = t_ruin_stone_hd(seed + 700)
    # Something hit it: a crushed point a little off centre, and the stone
    # has broken away from it in a star. The main arms are open breaks two
    # texels wide (an inked gap; the far wall of the gap lit where the light
    # gets in, i.e. the side facing up-left, the near wall in shadow); the
    # minor arms are hairlines. Arms stop short of the cell edge so a wall of
    # breakables still reads block by block along the joints.
    cx, cy = rnd.uniform(12, 19), rnd.uniform(12, 18)
    arms = []
    base = rnd.uniform(0, 360)
    for k in range(5):
        ang = math.radians(base + k * 72 + rnd.uniform(-14, 14))
        arms.append((ang, k < 3))
    for ang, major in arms:
        x, y = cx, cy
        ln = rnd.uniform(11, 16) if major else rnd.uniform(6, 9)
        a = ang
        pts = []
        for _ in range(int(ln * 2)):
            x += math.cos(a) * 0.5
            y += math.sin(a) * 0.5
            a += rnd.uniform(-0.18, 0.18)
            if not (2 <= x < N - 2 and 2 <= y < N - 2):
                break
            pts.append((int(round(x)), int(round(y))))
        for i, (px, py) in enumerate(pts):
            wide = major and i < len(pts) * 0.7
            for ox, oy in (((0, 0), (1, 0), (0, 1)) if wide else ((0, 0),)):
                ink(img, px + ox, py + oy)
            if wide:                                     # lit far wall, dark near wall
                put_c(img, px + 2, py + 1, "stone", 4.6)
                put_c(img, px + 1, py + 2, "stone", 4.2)
                put_c(img, px - 1, py - 1, "stone", 1)
            else:
                put_c(img, px + 1, py + 1, "stone", 4)
        if major and pts:                                # a hairline splits off it
            mx, my = pts[len(pts) // 2]
            b = ang + rnd.choice((-1, 1)) * rnd.uniform(0.6, 0.9)
            for j in range(rnd.randrange(4, 8)):
                hx, hy = int(round(mx + math.cos(b) * j)), int(round(my + math.sin(b) * j))
                if 2 <= hx < N - 2 and 2 <= hy < N - 2:
                    ink(img, hx, hy)
                    put_c(img, hx + 1, hy + 1, "stone", 3.8)
    # The crushed point: a pit with spalled flakes round it.
    pit(img, "stone", cx, cy, 2.6, 2.2, 1)
    for _ in range(4):
        a = rnd.uniform(0, 2 * math.pi)
        fx, fy = cx + math.cos(a) * 4.2, cy + math.sin(a) * 3.6
        put_c(img, round(fx), round(fy), "stone", 4.4)
        put_c(img, round(fx) + 1, round(fy) + 1, "stone", 1)
    # Two corners knocked off: the chip in shadow, a lit broken edge.
    for corner in rnd.sample(((0, 0), (1, 0), (0, 1), (1, 1)), 2):
        sz = rnd.randrange(3, 6)
        for d in range(sz):
            for e in range(sz - d):
                x = d if corner[0] == 0 else N - 1 - d
                y = e if corner[1] == 0 else N - 1 - e
                put_c(img, x, y, "stone", 0.4 if d + e < sz - 1 else 4.4)
    return img


# ------------------------------------------------------------- dressers
@dresser("dress_ruin")
def dress_ruin_hd(img, mask, rnd):
    """An exposed face is where the algae gets light: it grows on the
    shoulders and trails down; the crest is wet; the underside weeps, with a
    drop gathering here and there."""
    for side, bit in (("left", BIT_W), ("right", BIT_E)):
        if mask & bit:
            continue
        s = rnd.randrange(1 << 20)
        run = rnd.randrange(6, 13)
        for y in range(run):
            w = max(1, int(round(3.6 * (1 - y / float(run)) + wave(y, s, period=64))))
            for k in range(w):
                x, py = side_xy(side, k, y)
                put_c(img, x, py, "foliage", (3.0 if side == "left" else 2.0) - y * 0.15)
    if not mask & BIT_N:
        x = 0
        while x < N:
            if rnd.random() < 0.14:
                for k in range(rnd.randrange(2, 5)):
                    put_c(img, x + k, 0, "water", 5.6)
                x += 5
            else:
                x += 1
    if not mask & BIT_S:
        for x in range(N):
            if rnd.random() < 0.3:
                for k in range(rnd.randrange(1, 4)):
                    put_c(img, x, N - 1 - k, "water", 1.2 + k * 0.4)
        for _ in range(2):                               # a drop gathering
            x = rnd.randrange(2, N - 2)
            put_c(img, x, N - 1, "water", 5)
            put_c(img, x, N - 2, "water", 3)


@dresser("dress_ruin_algae")
def dress_ruin_algae_hd(img, mask, rnd):
    """The capped tile: as above, and the mat wraps any exposed shoulder --
    held dark: a bright ledge here would take the frog."""
    dress_ruin_hd(img, mask, rnd)
    for side, bit in (("left", BIT_W), ("right", BIT_E)):
        if mask & bit:
            continue
        run = rnd.randrange(8, 15)
        for y in range(run):
            w = max(1, int(round(4.2 * (1 - y / float(run)))))
            for k in range(w):
                x, py = side_xy(side, k, y)
                put_c(img, x, py, "foliage", (3.4 if side == "left" else 2.4) - y * 0.16)
            x, py = side_xy(side, w, y)
            put_c(img, x, py, "foliage", 1.0)


@dresser("dress_ruin_bg")
def dress_ruin_bg_hd(img, mask, rnd):
    if not mask & BIT_N:
        x = 0
        while x < N:
            if rnd.random() < 0.3:
                for k in range(rnd.randrange(2, 6)):
                    put_c(img, x + k, 0, "stone", 2.1)
                x += 6
            else:
                x += 1


ACCENTS["ruin"] = [lambda i, r: chip(i, r, "stone", 5),
                   lambda i, r: crack_down(i, r, "stone", 5)]


@decoration("d_kelp_hang")
def d_kelp_hang_hd(img, rnd):
    """Kelp trailing from whatever is above the cell: a thin stipe with
    ribbon blades off it in turn."""
    for _ in range(rnd.randrange(1, 3)):
        x = rnd.randrange(3, N - 5)
        run = rnd.randrange(16, N + 1)
        for y in range(run):
            put_c(img, x, y, "wood", 2.4)
            put_c(img, x + 1, y, "wood", 1.0)
            if y % 8 == 4:
                left = (y // 8) % 2 == 0
                leaf(img, x + (0 if left else 1), y, (math.pi - 0.4) if left else 0.4,
                     6, 1.4, "foliage", 2.4, wrap=False)
            if rnd.random() < 0.12:
                x = max(3, min(N - 5, x + rnd.choice((-1, 1))))
    return img


tile(220, 2201)(t_ruin_stone_hd)
tile(221, 2211)(lambda s: t_ruin_stone_hd(s, algae=True))
tile(222, 2221)(t_ruin_wall_hd)
tile(223, 2231)(t_ruin_silt_hd)
tile(225, 2251)(t_ruin_column_hd)
tile(226, 2261)(t_ruin_slab_hd)
tile(227, 2271)(t_ruin_urchin_hd)
tile(228, 2281)(t_ruin_grate_hd)
tile(229, 2291)(t_kelp_hd)
tile(230, 2301)(t_ruin_algae_hd)
tile(231, 2311)(t_ruin_cracked_hd)
