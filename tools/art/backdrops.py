"""Backdrops and UI art: bitmap font, title logo, title background, the
layered parallax planes, the lighting textures, the app icon and the store
icon set."""
import math
import os
import random

from PIL import Image

from .palette import (FONTS, INK, PAL, ROOT, SPRITES, bayer_on, blit, grid,
                      put, step)
from .sprites import K_IDLE

# ---------------------------------------------------------------- font
GLYPHS = {
 'A':["..##..",".#..#.","#....#","######","#....#","#....#","#....#",'......'],
 'B':["#####.","#....#","#....#","#####.","#....#","#....#","#####.",'......'],
 'C':[".####.","#....#","#.....","#.....","#.....","#....#",".####.",'......'],
 'D':["#####.","#....#","#....#","#....#","#....#","#....#","#####.",'......'],
 'E':["######","#.....","#.....","#####.","#.....","#.....","######",'......'],
 'F':["######","#.....","#.....","#####.","#.....","#.....","#.....",'......'],
 'G':[".####.","#....#","#.....","#..###","#....#","#....#",".####.",'......'],
 'H':["#....#","#....#","#....#","######","#....#","#....#","#....#",'......'],
 'I':[".####.","..##..","..##..","..##..","..##..","..##..",".####.",'......'],
 'J':["....##","....##","....##","....##","#...##","#...##",".####.",'......'],
 'K':["#....#","#...#.","#..#..","###...","#..#..","#...#.","#....#",'......'],
 'L':["#.....","#.....","#.....","#.....","#.....","#.....","######",'......'],
 'M':["#....#","##..##","######","#.##.#","#....#","#....#","#....#",'......'],
 'N':["#....#","##...#","#.#..#","#..#.#","#...##","#....#","#....#",'......'],
 'O':[".####.","#....#","#....#","#....#","#....#","#....#",".####.",'......'],
 'P':["#####.","#....#","#....#","#####.","#.....","#.....","#.....",'......'],
 'Q':[".####.","#....#","#....#","#....#","#..#.#","#...#.",".###.#",'......'],
 'R':["#####.","#....#","#....#","#####.","#..#..","#...#.","#....#",'......'],
 'S':[".#####","#.....","#.....",".####.",".....#",".....#","#####.",'......'],
 'T':["######","..##..","..##..","..##..","..##..","..##..","..##..",'......'],
 'U':["#....#","#....#","#....#","#....#","#....#","#....#",".####.",'......'],
 'V':["#....#","#....#","#....#","#....#","#....#",".#..#.","..##..",'......'],
 'W':["#....#","#....#","#....#","#.##.#","######","##..##","#....#",'......'],
 'X':["#....#",".#..#.","..##..","..##..","..##..",".#..#.","#....#",'......'],
 'Y':["#....#","#....#",".#..#.","..##..","..##..","..##..","..##..",'......'],
 'Z':["######","....#.","...#..","..#...",".#....","#.....","######",'......'],
 '0':[".####.","#...##","#..#.#","#.#..#","##...#","#....#",".####.",'......'],
 '1':["..##..",".###..","..##..","..##..","..##..","..##..",".####.",'......'],
 '2':[".####.","#....#",".....#","..###.",".#....","#.....","######",'......'],
 '3':["#####.",".....#",".....#","..###.",".....#",".....#","#####.",'......'],
 '4':["#...#.","#...#.","#...#.","######","....#.","....#.","....#.",'......'],
 '5':["######","#.....","#####.",".....#",".....#","#....#",".####.",'......'],
 '6':[".####.","#.....","#.....","#####.","#....#","#....#",".####.",'......'],
 '7':["######",".....#","....#.","...#..","..#...","..#...","..#...",'......'],
 '8':[".####.","#....#","#....#",".####.","#....#","#....#",".####.",'......'],
 '9':[".####.","#....#","#....#",".#####",".....#",".....#",".####.",'......'],
 '.':["......","......","......","......","......","..##..","..##..",'......'],
 ',':["......","......","......","......","..##..","..##..",".##...",'......'],
 ':':["......","..##..","..##..","......","..##..","..##..","......",'......'],
 '-':["......","......","......","######","......","......","......",'......'],
 '!':["..##..","..##..","..##..","..##..","..##..","......","..##..",'......'],
 '?':[".####.","#....#",".....#","...##.","..#...","......","..##..",'......'],
 "'":["..##..","..##..","......","......","......","......","......",'......'],
 '/':["....#.","...#..","...#..","..#...",".#....",".#....","#.....",'......'],
 '%':["#....#","#...#.","...#..","..#...",".#....","#...##","#...##",'......'],
 '+':["......","..##..","..##..","######","..##..","..##..","......",'......'],
 '(':["...##.","..#...",".#....",".#....",".#....","..#...","...##.",'......'],
 ')':[".##...","...#..","....#.","....#.","....#.","...#..",".##...",'......'],
 '*':["......","#..#..",".###..","######",".###..","#..#..","......",'......'],
 '=':["......","......","######","......","######","......","......",'......'],
 '>':["#.....","..#...","....#.",".....#","....#.","..#...","#.....",'......'],
 '<':[".....#","...#..",".#....","#.....",".#....","...#..",".....#",'......'],
 ' ':["......","......","......","......","......","......","......",'......'],
}
FONT_ORDER = " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ"

def build_font():
    """8x8 cell bitmap font laid out as a 16-column ASCII grid from space (32)."""
    cw, chh, cols = 8, 8, 16
    codes = list(range(32, 32 + 64))
    rows = (len(codes) + cols - 1) // cols
    img = Image.new("RGBA", (cols * cw, rows * chh), (0, 0, 0, 0))
    for i, code in enumerate(codes):
        ch = chr(code)
        g = GLYPHS.get(ch)
        if not g:
            continue
        ox, oy = (i % cols) * cw, (i // cols) * chh
        for y, row in enumerate(g):
            for x, c in enumerate(row):
                if c == '#':
                    img.putpixel((ox + x + 1, oy + y + 1), PAL['w'])
    img.save(os.path.join(FONTS, "font8.png"))
    print("font8.png (%d glyphs)" % len(GLYPHS))

# ---------------------------------------------------------------- title art
# A dusk sky has to cross from night blue to sunset orange, which no single
# material ramp does. Rather than inventing colours for it, this walks a path
# *through* the ramps — water, then purple as the bridge, then ember and gold —
# picked so every neighbouring pair is close enough in luminance that a Bayer
# dither between them reads as a gradient rather than as a seam. Straight
# blue-to-orange does not: it bands.
DUSK = [("water", 0), ("water", 1), ("water", 2), ("water", 3),
        ("purple", 3), ("purple", 4), ("ember", 3), ("ember", 4),
        ("gold", 4), ("gold", 5)]
def build_logo():
    """Title logo: the 8x8 font blown up 5x with a hard dark outline and the
    gold ramp poured down the letterform, dithered between steps, so it reads
    as chunky VGA lettering with a light on it rather than as two flat tones."""
    text = "KAYA"
    scale = 5
    off = 2                      # shadow offset in final pixels
    w = len(text) * 8 * scale
    h = 8 * scale
    img = Image.new("RGBA", (w + off + 4, h + off + 4), (0, 0, 0, 0))

    def stamp(colour_fn, dx, dy):
        for i, ch in enumerate(text):
            g = GLYPHS.get(ch)
            if not g:
                continue
            for y, row in enumerate(g):
                for x, c in enumerate(row):
                    if c != '#':
                        continue
                    for sy in range(scale):
                        for sx in range(scale):
                            px = dx + (i * 8 + x) * scale + sx
                            py = dy + y * scale + sy
                            if 0 <= px < img.width and 0 <= py < img.height:
                                img.putpixel((px, py),
                                             colour_fn(px, py, y * scale + sy))

    def gold_fill(px, py, yy):
        # bright at the top of the glyph, falling to a deep bronze at the foot
        lvl = 6.3 - (yy / float(h)) * 3.1
        lo = int(lvl)
        hi = lo + (1 if bayer_on(px, py, lvl - lo) else 0)
        return step("gold", hi) + (255,)

    # 1) dark green drop shadow, 2) black outline ring, 3) the ramp fill
    stamp(lambda _x, _y, _yy: PAL['g'], 2 + off, 2 + off)
    for ox, oy in ((1, 2), (3, 2), (2, 1), (2, 3)):
        stamp(lambda _x, _y, _yy: PAL['k'], ox, oy)
    stamp(gold_fill, 2, 2)
    img.save(os.path.join(SPRITES, "logo.png"))
    print("logo.png")


# ---------------------------------------------------------------- backdrops
def canopy_layer(img, base_y, colour, seed, amp=14, step_=9, wrap=False):
    """Rounded blobby treeline silhouette across the full width.

    `wrap=True` makes the silhouette repeat seamlessly, which the scrolling
    parallax layers need."""
    rnd = random.Random(seed)
    W, H = img.size
    tops = []
    x = 0
    while x < W:
        r = rnd.randint(step_ - 2, step_ + 4)
        cy = base_y + rnd.randint(-amp, amp // 2)
        tops.append((x, cy, r))
        x += rnd.randint(step_ - 3, step_ + 3)
    for px in range(W):
        top = H
        for (cx, cy, r) in tops:
            dx = px - cx
            if wrap:
                dx = (dx + W // 2) % W - W // 2
            if abs(dx) <= r:
                yy = cy - int((r * r - dx * dx) ** 0.5)
                top = min(top, yy)
        for py in range(max(0, top), H):
            img.putpixel((px, py), colour)


def build_title_bg():
    """Dusk over the canopy.

    The sky is the one place two different ramps have to meet, so it is done the
    way a VGA artist would: `water` climbing towards the horizon, `gold` coming
    up underneath it, and a Bayer cross-fade between the two. No colour in the
    result is anything but a ramp step."""
    W, H = 400, 240
    img = Image.new("RGBA", (W, H), PAL['d'])
    for y in range(H):
        t = min(1.0, y / (H * 0.88))
        pos = t * (len(DUSK) - 1)
        lo = int(pos)
        for x in range(W):
            i = lo + (1 if bayer_on(x, y, pos - lo) else 0)
            img.putpixel((x, y), step(*DUSK[min(i, len(DUSK) - 1)]) + (255,))
    cx, cy, r = 300, 150, 34                     # low sun
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            if not (0 <= x < W and 0 <= y < H):
                continue
            d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            if d <= r:
                lvl = 6.0 if d < r - 4 else 5.0
                img.putpixel((x, y), step("gold", lvl) + (255,))
    rnd = random.Random(9)
    for _ in range(50):
        x, y = rnd.randrange(W), rnd.randrange(60)
        img.putpixel((x, y), PAL['w'])
    canopy_layer(img, 176, step("foliage", 4) + (255,), 101, amp=12, step_=11)
    canopy_layer(img, 198, step("foliage", 2) + (255,), 202, amp=14, step_=13)
    canopy_layer(img, 222, step("foliage", 0) + (255,), 303, amp=10, step_=15)
    rnd = random.Random(77)
    for _ in range(16):                          # hanging vines
        x = rnd.randrange(W)
        ln = rnd.randrange(20, 90)
        for y in range(ln):
            xx = x + int(2 * math.sin(y / 7.0))
            if 0 <= xx < W:
                img.putpixel((xx, y), step("foliage", 1) + (255,))
                if y % 9 == 0 and 0 <= xx + 1 < W:
                    img.putpixel((xx + 1, y), step("foliage", 4) + (255,))
    img.save(os.path.join(SPRITES, "title_bg.png"))
    print("title_bg.png")


# ---------------------------------------------------------------- depth model
# Phase 3. The plan's sentence for this is "distance reads as lower contrast,
# not just smaller", and the old parallax got it exactly backwards: every layer
# was painted at the dark end of `foliage`, so the furthest thing on screen was
# also the highest-contrast thing on screen — a black wall behind a lit jungle.
#
# So depth is not a brush decision here, it is a property of the *plane* a brush
# paints into. A Plane owns a slice of one ramp — its `window` — and generators
# paint in **material value**: 0 is the shadowed side of a thing, 1 the lit
# side, and the plane maps that onto its window when it renders. Two
# consequences, both of them the point:
#
#   * The width of the window is the plane's whole contrast budget. A far plane
#     with a 1.2-step window cannot out-contrast a near plane with 2.4, however
#     it is drawn, so a later change to the art cannot quietly break the depth.
#   * Distance can be *brighter*. Haze lightens what is behind it; only the
#     amount of shading available falls off. That is what the old strips could
#     not express and it is most of what reads as air.
#
# The buffer is kept as float values rather than pixels so `boost()` can lift
# what is already painted (light shafts, mist) instead of stamping over it.
class Plane:
    """One depth plane of a backdrop: a value buffer plus its slice of a ramp."""

    def __init__(self, ramp, window, opaque=False, w=400, h=240, windows=None):
        self.ramp = ramp
        self.lo, self.hi = window
        # Per-material exception to the plane's window. Haze acts on the light a
        # material reflects, and a forest canopy seen through the same air as a
        # cloud is nothing like as bright as the cloud: one window for both puts
        # a glaring green slab under the cloud sea. Sparingly — the plane's own
        # window is what holds the depth together.
        self.windows = windows or {}
        self.opaque = opaque
        self.w, self.h = w, h
        self.val = [[None] * w for _ in range(h)]
        self.mat = [[None] * w for _ in range(h)]   # per-pixel ramp override

    def contrast(self):
        """The plane's contrast budget, in ramp steps."""
        return self.hi - self.lo

    def set(self, x, y, v, ramp=None):
        """Paint material value `v` at (x, y). Wraps in x: every backdrop layer
        is one screen wide and has to tile seamlessly as the camera flips."""
        x %= self.w
        if 0 <= y < self.h:
            self.val[y][x] = v
            self.mat[y][x] = ramp

    def boost(self, x, y, dv, frac=1.0):
        """Lift what is already there, dithered. Light shafts and mist are done
        this way so they read as air over the art rather than as paint on it."""
        x %= self.w
        if not (0 <= y < self.h) or self.val[y][x] is None:
            return
        if frac >= 1.0 or bayer_on(x, y, frac):
            self.val[y][x] = min(1.0, self.val[y][x] + dv)

    def window_for(self, ramp):
        return self.windows.get(ramp, (self.lo, self.hi))

    def render(self):
        img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        for y in range(self.h):
            for x in range(self.w):
                v = self.val[y][x]
                if v is None:
                    if not self.opaque:
                        continue
                    v = 0.0
                ramp = self.mat[y][x] or self.ramp
                lo, hi = self.window_for(ramp)
                put(img, x, y, ramp, lo + max(0.0, min(1.0, v)) * (hi - lo))
        return img


# ---------------------------------------------------------------- brushes
def vband(p, y0, y1, v0, v1, ramp=None, curve=1.0):
    """Vertical gradient across the full width."""
    for y in range(max(0, y0), min(p.h, y1)):
        t = (y - y0) / float(max(1, y1 - y0))
        v = v0 + (v1 - v0) * (t ** curve)
        for x in range(p.w):
            p.set(x, y, v, ramp)


def ridge(p, base_y, v, seed, amp=14, step=11, thickness=None, ramp=None,
          crest=0.0, fade=0.0, rough=0.0):
    """A rolling silhouette — treeline, hill, cloud bank, cave roof.

    Wraps in x by construction, so the horizon does not jump at a screen flip.
    `crest` brightens the topmost pixels, which is what makes a distant ridge
    read as lit from above rather than as a cut-out; `fade` darkens with depth
    into the band so it does not come out as a slab of one value, which is the
    single thing that most gives a silhouette away as generated."""
    rnd = random.Random(seed)
    lumps = []
    x = 0
    while x < p.w:
        r = rnd.randint(step - 2, step + 5)
        lumps.append((x, base_y + rnd.randint(-amp, amp // 2), r))
        x += rnd.randint(step - 3, step + 3)
    for px in range(p.w):
        top = p.h
        for (cx, cy, r) in lumps:
            dx = (px - cx + p.w // 2) % p.w - p.w // 2
            if abs(dx) <= r:
                top = min(top, cy - int((r * r - dx * dx) ** 0.5))
        if top >= p.h:
            continue
        end = p.h if thickness is None else min(p.h, max(0, top) + thickness)
        depth = max(1, end - max(0, top))
        for py in range(max(0, top), end):
            d = py - top
            vv = v + (crest if d < 2 else 0.0) - fade * (d / float(depth))
            if rough:
                vv += rough * (rnd.random() - 0.5)
            p.set(px, py, vv, ramp)


def canopy(p, base_y, v, seed, count=16, rx=(14, 30), ry=(7, 14), spread=22,
           ramp=None):
    """A mass of foliage rather than a silhouette: overlapping crowns strung
    along a line, which is what a distant forest actually looks like. `ridge`
    gives an edge; this gives the body behind it."""
    rnd = random.Random(seed)
    for i in range(count):
        cx = int(i * (p.w / float(count)) + rnd.randint(-12, 12))
        cy = base_y + rnd.randint(-spread, spread)
        crown(p, cx, cy, rnd.randint(*rx), rnd.randint(*ry),
              v + rnd.uniform(-0.06, 0.06), seed * 7 + i, lumps=7, ramp=ramp)


def trunk(p, x, top, bottom, width, v, ramp=None, lean=0.0):
    """A tree trunk with a lit shoulder and an occluded side. The bevel runs
    upper-left like everything else in the game (palette.LIGHT)."""
    for y in range(max(0, top), min(p.h, bottom)):
        cx = x + lean * (y - top)
        for k in range(width):
            t = k / float(max(1, width - 1))
            shade = v + (0.30 if t < 0.28 else (-0.26 if t > 0.72 else 0.0))
            if k == 0 or k == width - 1:
                shade = v - 0.34
            p.set(int(cx) + k, y, shade, ramp)


def crown(p, cx, cy, rx, ry, v, seed, lumps=7, ramp=None):
    """A leaf mass: overlapping blobs, lit on their upper-left."""
    rnd = random.Random(seed)
    for _ in range(lumps):
        ox = rnd.randint(-rx, rx)
        oy = rnd.randint(-ry // 2, ry // 2)
        r = rnd.randint(max(3, rx // 3), max(4, rx // 2))
        for y in range(cy + oy - r, cy + oy + r + 1):
            for x in range(cx + ox - r, cx + ox + r + 1):
                dx, dy = (x - cx - ox) / float(r), (y - cy - oy) / float(r)
                d = dx * dx + dy * dy
                if d > 1.0:
                    continue
                facing = -dx - dy
                p.set(x, y, v + (0.26 if facing > 0.55 else
                                 (-0.22 if facing < -0.6 else 0.0)), ramp)


def hang(p, x, y0, length, v, seed, ramp=None):
    """A hanging vine or root, drifting as it falls."""
    rnd = random.Random(seed)
    xx = float(x)
    for i in range(length):
        y = y0 + i
        if y >= p.h:
            break
        xx += math.sin(i / 6.0 + seed) * 0.22
        p.set(int(xx), y, v, ramp)
        if i % 11 == 5:
            p.set(int(xx) + 1, y, v + 0.3, ramp)
            p.set(int(xx) - 1, y, v - 0.2, ramp)


def cloud(p, cx, cy, rx, ry, v, seed, ramp=None):
    """A cloud bank: stacked lumps, bright on top, shaded underneath."""
    rnd = random.Random(seed)
    for _ in range(9):
        ox = rnd.randint(-rx, rx)
        r = rnd.randint(max(4, ry // 2), max(6, ry))
        oy = rnd.randint(-ry // 3, ry // 3)
        for y in range(cy + oy - r, cy + oy + r + 1):
            for x in range(cx + ox - r, cx + ox + r + 1):
                dx = (x - cx - ox) / float(r)
                dy = (y - cy - oy) / float(r)
                if dx * dx + dy * dy > 1.0:
                    continue
                p.set(x, y, v + (0.30 if dy < -0.35 else
                                 (-0.28 if dy > 0.3 else 0.05)), ramp)


def shafts(p, count, seed, dv=0.26, slope=3, width=(10, 26), top=0, reach=1.0):
    """Slanted light coming down through the canopy or the water.

    Dithered, and applied with `boost`, so it lifts whatever it crosses instead
    of painting a stripe over it."""
    rnd = random.Random(seed)
    for _ in range(count):
        sx = rnd.randrange(p.w)
        wdt = rnd.randrange(*width)
        span = int(p.h * reach)
        for y in range(top, min(p.h, top + span)):
            fade = 1.0 - (y - top) / float(max(1, span))
            for x in range(sx + y // slope, sx + y // slope + wdt):
                p.boost(x, y, dv * fade, 0.5 * fade + 0.2)


def mist(p, y0, thickness, amount, dv=0.22):
    """A horizontal haze band: the cheapest depth cue there is."""
    for y in range(y0, min(p.h, y0 + thickness)):
        fade = 1.0 - abs((y - y0) - thickness / 2.0) / (thickness / 2.0)
        for x in range(p.w):
            p.boost(x, y, dv * fade, amount * fade)


def grain(p, seed, count, dv=0.12):
    """Loose noise so a gradient does not read as a flat wash."""
    rnd = random.Random(seed)
    for _ in range(count):
        p.boost(rnd.randrange(p.w), rnd.randrange(p.h),
                dv if rnd.random() < 0.5 else -dv)


def horizon_haze(p, y0, y1, v0, v1, ramp=None, curve=1.0, bands=5):
    """Phase C, docs/plan-art-motion.md: "horizon gradient banding via dither
    on the far planes." A dithered gradient like `vband`, except it steps
    through `bands` discrete levels rather than a continuous curve — the
    classic banded-sunset look, each band Bayer-dithered into the next at its
    boundary. And unlike `vband` it only fills pixels the plane has not
    already painted: called after a world's colonnade/ridge/comb is drawn, it
    shows up in the gaps between them — behind an arcade's arches, through a
    comb's cells — as atmosphere, and never overwrites a silhouette."""
    for y in range(max(0, y0), min(p.h, y1)):
        t = (y - y0) / float(max(1, y1 - y0))
        step_t = round(t * bands) / float(bands)
        v = v0 + (v1 - v0) * (step_t ** curve)
        for x in range(p.w):
            if p.val[y][x] is None:
                p.set(x, y, v, ramp)


def sky_path(p, path, curve=1.0):
    """Vertical gradient that walks a path *through* several ramps.

    Phase 1's finding, reused: a sky that has to cross hues bands if you dither
    straight between the ends, so the crossing is routed as a list of
    neighbouring (ramp, value) pairs close enough in luminance to mix."""
    for y in range(p.h):
        t = (y / float(p.h - 1)) ** curve
        pos = t * (len(path) - 1)
        lo = int(pos)
        hi = min(lo + 1, len(path) - 1)
        for x in range(p.w):
            e = path[hi] if bayer_on(x, y, pos - lo) else path[lo]
            p.set(x, y, e[1], e[0])


def colonnade(p, x0, spacing, top, bottom, width, v, seed, ramp=None,
              arch=True):
    """A run of columns, optionally with the arches still standing on them.

    SUNKEN RUINS is architecture rather than landscape, and architecture is the
    one backdrop subject where *regularity* is the read — so this is the only
    brush here that repeats on a fixed pitch."""
    rnd = random.Random(seed)
    x = x0
    while x < p.w + spacing:
        h = bottom - rnd.randint(0, 22)                  # some are broken off
        trunk(p, x, top + rnd.randint(0, 10), h, width, v, ramp)
        if arch and rnd.random() < 0.7:
            r = spacing // 2
            for a in range(-r, r + 1):
                dy = int((1.0 - (a / float(r)) ** 2) ** 0.5 * (r * 0.55))
                for t in range(3):
                    p.set(x + width // 2 + r + a, top + 10 - dy + t,
                          v + (0.26 if t == 0 else -0.16), ramp)
        x += spacing


def spires(p, base_y, count, v, seed, ramp=None, height=(40, 130),
           width=(10, 34)):
    """Jagged volcanic-glass teeth. Lit on the upper-left face and falling away
    to the right, like every other solid in this game."""
    rnd = random.Random(seed)
    for i in range(count):
        cx = int(i * (p.w / float(count)) + rnd.randint(-14, 14))
        h = rnd.randint(*height)
        half = rnd.randint(*width) // 2
        lean = rnd.uniform(-0.18, 0.18)
        for y in range(max(0, base_y - h), min(p.h, base_y + 6)):
            t = (base_y - y) / float(h)
            if t < 0:
                continue
            wdt = half * (1.0 - t ** 0.8)
            sx = cx + int(lean * (base_y - y))
            for x in range(int(sx - wdt), int(sx + wdt) + 1):
                u = (x - sx) / max(wdt, 0.8)
                p.set(x, y, v + (0.34 if u < -0.35 else
                                 (-0.26 if u > 0.45 else 0.0)), ramp)


def glow(p, cx, cy, r, dv, seed, frac=0.9):
    """A pool of light in the backdrop, dithered outward. `boost`-based, so it
    lifts whatever is already painted rather than stamping a disc on it."""
    rnd = random.Random(seed)
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            d = math.hypot(x - cx, y - cy) / float(r)
            if d > 1.0:
                continue
            k = (1.0 - d) ** 1.6
            p.boost(x, y, dv * k, min(1.0, frac * k + 0.08))


def build_backdrops():
    """The parallax planes of every world: tools/art/parallax_worlds.py paints
    them (Kaya Refit phase 3), sized by data/parallax.json.

    The world names are an interface: data/ambience.json has to name the same
    string, or `Ambience.for_level()` resolves a level to a backdrop that has
    no art. tests/test_art_depth.gd checks exactly that, in both directions.
    """
    from . import parallax_worlds
    made = parallax_worlds.build(SPRITES)
    for world, planes in sorted(made.items()):
        print("bg_%s_{%s}.png  %s  contrast budget %s steps" % (
            world, ",".join(planes), " ".join("%dx%d" % (p.w, p.h) for p in planes.values()),
            "/".join("%.1f" % planes[n].contrast() for n in ("sky", "far", "near"))))


# ---------------------------------------------------------------- light art
# The lighting decision (docs/art-direction.md, phase 3) came down on the side
# of additive light pools over Light2D. These are the two textures it needs.
def build_light_art():
    """A light pool and a screen vignette, both dithered rather than smooth.

    A smooth 8-bit falloff over 16-colour-per-material pixel art looks like a
    modern glow filter dropped on a DOS game. VGA artists had the same problem
    and solved it the same way as everything else: quantise the falloff into a
    few bands and Bayer the boundaries. Dithering is also what lets the pools be
    drawn additively without the banding a straight gradient would show on the
    flat backdrop planes."""
    S = 96
    pool = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    r = S / 2.0
    for y in range(S):
        for x in range(S):
            d = math.hypot(x - r + 0.5, y - r + 0.5) / r
            if d >= 1.0:
                continue
            f = (1.0 - d) ** 1.7               # falloff
            lvl = f * 6.0                      # six alpha bands
            band = int(lvl) + (1 if bayer_on(x, y, lvl - int(lvl)) else 0)
            if band <= 0:
                continue
            a = int(255 * min(1.0, band / 6.0) * 0.72)
            pool.putpixel((x, y), step("metal", 6) + (a,))
    pool.save(os.path.join(SPRITES, "light_pool.png"))

    W, H = 400, 240
    vig = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for y in range(H):
        for x in range(W):
            nx = (x - W / 2.0) / (W / 2.0)
            ny = (y - H / 2.0) / (H / 2.0)
            d = max(0.0, math.hypot(nx * 0.92, ny) - 0.42) / 0.72
            lvl = min(1.0, d) ** 1.6 * 5.0
            band = int(lvl) + (1 if bayer_on(x, y, lvl - int(lvl)) else 0)
            if band <= 0:
                continue
            vig.putpixel((x, y), INK + (int(255 * min(1.0, band / 5.0)),))
    vig.save(os.path.join(SPRITES, "vignette.png"))
    print("light_pool.png vignette.png")


def build_store_icons():
    """Store/app icons at every size the export presets ask for, plus a boot
    splash. All derived from the same 128px roundel so they stay consistent."""
    src = Image.open(os.path.join(SPRITES, "icon.png")).convert("RGBA")
    out = os.path.join(ROOT, "export", "icons")
    os.makedirs(out, exist_ok=True)
    for size in (1024, 512, 256, 192, 180, 167, 152, 144, 120, 114, 108, 87,
                 80, 76, 72, 60, 58, 40, 29, 20):
        # Nearest for exact multiples of 128 keeps the pixels crisp; otherwise
        # box-filter so small icons do not alias into mush.
        mode = Image.NEAREST if size % 128 == 0 else Image.LANCZOS
        img = src.resize((size, size), mode)
        if size >= 40:
            flat = Image.new("RGBA", (size, size), step("foliage", 1) + (255,))
            flat.alpha_composite(img)
            img = flat
        img.save(os.path.join(out, "icon_%d.png" % size))
    # Boot splash: the logo centred on the palette background.
    logo = Image.open(os.path.join(SPRITES, "logo.png")).convert("RGBA")
    sp = Image.new("RGBA", (640, 384), INK + (255,))
    big = logo.resize((logo.width * 2, logo.height * 2), Image.NEAREST)
    sp.alpha_composite(big, ((sp.width - big.width) // 2, (sp.height - big.height) // 2 - 20))
    sp.save(os.path.join(SPRITES, "splash.png"))
    print("store icons + splash")


def build_icon():
    """128x128 app icon: Kaya's head on a leaf roundel."""
    S = 128
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    for y in range(S):
        for x in range(S):
            d = math.hypot(x - S / 2 + 0.5, y - S / 2 + 0.5)
            if d < 60:
                img.putpixel((x, y), PAL['g'])
            if d < 55:
                img.putpixel((x, y), PAL['G'])
            if d < 48:
                img.putpixel((x, y), PAL['d'])
    head = [r[:16] for r in K_IDLE[0:12]]
    tmp = Image.new("RGBA", (16, 12), (0, 0, 0, 0))
    blit(tmp, 0, 0, grid(head))
    tmp = tmp.resize((16 * 6, 12 * 6), Image.NEAREST)
    img.alpha_composite(tmp, ((S - tmp.width) // 2, (S - tmp.height) // 2 - 4))
    img.save(os.path.join(SPRITES, "icon.png"))
    print("icon.png")


