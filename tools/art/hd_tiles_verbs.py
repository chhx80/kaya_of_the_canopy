"""The movement verbs (ids 200-215), drawn natively at 2x.

Currents, drafts and the walls the blade can open are shared by worlds 2-4,
and each is built on a jungle material (water, stone, dirt), so they are
redrawn here on the jungle's 2x painters rather than by any one world. Same
rule as at 1x: a verb you cannot SEE is a verb that reads as a bug, so each
one announces itself -- the direction a current pushes, the way air moves,
the crack you can break.
"""
import math
import random

from .hd_tilekit import N, blob, get, level_of, new, pit, put, put_c, tile
from .hd_tiles_jungle import t_dirt_hd, t_stone_hd, t_water_hd


def _chevron(img, cx, cy, dx, dy, size, fast):
    """A chevron pointing the way the water pushes: a bright leading edge,
    a body a step down, a trail fading behind. Fast water carries a second
    one close behind the first, so the two speeds differ in kind, not just
    in brightness."""
    head = ("metal", 6) if fast else ("water", 6)
    for rep in range(2 if fast else 1):
        off = -rep * 4
        for t in range(-size, size + 1):
            u = off - abs(t) * 0.9
            for back, (ramp, lvl) in enumerate((head, ("water", 6), ("water", 5))):
                uu = u - back
                if dx:
                    x, y = cx + uu * dx, cy + t
                else:
                    x, y = cx + t, cy + uu * dy
                m = level_of(get(img, x, y))
                if back == 2 and m and m[1] >= 5:
                    continue
                put(img, round(x), round(y), ramp, lvl)


def t_current_hd(seed, dx, dy, fast=False):
    img = t_water_hd(seed)
    rnd = random.Random(seed + 7)
    n = 3 if fast else 2
    for i in range(n):
        along = rnd.uniform(0, N)
        across = (i * N / float(n) + rnd.uniform(3, 7)) % N
        if dx:
            _chevron(img, along, across, dx, 0, 4 if fast else 5, fast)
        else:
            _chevron(img, across, along, 0, dy, 4 if fast else 5, fast)
    return img


def t_draft_hd(seed, dy, strong=False, sideways=0):
    """Moving air: thin wisps that taper at both ends, brightest at the head
    (the way the air goes) and curling a little as they run. Transparent, in
    front of the backdrop; a strong draft has more of them, and denser."""
    img = new(0)
    rnd = random.Random(seed)
    for _ in range(6 if strong else 4):
        x, y = rnd.uniform(0, N), rnd.uniform(0, N)
        run = rnd.randrange(9, 18)
        ph = rnd.uniform(0, 2 * math.pi)
        for k in range(run):
            t = k / float(run - 1)
            a = (170 if strong else 125) * (math.sin(math.pi * t) ** 0.6)
            lvl = 4.4 + 2.2 * t
            wob = 0.9 * math.sin(k * 0.45 + ph)
            if sideways:
                px, py = x + k * sideways, y + wob
            else:
                px, py = x + wob, y + k * (1 if dy > 0 else -1)
            if a > 20:
                put(img, round(px), round(py), "cloth", lvl, alpha=int(a))
                fx, fy = (0, 1) if sideways else (1, 0)
                put(img, round(px) + fx, round(py) + fy, "cloth", lvl - 1, alpha=int(a * 0.6))
    return img


def _bold_crack(img, rnd, ramp, x, y, length):
    """A crack that says 'breakable': a dark core that opens to two texels
    in its middle third, a lit lip under it, and a branch."""
    for k in range(length):
        wide = length // 5 <= k < 4 * length // 5
        put(img, x, y, ramp, 0)
        put(img, x - 1, y, ramp, 1)
        if wide:
            put(img, x + 1, y, ramp, 0)
        put(img, x, y + 1, ramp, 5)
        if wide:
            put(img, x + 1, y + 1, ramp, 5)
        if k == length // 2:
            bx, by = x, y
            for j in range(rnd.randrange(3, 7)):
                bx += rnd.choice((-1, 1))
                by += 1
                put(img, bx, by, ramp, 0)
                put(img, bx + 1, by, ramp, 4)
        x += rnd.choice((0, 1, 1))
        y += rnd.choice((-1, 0, 1, 1))


def t_cracked_hd(seed, base):
    img = t_stone_hd(seed) if base == "stone" else t_dirt_hd(seed)
    rnd = random.Random(seed + 3)
    ramp = "stone" if base == "stone" else "dirt"
    for i in range(3):
        _bold_crack(img, rnd, ramp, rnd.randrange(3, N - 12), 2 + i * 9 + rnd.randrange(4),
                    rnd.randrange(14, 22))
    return img


def t_termite_wall_hd(seed):
    img = t_dirt_hd(seed)
    rnd = random.Random(seed + 5)
    for _ in range(14):
        pit(img, "dirt", rnd.uniform(0, N), rnd.uniform(0, N), rnd.uniform(1.8, 3.4),
            rnd.uniform(1.6, 2.8), 1.0)
    return img


def t_luminous_wall_hd(seed):
    """Breakable, and the only light in a dark room: gold veins with a white-
    hot core, a halo a step down on each side, and a crystal where two meet."""
    img = t_stone_hd(seed)
    rnd = random.Random(seed + 9)
    for _ in range(4):
        x, y = rnd.uniform(4, N - 4), rnd.uniform(4, N - 4)
        a = rnd.uniform(0, math.pi)
        for k in range(rnd.randrange(14, 24)):
            x += math.cos(a)
            y += math.sin(a) * 0.6
            a += rnd.uniform(-0.4, 0.4)
            put(img, round(x), round(y) - 1, "gold", 4)
            put(img, round(x) + 1, round(y) - 1, "gold", 3)
            put(img, round(x), round(y), "gold", 6)
            put(img, round(x) + 1, round(y), "gold", 5)
            put(img, round(x), round(y) + 1, "gold", 4)
        put(img, round(x), round(y), "gold", 6)
        put(img, round(x) + 1, round(y), "gold", 5)
        put(img, round(x), round(y) - 1, "gold", 6)
    return img


def t_rubble_hd(seed):
    """What a broken wall leaves: a heap of broken stones, each lit on its
    upper left, the ones behind darker than the ones in front, and grit."""
    img = new(0)
    rnd = random.Random(seed)
    for x in range(1, N - 1):                            # a low mound of grit
        h = int(round(3 + 2.5 * math.sin(math.pi * x / N) + rnd.uniform(-0.6, 0.6)))
        for k in range(h):
            put_c(img, x, N - 1 - k, "dirt", 2.2 + (1.4 if k == h - 1 else 0) - k * 0.1)
    stones = [((i + 0.5) * N / 9.0 + rnd.uniform(-1.5, 1.5),
               rnd.uniform(22, N - 4) - 3 * math.sin(math.pi * (i + 0.5) / 9.0))
              for i in range(9)]
    for x, y in sorted(stones, key=lambda s: s[1]):
        blob(img, "stone", x, y, rnd.uniform(2.2, 3.6), rnd.uniform(1.7, 2.6),
             2.2 + (y - 18) * 0.1, wrap=False)
    for _ in range(10):
        put_c(img, rnd.randrange(2, N - 2), rnd.randrange(N - 5, N), "dirt", 4)
    return img


tile(200, 2001)(lambda s: t_current_hd(s, 1, 0))
tile(201, 2011)(lambda s: t_current_hd(s, -1, 0))
tile(202, 2021)(lambda s: t_current_hd(s, 0, -1))
tile(203, 2031)(lambda s: t_current_hd(s, 0, 1))
tile(204, 2041)(lambda s: t_current_hd(s, 1, 0, fast=True))
tile(205, 2051)(lambda s: t_current_hd(s, -1, 0, fast=True))
tile(206, 2061)(lambda s: t_draft_hd(s, -1))
tile(207, 2071)(lambda s: t_draft_hd(s, -1, strong=True))
tile(208, 2081)(lambda s: t_draft_hd(s, 1))
tile(209, 2091)(lambda s: t_draft_hd(s, 0, sideways=1))
tile(210, 2101)(lambda s: t_draft_hd(s, 0, sideways=-1))
tile(211, 2111)(lambda s: t_cracked_hd(s, "stone"))
tile(212, 2121)(lambda s: t_cracked_hd(s, "dirt"))
tile(213, 2131)(t_termite_wall_hd)
tile(214, 2141)(t_luminous_wall_hd)
tile(215, 2151)(t_rubble_hd)
