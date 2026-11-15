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
            cx = rnd.uniform(0, N)
            ellipse(img, "foliage", cx, course * 16 + 13.5, rnd.uniform(2.5, 4.5), 1.6, 1.4)
            put(img, cx, course * 16 + 12, "foliage", 2.2)
    crack(img, "stone", rnd.randrange(3, 14), rnd.randrange(4, 10), 10, 2.5, rnd)
    if algae:
        # The ledge-top read. Dark on purpose (foliage 1-3): a bright cap would
        # take the frog standing on it. The only bright thing is a broken wet
        # line along the crest, a texel deep.
        s = rnd.randrange(1 << 20)
        depth = []
        for x in range(N):
            h = 4 + int(round(2 * (wave(x, s) * 0.5 + 0.5))) + (1 if rnd.random() < 0.3 else 0)
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
    for _ in range(2):                                   # a drowned-green bloom, flat
        cx, cy = rnd.uniform(0, N), rnd.uniform(0, N)
        ellipse(img, "foliage", cx, cy, rnd.uniform(5, 9), rnd.uniform(3, 5), 1)
        ellipse(img, "foliage", cx - 1, cy - 1, rnd.uniform(2, 4), rnd.uniform(1.5, 2.5), 2)
    for _ in range(12):
        put(img, rnd.randrange(N), rnd.randrange(N), "stone", rnd.choice((0, 2)))
    return img


def t_ruin_silt_hd(seed):
    """Cold silt: stone-grey mud with the warm earth coming through it, shell
    grit (each a tiny lit arc), standing water in the hollows, worm casts."""
    rnd = random.Random(seed)
    img = fill(new(255), "stone", 1.9, rnd, grain=0.26)
    for _ in range(6):                                   # the mud coming through
        ellipse(img, "dirt", rnd.uniform(0, N), rnd.uniform(0, N), rnd.uniform(3.0, 5.5),
                rnd.uniform(1.8, 3.2), rnd.choice((1, 2)))
    for _ in range(3):                                   # water in a hollow, lit far lip
        cx, cy = rnd.uniform(0, N), rnd.uniform(0, N)
        rx, ry = rnd.uniform(3.0, 5.0), rnd.uniform(1.4, 2.4)
        ellipse(img, "water", cx, cy, rx, ry, 2)
        for x in range(int(cx - rx * 0.6), int(cx + rx * 0.6)):
            put(img, x, cy + ry, "stone", 3)
    for _ in range(7):                                   # shells
        x, y = rnd.randrange(N), rnd.randrange(N)
        put(img, x, y, "stone", 4)
        put(img, x + 1, y - 1, "stone", 5)
        put(img, x + 2, y, "stone", 3)
        put(img, x + 1, y + 1, "stone", 1)
    for _ in range(2):
        ellipse(img, "foliage", rnd.uniform(0, N), rnd.uniform(0, N), 2.2, 1.4, 1.6)
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
    for x in range(N):
        put_c(img, x, 26, "dirt", 2.6 + rnd.uniform(-0.3, 0.3))
        put_c(img, x, 27, "dirt", 2.0)
        put_c(img, x, 28, "dirt", 1.4)
        put_c(img, x, 29, "dirt", 1.0)
        ink(img, x, 30)
    for (cx, cy, r) in ((6.0, 20.0, 6.0), (17.0, 22.0, 5.0), (26.5, 19.0, 6.6)):
        for ang in (200, 222, 245, 270, 295, 318, 340):
            a = math.radians(ang + rnd.randrange(-7, 8))
            ln = r + 5 + rnd.uniform(0, 2)
            k = r * 0.6
            while k < ln:
                px, py = cx + math.cos(a) * k, cy + math.sin(a) * k
                tip = k > ln - 2.5
                put_c(img, round(px), round(py), "metal", 6 if tip else 3.4)
                if not tip:
                    put_c(img, round(px - math.sin(a)), round(py + math.cos(a)), "metal", 1.6)
                k += 0.7
        blob(img, "purple", cx, cy, r, r * 0.85, 1.4, lit=1.8, dark=1.0, wrap=False)
        for a in range(200, 345, 24):                    # the ribbed test
            put_c(img, round(cx + math.cos(math.radians(a)) * r * 0.55),
                  round(cy + math.sin(math.radians(a)) * r * 0.5), "purple", 4)
        put_c(img, round(cx - r * 0.4), round(cy - r * 0.35), "water", 6)
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
    for _ in range(6):
        x, y = rnd.choice((0, 11, 22)) + rnd.randrange(3), rnd.randrange(N)
        if rnd.random() < 0.5:
            x, y = y, x
        put(img, x, y, "ember", 2)
        put(img, x, y + 1, "ember", 1)
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
    for x in range(N):
        put(img, x, 15, "stone", 0.6)
        put(img, x, 16, "stone", 4.2)
    yy = 5
    for x in range(N):
        yy = max(3, min(26, yy + rnd.choice((-1, 0, 0, 1, 1, 1))))
        ink(img, x, yy)
        ink(img, x, yy + 1)
        put(img, x, yy + 2, "stone", 4.6)
        put(img, x, yy - 1, "stone", 1.0)
    for corner in ((0, 0), (N - 3, 0), (0, N - 3), (N - 3, N - 3)):
        for dx in range(3):
            for dy in range(3):
                if dx + dy < 3 and rnd.random() < 0.8:
                    put_c(img, corner[0] + dx, corner[1] + dy, "stone", 0.8)
    for _ in range(3):
        crack(img, "stone", rnd.randrange(4, 26), rnd.randrange(18, 26), 8, 2.4, rnd,
              drift=(-1, 0, 1))
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
