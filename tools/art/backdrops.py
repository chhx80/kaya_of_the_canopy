"""Backdrops and UI art: bitmap font, title logo, title background, the
layered parallax planes, the lighting textures, the app icon and the store
icon set."""
import math
import os
import random

from PIL import Image

from .palette import (ART_SCALE, BAYER, FONTS, HD_NATIVE, INK, PAL, RAMPS, ROOT,
                      SPRITES, blit, grid, step)
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

# ---------------------------------------------------------------- HD dither
# docs/plan-hd.md step 2: everything from here down is drawn natively at
# ART_SCALE texels per world unit. Coordinates stay in WORLD units throughout
# (a plane is still 448 wide, a ridge still sits at y 190); only the raster
# underneath is finer, so a shape's edge, a leaf's midrib or a mortar line is
# drawn a texel at a time instead of a world pixel at a time.
#
# The dither is the part that cannot simply be scaled. A 4x4 Bayer laid over
# 2x2 texel blocks is the old screen-door at twice the size; laid over texels
# it is a fine grey hatch that reads as noise next to the whole-step HD tiles
# (the look sample's finding, tools/art/kaya40.py `shade_hd`). So:
#
#   * The matrix is 8x8, built so its even/even sublattice IS the old 4x4
#     Bayer. `palette.open_1x()` decimates a native sheet by taking exactly that
#     texel of every 2x2 block, so the tools that judge a backdrop at one pixel
#     per world unit (gen_art.py --readability, tests/test_art_depth.gd) see the
#     same dither phase they always did, not a biased sample of a new one.
#   * Fills are squeezed toward whole steps. Only the middle `SEAM` of each
#     step-to-step interval is dithered; the rest renders as clean flat steps.
#     A gradient becomes broad clean bands joined by a narrow dithered seam --
#     the banded VGA sky, drawn at a resolution where the seam is fine enough
#     to read as a soft edge rather than as a pattern.
K = ART_SCALE
SEAM = 0.4
#: Where a sky crosses from one ramp to another the two colours are far apart,
#: and a wide seam between them is a checkerboard band: keep it thin.
RAMP_SEAM = 0.2
_D2 = ((0, 2), (3, 1))
BAYER8 = [[4 * BAYER[y // 2][x // 2] + _D2[y % 2][x % 2] for x in range(8)]
          for y in range(8)]


def hd_on(tx, ty, frac, seam=SEAM):
    """True for the texels the squeezed 8x8 Bayer turns on at `frac`.
    `seam=1.0` is an ordinary ordered dither (used for coverage, not value)."""
    f = (frac - 0.5) / seam + 0.5
    return (BAYER8[ty & 7][tx & 7] + 0.5) / 64.0 < f


def hd_colour(ramp, tx, ty, level, seam=SEAM):
    """A fractional ramp level at texel (tx, ty): whole steps, seams dithered."""
    lo = math.floor(level)
    return step(ramp, lo + (1 if hd_on(tx, ty, level - lo, seam) else 0))


def _render_rows(w, h, colour_at):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    img.putdata([colour_at(x, y) for y in range(h) for x in range(w)])
    return img


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
    """Title logo: the 8x8 font's KAYA blown up 5x, as before, but drawn at
    2x. The stair-stepped diagonals of the K, the A and the Y are bridged into
    continuous slanted strokes (a font pixel touching another only at a corner
    was two squares at 1x; at 2x it can be one stroke), the outer corners are
    rounded off by a texel, and the face is a bevelled slab: the gold ramp
    poured down it in clean steps as before, a sunlit texel along every top and
    left edge, a bronze one along every bottom and right edge, and a glint on
    each letter's top-left corner. Ink ring and green drop shadow keep their
    old weight (one world unit, two world units)."""
    text = "KAYA"
    scale = 5
    off = 2                      # shadow offset, world units
    w = len(text) * 8 * scale
    h = 8 * scale
    W, H = (w + off + 4) * K, (h + off + 4) * K
    S = scale * K                # texels per font pixel
    inside = [[False] * W for _ in range(H)]
    for i, ch in enumerate(text):
        g = GLYPHS.get(ch, [])

        def on(gx, gy):
            return 0 <= gy < len(g) and 0 <= gx < len(g[gy]) and g[gy][gx] == '#'
        ox, oy = (2 + i * 8 * scale) * K, 2 * K
        for gy in range(len(g)):
            for gx in range(len(g[gy])):
                if not on(gx, gy):
                    continue
                for ty in range(S):
                    for tx in range(S):
                        inside[oy + gy * S + ty][ox + gx * S + tx] = True
                for sx in (1, -1):        # a corner-only neighbour: bridge it
                    if on(gx + sx, gy + 1) and not on(gx + sx, gy) and not on(gx, gy + 1):
                        ax, ay = ox + (gx + 0.5) * S, oy + (gy + 0.5) * S
                        bx, by = ax + sx * S, ay + S
                        for ty in range(int(ay), int(by)):
                            for tx in range(int(min(ax, bx)), int(max(ax, bx))):
                                px_, py_ = tx + 0.5, ty + 0.5
                                d = abs((bx - ax) * (ay - py_) - (ax - px_) * (by - ay)) / (S * 2 ** 0.5)
                                if d <= S * 0.5:
                                    inside[ty][tx] = True

    def at(m, x, y):
        return 0 <= x < W and 0 <= y < H and m[y][x]

    # round the outer corners of the slab by one texel: a texel with two
    # orthogonal empty neighbours that are also empty diagonally goes
    body = [row[:] for row in inside]
    for y in range(H):
        for x in range(W):
            if not inside[y][x]:
                continue
            for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                if not at(inside, x + dx, y) and not at(inside, x, y + dy) \
                        and not at(inside, x + dx, y + dy):
                    body[y][x] = False

    def dist(m, x, y, dx, dy, cap):
        n = 0
        while n < cap and at(m, x + dx * (n + 1), y + dy * (n + 1)):
            n += 1
        return n

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = img.load()
    shade = step("foliage", 1) + (255,)
    # 1) the drop shadow, 2) an ink ring one world unit thick
    for y in range(H):
        for x in range(W):
            if at(body, x - off * K, y - off * K):
                px[x, y] = shade
    ring = 1 * K
    for y in range(H):
        for x in range(W):
            if body[y][x]:
                continue
            for dy in range(-ring, ring + 1):
                for dx in range(-ring, ring + 1):
                    if abs(dx) + abs(dy) <= ring + 1 and at(body, x + dx, y + dy):
                        px[x, y] = INK + (255,)
                        break
                else:
                    continue
                break
    # 3) the face
    for y in range(H):
        for x in range(W):
            if not body[y][x]:
                continue
            yy = y - 2 * K
            up = dist(body, x, y, 0, -1, 2)
            lf = dist(body, x, y, -1, 0, 2)
            dn = dist(body, x, y, 0, 1, 2)
            rt = dist(body, x, y, 1, 0, 2)
            # bright at the top of the glyph, falling to a deep bronze at the foot
            lvl = 6.3 - (yy / float(h * K)) * 3.1
            if up < 1 or lf < 1:
                lvl = min(6.0, lvl + 1.0)               # the sunlit arris
            elif dn < 1 or rt < 1:
                lvl -= 1.3                              # the bronze one
            elif dn < 2 or rt < 2:
                lvl -= 0.5
            px[x, y] = hd_colour("gold", x, y, lvl) + (255,)
    # 4) a catch-light on the top-left corner of every letter
    for i, ch in enumerate(text):
        col = GLYPHS[ch][0].index('#')
        cx, cy = (2 + (i * 8 + col) * scale) * K + 3, 2 * K + 3
        for d in range(-3, 4):
            for (sx, sy) in ((cx + d, cy), (cx, cy + d)):
                if at(body, sx, sy) and abs(d) < 3:
                    px[sx, sy] = step("gold", 6) + (255,)
    img.save(os.path.join(SPRITES, "logo.png"))
    print("logo.png")


# ---------------------------------------------------------------- backdrops
def canopy_layer(p, base_y, v, seed, amp=14, step_=9, rim=0.0, ramp=None):
    """Rounded treeline silhouette across the full width of a plane, in world
    units. At 2x the lumps get a serrated top -- leaf tips standing out of the
    edge -- a lit rim on their upper-left, and a shaded crease where one lump
    tucks under the next, which is all a crown is at sunset."""
    rnd = random.Random(seed)
    tops = []
    x = 0
    while x < p.w:
        r = rnd.randint(step_ - 2, step_ + 4)
        cy = base_y + rnd.randint(-amp, amp // 2)
        tops.append((x, cy, r))
        x += rnd.randint(step_ - 3, step_ + 3)
    for px in p.span(0, p.w):
        cxp = px + p.c
        top, own = p.h, None
        for (cx, cy, r) in tops:
            dx = cxp - cx
            if abs(dx) <= r:
                yy = cy - (r * r - dx * dx) ** 0.5
                if yy < top:
                    top, own = yy, (cx, cy, r, dx)
        if own is None:
            continue
        cx, cy, r, dx = own
        # leaf tips: a sawtooth riding the dome, period 3 world units
        top -= 1.2 * abs(((cxp * 0.67 + seed) % 2.0) - 1.0)
        for py in p.span(max(0.0, top), p.h):
            d = py - top
            s = 0.0
            if d < 1.0 and dx < r * 0.35:
                s = rim
            elif d < 4.0 and dx > r * 0.55:
                s = -rim                       # the crease under the next lump
            p.set(px, py, v + s, ramp)


def build_title_bg():
    """Dusk over the canopy, drawn at 2x on a Plane so it shares the backdrops'
    dither. The composition is the old one, element for element: the DUSK sky,
    the low sun, fifty stars, three canopy bands and sixteen vines; only the sun
    has moved, from (300, 150) to (158, 150), to sit between Kaya and the menu
    (src/ui/menus/title_screen.gd). What 2x adds: a sun with a lit rim and two
    cloud streaks across its foot, stars of three magnitudes with the brightest
    twinkling, leaf tips and a sunlit rim along each canopy, and vines with
    paired leaves."""
    W, H = 400, 240
    full = (0.0, 6.0)               # value v maps straight onto step 6 * v
    p = Plane("water", full, opaque=True, w=W, h=H,
              windows={r: full for r in RAMPS})
    for y in p.span(0, H):
        t = min(1.0, (y + p.c) / (H * 0.88))
        pos = t * (len(DUSK) - 1)
        lo = int(pos)
        ty = int(y * K)
        for tx in range(p.tw):
            i = lo + (1 if hd_on(tx, ty, pos - lo) else 0)
            r, s = DUSK[min(i, len(DUSK) - 1)]
            p.val[ty][tx] = s / 6.0
            p.mat[ty][tx] = r
    cx, cy, r = 158, 150, 34                     # low sun, between Kaya and the menu
    for y in p.span(cy - r, cy + r + 1):
        for x in p.span(cx - r, cx + r + 1):
            d = math.hypot(x + p.c - cx, y + p.c - cy)
            if d > r:
                continue
            lvl = 6.0 if d < r - 4 else 5.0
            if r - 0.6 < d:
                lvl = 5.0                        # the rim, one texel
            elif r - 5.0 < d < r - 4.0 and (x + p.c - cx) + (y + p.c - cy) < 0:
                lvl = 6.0                        # lit inner edge, upper left
            p.set(x, y, lvl / 6.0, "gold")
    for (sy, th, a, b) in ((cy - 3, 1.0, -0.2, 1.0), (cy + 6, 1.5, -1.0, 0.45)):
        for y in p.span(sy, sy + th):                     # cloud streaks over its foot
            half = (r * r - (y + p.c - cy) ** 2) ** 0.5 - 3.0
            for x in p.span(cx + a * half, cx + b * half):
                p.set(x, y, 4.0 / 6.0 if y < sy + 0.5 else 3.0 / 6.0, "purple")
    rnd = random.Random(9)
    for i in range(50):
        x, y = rnd.randrange(W), rnd.randrange(60)
        mag = i % 7
        if mag == 0:                             # the bright ones twinkle
            for (dx, dy) in ((0, 0), (0.5, 0), (0, 0.5), (0.5, 0.5)):
                p.set(x + dx, y + dy, 1.0, "metal")
            for (dx, dy) in ((-0.5, 0), (1, 0), (0, -0.5), (0, 1)):
                p.set(x + dx, y + dy, 5.0 / 6.0, "metal")
        elif mag < 4:
            p.set(x, y, 1.0, "metal")
        else:
            p.set(x + 0.5, y + 0.5, 4.0 / 6.0, "metal")
    canopy_layer(p, 176, 4.0 / 6.0, 101, amp=12, step_=11, rim=1.0 / 6.0, ramp="foliage")
    canopy_layer(p, 198, 2.0 / 6.0, 202, amp=14, step_=13, rim=1.0 / 6.0, ramp="foliage")
    canopy_layer(p, 222, 0.0, 303, amp=10, step_=15, rim=1.0 / 6.0, ramp="foliage")
    rnd = random.Random(77)
    for _ in range(16):                          # hanging vines
        x = rnd.randrange(W)
        ln = rnd.randrange(20, 90)
        for y in p.span(0, ln):
            xx = x + 2 * math.sin(y / 7.0)
            p.set(xx, y, 1.0 / 6.0, "foliage")
            p.set(xx + 0.5, y, 0.0, "foliage")
            if int(y * K) % (9 * K) == 0 and y > 0:      # a pair of leaves
                for side in (-1, 1):
                    for k in range(5):
                        lx = xx + 0.25 + side * (0.5 + k * 0.5)
                        ly = y - 0.5 + k * 0.4 - (0.4 if 1 <= k <= 2 else 0)
                        p.set(lx, ly, (4.0 if side < 0 else 2.0) / 6.0, "foliage")
                        if 1 <= k <= 3:
                            p.set(lx, ly + 0.5, 1.0 / 6.0, "foliage")
    p.render().save(os.path.join(SPRITES, "title_bg.png"))
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
#
# HD: the buffer is K texels per world unit. Brushes address it in world units
# (floats) and walk it with `span()`, which yields the world coordinate of
# every texel edge in a range; `c` is half a texel, for sampling at centres.
class Plane:
    """One depth plane of a backdrop: a value buffer plus its slice of a ramp."""

    def __init__(self, ramp, window, opaque=False, w=400, h=240, windows=None, k=K,
                 seam=SEAM, gain=None):
        self.ramp = ramp
        self.lo, self.hi = window
        # HD: how the window is spent. At 1x a value between two steps was a
        # Bayer mix, so a facet 0.3 of a step lighter still showed as a denser
        # dot. At 2x fills are whole steps (`seam`, see hd_on), and a detail
        # that is less than half a step from its ground would round away. A
        # `gain` above 1 stretches values about the window's centre so details
        # land on a step of their own, clamped to the steps the window already
        # touched -- the same colours the 1x dither used, so the plane's
        # luma span (its contrast budget, tests/test_art_depth.gd) cannot grow.
        # The default gain is 1 for an opaque plane (a sky is a gradient, and
        # stretching it changes the time of day) and otherwise grows as the
        # window narrows: 1.8 / contrast, between 1 and 1.5.
        self.seam = seam
        if gain is None:
            gain = 1.0 if opaque else max(1.0, min(1.5, 1.8 / max(0.1, window[1] - window[0])))
        self.gain = gain
        # Per-material exception to the plane's window. Haze acts on the light a
        # material reflects, and a forest canopy seen through the same air as a
        # cloud is nothing like as bright as the cloud: one window for both puts
        # a glaring green slab under the cloud sea. Sparingly — the plane's own
        # window is what holds the depth together.
        self.windows = windows or {}
        self.opaque = opaque
        self.w, self.h = w, h
        self.k = k
        self.c = 0.5 / k
        self.tw, self.th = w * k, h * k
        self.val = [[None] * self.tw for _ in range(self.th)]
        self.mat = [[None] * self.tw for _ in range(self.th)]   # per-texel ramp override

    def contrast(self):
        """The plane's contrast budget, in ramp steps."""
        return self.hi - self.lo

    def span(self, a, b):
        """World coordinates of the texel edges covering [a, b)."""
        k = self.k
        return [i / float(k) for i in range(int(math.floor(a * k)), int(math.ceil(b * k)))]

    def texel(self, x, y):
        return int(math.floor(x * self.k)) % self.tw, int(math.floor(y * self.k))

    def set(self, x, y, v, ramp=None):
        """Paint material value `v` on the texel at world (x, y). Wraps in x:
        every backdrop strip has to tile seamlessly as the camera scrolls."""
        tx, ty = self.texel(x, y)
        if 0 <= ty < self.th:
            self.val[ty][tx] = v
            self.mat[ty][tx] = ramp

    def get(self, x, y):
        tx, ty = self.texel(x, y)
        return self.val[ty][tx] if 0 <= ty < self.th else None

    def clear(self, x, y):
        tx, ty = self.texel(x, y)
        if 0 <= ty < self.th:
            self.val[ty][tx] = None

    def boost(self, x, y, dv, frac=1.0):
        """Lift what is already there. Light shafts and mist are done this way
        so they read as air over the art rather than as paint on it. At 1x
        `frac` was a Bayer coverage; at 2x the lift is applied as its mean and
        the render's banding draws it, so a shaft is a clean lighter band with
        a soft seam, not a screen-door."""
        tx, ty = self.texel(x, y)
        if not (0 <= ty < self.th) or self.val[ty][tx] is None:
            return
        self.val[ty][tx] = min(1.0, self.val[ty][tx] + dv * min(1.0, frac))

    def window_for(self, ramp):
        return self.windows.get(ramp, (self.lo, self.hi))

    def render(self):
        def at(tx, ty):
            v = self.val[ty][tx]
            if v is None:
                if not self.opaque:
                    return (0, 0, 0, 0)
                v = 0.0
            ramp = self.mat[ty][tx] or self.ramp
            lo, hi = self.window_for(ramp)
            level = lo + max(0.0, min(1.0, v)) * (hi - lo)
            if self.gain != 1.0:
                mid = (lo + hi) * 0.5
                level = max(math.floor(lo), min(math.ceil(hi),
                                                mid + (level - mid) * self.gain))
            return hd_colour(ramp, tx, ty, level, self.seam) + (255,)
        return _render_rows(self.tw, self.th, at)


# ---------------------------------------------------------------- brushes
def vband(p, y0, y1, v0, v1, ramp=None, curve=1.0):
    """Vertical gradient across the full width."""
    for y in p.span(max(0, y0), min(p.h, y1)):
        t = (y + p.c - y0) / float(max(1, y1 - y0))
        v = v0 + (v1 - v0) * (max(0.0, t) ** curve)
        ty = int(y * p.k)
        p.val[ty] = [v] * p.tw
        p.mat[ty] = [ramp] * p.tw


def ridge(p, base_y, v, seed, amp=14, step=11, thickness=None, ramp=None,
          crest=0.0, fade=0.0, rough=0.0):
    """A rolling silhouette — treeline, hill, cloud bank, cave roof.

    Wraps in x by construction, so the horizon does not jump at a screen flip.
    `crest` brightens the topmost two world units, which is what makes a
    distant ridge read as lit from above rather than as a cut-out, with the
    very top texel lifted again as a lip; `fade` darkens with depth into the
    band so it does not come out as a slab of one value, which is the single
    thing that most gives a silhouette away as generated."""
    rnd = random.Random(seed)
    lumps = []
    x = 0
    while x < p.w:
        r = rnd.randint(step - 2, step + 5)
        lumps.append((x, base_y + rnd.randint(-amp, amp // 2), r))
        x += rnd.randint(step - 3, step + 3)
    for px in p.span(0, p.w):
        top = float(p.h)
        for (cx, cy, r) in lumps:
            dx = (px + p.c - cx + p.w / 2.0) % p.w - p.w / 2.0
            if abs(dx) <= r:
                top = min(top, cy - (r * r - dx * dx) ** 0.5)
        if top >= p.h:
            continue
        end = p.h if thickness is None else min(p.h, max(0, top) + thickness)
        depth = max(1, end - max(0, top))
        for py in p.span(max(0, top), end):
            d = py - top
            vv = v + (crest if d < 2 else 0.0) - fade * (d / float(depth))
            if d < 0.5 and crest:
                vv += 0.06
            if rough:
                vv += rough * (rnd.random() - 0.5)
            p.set(px, py, vv, ramp)


def cloud(p, cx, cy, rx, ry, v, seed, ramp=None):
    """A cloud bank: stacked lumps, bright on top, shaded underneath, with a
    one-texel silver lip where a lump's top meets the sky."""
    rnd = random.Random(seed)
    for _ in range(9):
        ox = rnd.randint(-rx, rx)
        r = rnd.randint(max(4, ry // 2), max(6, ry))
        oy = rnd.randint(-ry // 3, ry // 3)
        for y in p.span(cy + oy - r, cy + oy + r + 1):
            for x in p.span(cx + ox - r, cx + ox + r + 1):
                dx = (x + p.c - cx - ox) / float(r)
                dy = (y + p.c - cy - oy) / float(r)
                d = dx * dx + dy * dy
                if d > 1.0:
                    continue
                s = 0.30 if dy < -0.35 else (-0.28 if dy > 0.3 else 0.05)
                if dy < -0.5 and d > (1.0 - 1.0 / (r * p.k)) ** 2:
                    s = 0.40
                p.set(x, y, v + s, ramp)


def shafts(p, count, seed, dv=0.26, slope=3, width=(10, 26), top=0, reach=1.0):
    """Slanted light coming down through the canopy or the water, applied with
    `boost` so it lifts whatever it crosses instead of painting a stripe over
    it. At 2x each shaft feathers in over its outer two world units and has a
    brighter core line, so it reads as a beam rather than a ruled band."""
    rnd = random.Random(seed)
    for _ in range(count):
        sx = rnd.randrange(p.w)
        wdt = rnd.randrange(*width)
        span = int(p.h * reach)
        for y in p.span(top, min(p.h, top + span)):
            fade = 1.0 - (y - top) / float(max(1, span))
            x0 = sx + y / float(slope)
            for x in p.span(x0, x0 + wdt):
                u = (x + p.c - x0) / float(wdt)
                edge = min(1.0, min(u, 1.0 - u) * wdt / 2.0)
                core = 1.25 if abs(u - 0.3) < 0.06 else 1.0
                p.boost(x, y, dv * fade * edge * core, 0.5 * fade + 0.2)


def mist(p, y0, thickness, amount, dv=0.22):
    """A horizontal haze band: the cheapest depth cue there is."""
    for y in p.span(y0, min(p.h, y0 + thickness)):
        fade = 1.0 - abs((y + p.c - y0) - thickness / 2.0) / (thickness / 2.0)
        for x in p.span(0, p.w):
            p.boost(x, y, dv * fade, amount * fade)


def grain(p, seed, count, dv=0.12):
    """Loose single-texel noise so a gradient does not read as a flat wash.
    Same density per world unit as at 1x, so K*K as many grains."""
    rnd = random.Random(seed)
    for _ in range(count * p.k * p.k):
        x, y = rnd.uniform(0, p.w), rnd.uniform(0, p.h)
        tx, ty = p.texel(x, y)
        if 0 <= ty < p.th and p.val[ty][tx] is not None:
            p.val[ty][tx] = min(1.0, p.val[ty][tx] + (dv if rnd.random() < 0.5 else -dv))


def horizon_haze(p, y0, y1, v0, v1, ramp=None, curve=1.0, bands=5):
    """Phase C, docs/plan-art-motion.md: "horizon gradient banding via dither
    on the far planes." A gradient like `vband`, except it steps through
    `bands` discrete levels rather than a continuous curve — the classic
    banded-sunset look, each band dithered into the next at its boundary. And
    unlike `vband` it only fills texels the plane has not already painted:
    called after a world's colonnade/ridge/comb is drawn, it shows up in the
    gaps between them as atmosphere, and never overwrites a silhouette."""
    for y in p.span(max(0, y0), min(p.h, y1)):
        t = (y + p.c - y0) / float(max(1, y1 - y0))
        step_t = round(t * bands) / float(bands)
        v = v0 + (v1 - v0) * (step_t ** curve)
        ty = int(y * p.k)
        row, mrow = p.val[ty], p.mat[ty]
        for tx in range(p.tw):
            if row[tx] is None:
                row[tx] = v
                mrow[tx] = ramp


def sky_path(p, path, curve=1.0):
    """Vertical gradient that walks a path *through* several ramps.

    Phase 1's finding, reused: a sky that has to cross hues bands if you dither
    straight between the ends, so the crossing is routed as a list of
    neighbouring (ramp, value) pairs close enough in luminance to mix."""
    for y in p.span(0, p.h):
        t = ((y + p.c) / float(p.h)) ** curve
        pos = t * (len(path) - 1)
        lo = int(pos)
        hi = min(lo + 1, len(path) - 1)
        ty = int(y * p.k)
        seam = SEAM if path[hi][0] == path[lo][0] else RAMP_SEAM
        for tx in range(p.tw):
            e = path[hi] if hd_on(tx, ty, pos - lo, seam) else path[lo]
            p.val[ty][tx] = e[1]
            p.mat[ty][tx] = e[0]


def spires(p, base_y, count, v, seed, ramp=None, height=(40, 130),
           width=(10, 34)):
    """Jagged volcanic-glass teeth. Lit on the upper-left face and falling away
    to the right, like every other solid in this game.

    At 2x a spire is cut glass rather than three flat strips: two more facet
    lines run up each face toward the tip, every facet takes its own value,
    the arris between the lit face and the next catches a one-texel line of
    light, and a conchoidal chip or two breaks the shadow face."""
    rnd = random.Random(seed)
    for i in range(count):
        cx = int(i * (p.w / float(count)) + rnd.randint(-14, 14))
        h = rnd.randint(*height)
        half = rnd.randint(*width) // 2
        lean = rnd.uniform(-0.18, 0.18)
        frnd = random.Random(seed * 131 + i)
        cuts = sorted((frnd.uniform(-0.15, 0.05), frnd.uniform(0.2, 0.45)))
        bend = frnd.uniform(-0.12, 0.12)
        chips = [(frnd.uniform(0.15, 0.7), frnd.uniform(0.5, 0.8)) for _ in range(2)]
        for y in p.span(max(0, base_y - h), min(p.h, base_y + 6)):
            t = (base_y - y) / float(h)
            if t < 0:
                continue
            wdt = half * (1.0 - t ** 0.8)
            sx = cx + lean * (base_y - y)
            for x in p.span(sx - wdt, sx + wdt + 1):
                u = (x + p.c - sx) / max(wdt, 0.8)
                if u > 1.0 + p.c / max(wdt, 0.8):
                    continue
                if u < -0.35:
                    s = 0.34
                elif u > 0.45:
                    s = -0.26
                else:
                    c0 = cuts[0] + bend * t
                    c1 = cuts[1] - bend * t
                    s = 0.16 if u < c0 else (0.0 if u < c1 else -0.12)
                du = 1.0 / (max(wdt, 0.8) * p.k)
                if abs(u + 0.35) < du:
                    s = 0.44                      # the lit arris
                elif abs(u - 0.45) < du:
                    s = -0.34                     # the shadow arris
                for (ct, cu) in chips:
                    if abs(t - ct) < 0.035 and abs(u - cu) < 0.14:
                        s = -0.36 if t < ct else -0.18
                p.set(x, y, v + s, ramp)


def glow(p, cx, cy, r, dv, seed, frac=0.9):
    """A pool of light in the backdrop. `boost`-based, so it lifts whatever is
    already painted rather than stamping a disc on it."""
    for y in p.span(cy - r, cy + r + 1):
        for x in p.span(cx - r, cx + r + 1):
            d = math.hypot(x + p.c - cx, y + p.c - cy) / float(r)
            if d > 1.0:
                continue
            k = (1.0 - d) ** 1.6
            p.boost(x, y, dv * k, min(1.0, frac * k + 0.08))


def build_backdrops():
    """The parallax planes of every world: tools/art/parallax_worlds.py paints
    them (Kaya Refit phase 3), sized by data/parallax.json, at K texels per
    world unit.

    The world names are an interface: data/ambience.json has to name the same
    string, or `Ambience.for_level()` resolves a level to a backdrop that has
    no art. tests/test_art_depth.gd checks exactly that, in both directions.
    """
    from . import parallax_worlds
    made = parallax_worlds.build(SPRITES)
    for world, planes in sorted(made.items()):
        print("bg_%s_{%s}.png  %s  contrast budget %s steps" % (
            world, ",".join(planes), " ".join("%dx%d" % (p.tw, p.th) for p in planes.values()),
            "/".join("%.1f" % planes[n].contrast() for n in ("sky", "far", "near"))))


# ---------------------------------------------------------------- light art
# The lighting decision (docs/art-direction.md, phase 3) came down on the side
# of additive light pools over Light2D. These are the two textures it needs.
def build_light_art():
    """A light pool and a screen vignette, both banded rather than smooth.

    A smooth 8-bit falloff over 16-colour-per-material pixel art looks like a
    modern glow filter dropped on a DOS game. VGA artists had the same problem
    and solved it the same way as everything else: quantise the falloff into a
    few bands and dither the boundaries. At 2x there are twice the bands, half
    as tall each, and the seams are dithered on the texel grid, so a pool's
    edge is a soft step rather than a doubled checkerboard."""
    S = 96 * K
    r = S / 2.0
    pool = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    bands = 12
    for y in range(S):
        for x in range(S):
            d = math.hypot(x - r + 0.5, y - r + 0.5) / r
            if d >= 1.0:
                continue
            f = (1.0 - d) ** 1.7               # falloff
            lvl = f * bands
            band = int(lvl) + (1 if hd_on(x, y, lvl - int(lvl)) else 0)
            if band <= 0:
                continue
            a = int(255 * min(1.0, band / float(bands)) * 0.72)
            pool.putpixel((x, y), step("metal", 6) + (a,))
    pool.save(os.path.join(SPRITES, "light_pool.png"))

    W, H = 400 * K, 240 * K
    vbands = 10

    def vig_at(x, y):
        nx = (x + 0.5 - W / 2.0) / (W / 2.0)
        ny = (y + 0.5 - H / 2.0) / (H / 2.0)
        d = max(0.0, math.hypot(nx * 0.92, ny) - 0.42) / 0.72
        lvl = min(1.0, d) ** 1.6 * vbands
        band = int(lvl) + (1 if hd_on(x, y, lvl - int(lvl)) else 0)
        if band <= 0:
            return (0, 0, 0, 0)
        return INK + (int(255 * min(1.0, band / float(vbands))),)
    _render_rows(W, H, vig_at).save(os.path.join(SPRITES, "vignette.png"))
    print("light_pool.png vignette.png")



def build_store_icons():
    """The boot splash. (The icons at every store size are build_icon()'s,
    tools/art/app_icon.py.)"""
    # Boot splash: the logo centred on the palette background.
    logo = Image.open(os.path.join(SPRITES, "logo.png")).convert("RGBA")
    sp = Image.new("RGBA", (640, 384), INK + (255,))
    # The splash shows the logo at twice its world size: the native 2x logo is
    # already that, texel for texel (docs/plan-hd.md).
    big = logo if "logo" in HD_NATIVE else logo.resize((logo.width * 2, logo.height * 2),
                                                       Image.NEAREST)
    sp.alpha_composite(big, ((sp.width - big.width) // 2, (sp.height - big.height) // 2 - 20))
    sp.save(os.path.join(SPRITES, "splash.png"))
    print("store icons + splash")


def build_icon():
    """The app icon, at every size that ships: the owner's picture of Kaya on
    the title's sunset (tools/art/app_icon.py). Needs title_bg.png, so it runs
    after build_title_bg()."""
    from . import app_icon
    app_icon.write_all()
