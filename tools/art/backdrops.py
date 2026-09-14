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


# ---------------------------------------------------------------- the worlds
# A world is three planes, furthest first. Only the two worlds whose parallax is
# actually on screen are built — see build_backdrops().
def _jungle():
    # Sky: the air itself, blue-grey rather than green. The foreground is warm
    # and saturated, so putting the distance on a cool ramp separates them by
    # hue as well as by contrast, and no amount of green in front of it can be
    # mistaken for part of the backdrop.
    sky = Plane("water", (2.3, 4.4), opaque=True)
    vband(sky, 0, 156, 1.0, 0.26, curve=0.8)
    vband(sky, 156, 240, 0.26, 0.12)
    shafts(sky, 5, 41, dv=0.20, slope=4, width=(16, 40), reach=0.8)
    canopy(sky, 168, 0.26, 4011, count=13, rx=(20, 40), ry=(9, 16), spread=12,
           ramp="foliage")
    ridge(sky, 156, 0.30, 4012, amp=13, step=17, ramp="foliage", crest=0.16,
          fade=0.24, rough=0.05)
    mist(sky, 138, 30, 0.62)
    grain(sky, 4013, 1600)

    # Far: a receding stand of trees standing out of a canopy mass. One-and-a-
    # bit steps of contrast to build them from, which is the whole point — they
    # cannot shout.
    far = Plane("foliage", (1.5, 2.7))
    rnd = random.Random(4020)
    for i in range(9):
        x = (i * 43 + rnd.randrange(22)) % 400
        base = rnd.randrange(168, 206)
        top = base - rnd.randrange(84, 136)
        w = rnd.randrange(4, 8)
        trunk(far, x, top + 12, base, w, 0.40)
        crown(far, x + w // 2, top + 6, rnd.randrange(20, 34),
              rnd.randrange(12, 19), 0.60, 4030 + i, lumps=9)
    canopy(far, 196, 0.44, 4040, count=14, rx=(18, 34), ry=(10, 18), spread=14)
    ridge(far, 206, 0.30, 4041, amp=8, step=15, thickness=44, crest=0.22,
          fade=0.30, rough=0.06)
    mist(far, 156, 34, 0.45)
    shafts(far, 4, 4050, dv=0.18, slope=4, width=(12, 30), reach=0.9)

    # Near: the frame. The widest window of the three, kept at the dark end of
    # the ramp — it is a silhouette, so its contrast is against the plane behind
    # it rather than within itself, and nothing in it is bright enough to
    # compete with a tile the player might stand on.
    near = Plane("foliage", (0.0, 2.2))
    rnd = random.Random(4060)
    for i in range(4):
        x = (i * 97 + rnd.randrange(52)) % 400
        w = rnd.randrange(14, 22)
        trunk(near, x, 0, 240, w, 0.46, lean=rnd.choice((-0.02, 0.0, 0.03)))
        for _ in range(3):                       # branches and their leaves
            by = rnd.randrange(40, 200)
            side = rnd.choice((-1, 1))
            span = rnd.randrange(16, 34)
            for k in range(span):
                p_y = by + k // 4
                for t in range(max(1, 4 - k // 9)):
                    near.set(x + w // 2 + side * k, p_y + t, 0.40)
            crown(near, x + w // 2 + side * (span + 4), by + span // 4,
                  rnd.randrange(13, 20), rnd.randrange(8, 13), 0.62, 4070 + i)
    # Leaf fringe over the top edge: crowns, not a bar, so the frame has a
    # ragged underside for the level to show through.
    canopy(near, 4, 0.56, 4090, count=11, rx=(16, 30), ry=(9, 16), spread=6)
    for i in range(9):                           # vines off that fringe
        hang(near, rnd.randrange(400), rnd.randrange(6, 22),
             rnd.randrange(28, 120), 0.34, 4080 + i)
    return {"sky": sky, "far": far, "near": near}


def _sky():
    # SKY BRANCH is the bright level, and the one place the backdrop is the
    # loudest thing on screen. Two rules keep it playable: the top stays deep
    # enough for the white HUD to sit on, and the pale end is put at the bottom
    # where the tiles that overlap it are darkest.
    sky = Plane("water", (3.0, 6.5), opaque=True)
    sky_path(sky, [("water", 0.40), ("water", 0.56), ("water", 0.70),
                   ("water", 0.82), ("metal", 0.70), ("metal", 0.82),
                   ("metal", 0.92), ("metal", 1.0)], curve=1.25)
    rnd = random.Random(5010)
    for i in range(6):                           # high thin cirrus
        cloud(sky, rnd.randrange(400), rnd.randrange(24, 92),
              rnd.randrange(26, 52), rnd.randrange(3, 6), 0.84, 5020 + i,
              ramp="metal")
    grain(sky, 5030, 1100, dv=0.07)

    # Far: the cloud sea, and the canopy a very long way below it. The canopy is
    # the furthest green in the game and is deliberately the flattest: two
    # steps, no structure, mist over the top of it.
    # The canopy is the furthest thing in the game and it is painted *pale*:
    # a forest seen from this high through this much air is a grey-green, and
    # painting it the dark green it "is" would put the highest-contrast edge on
    # the screen directly behind the play field.
    far = Plane("metal", (4.2, 5.8), windows={"foliage": (3.2, 4.2)})
    rnd = random.Random(5040)
    ridge(far, 186, 0.40, 5060, amp=7, step=21, thickness=54, ramp="foliage",
          crest=0.18, fade=0.34, rough=0.05)
    canopy(far, 214, 0.30, 5061, count=11, rx=(20, 38), ry=(8, 14), spread=8,
           ramp="foliage")
    for i in range(8):
        cloud(far, rnd.randrange(400), rnd.randrange(116, 178),
              rnd.randrange(30, 62), rnd.randrange(9, 17), 0.5, 5050 + i)
    mist(far, 170, 30, 0.5)

    # Near: one big limb across the top with its leaves, which is what tells you
    # you are up a tree rather than in one.
    near = Plane("foliage", (0.2, 2.6))
    rnd = random.Random(5070)
    for y in range(0, 30):                       # the limb itself
        for x in range(400):
            t = (y - (3 + int(7 * math.sin(x / 61.0)))) / 17.0
            if 0.0 <= t <= 1.0:
                near.set(x, y, 0.46 + (0.30 if t < 0.3 else
                                       (-0.24 if t > 0.78 else 0.0)), "wood")
    canopy(near, 26, 0.58, 5080, count=12, rx=(12, 22), ry=(7, 12), spread=7)
    # Four short vines, not the jungle's nine. SKY BRANCH has climbable vine
    # tiles in it, and a backdrop full of dangling green strings is exactly the
    # kind of pretty that makes a player try to climb the wallpaper.
    for i in range(4):
        hang(near, rnd.randrange(400), 24, rnd.randrange(26, 74), 0.30,
             5090 + i)
    trunk(near, 20, 0, 240, 17, 0.44, ramp="wood")   # one edge post only
    return {"sky": sky, "far": far, "near": near}


WORLDS = {"jungle": _jungle, "sky": _sky}


def build_backdrops():
    """Three parallax planes per world, each exactly one screen (400x240).

    One screen wide is what makes them tile seamlessly as the camera flips, and
    one screen tall is what keeps them screen-locked vertically: a two-screen
    level draws the same backdrop on both rows, so there is no seam to find at
    the join. `src/world/parallax_bg.gd` relies on both.

    Only `jungle` and `sky` are built. ROOT HOLLOW and THE WATERWAY author a
    solid `bg_rock` wall behind every tile of every screen, so nothing of the
    parallax is visible in either of them — measured, 0% of both levels. Their
    depth comes from ambient tint and light pools instead, which is what
    data/ambience.json is for.
    """
    for world, make in sorted(WORLDS.items()):
        planes = make()
        for name in ("sky", "far", "near"):
            p = planes[name]
            p.render().save(os.path.join(SPRITES, "bg_%s_%s.png" % (world, name)))
        print("bg_%s_{sky,far,near}.png  contrast budget %.1f/%.1f/%.1f steps"
              % (world, planes["sky"].contrast(), planes["far"].contrast(),
                 planes["near"].contrast()))
    # The phase 1 strips are gone; nothing may keep loading them.
    for stale in ("bg_far.png", "bg_near.png"):
        for suffix in ("", ".import"):
            path = os.path.join(SPRITES, stale + suffix)
            if os.path.exists(path):
                os.remove(path)


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


