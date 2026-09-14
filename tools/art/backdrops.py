"""Backdrops and UI art: bitmap font, title logo, title background, the two
parallax strips, the app icon and the store icon set."""
import math
import os
import random

from PIL import Image

from .palette import (FONTS, INK, PAL, ROOT, SPRITES, bayer_on, blit, grid,
                      step)
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


def build_parallax():
    """Two scrolling backdrop strips (400x240 = exactly one screen each).

    Both tile seamlessly left/right; vertically they are screen-locked so a tall
    level shows the same depth on every screen instead of a seam. The far layer
    carries a full-height forest so no part of the screen is a flat fill.

    Everything here sits at the dark end of `foliage` and `water`. That is the
    atmospheric-perspective trick: depth is a *ramp position*, not a separate
    set of colours, so the far layer cannot compete with the tiles in front of
    it. Phase 3 replaces these silhouettes with real layered art; phase 1 just
    gets them onto the ramps.
    """
    W, H = 400, 240

    def band(img, x, y, ramp, lvl):
        lo = int(lvl)
        img.putpixel((x, y), step(ramp, lo + (1 if bayer_on(x, y, lvl - lo) else 0))
                     + (255,))

    # ---------------- far: hazy deep forest, full height
    far = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for y in range(H):
        t = y / H
        lvl = 1.4 - (t ** 0.7) * 0.9                  # haze thinning with depth
        for x in range(W):
            band(far, x, y, "foliage", lvl)
    rnd = random.Random(88)
    # distant trunks, thin and low-contrast, spread over the whole height
    for _ in range(26):
        x = rnd.randrange(W)
        w = rnd.randrange(2, 5)
        top = rnd.randrange(0, 70)
        lvl = rnd.choice([0.9, 1.2, 0.5])
        for yy in range(top, H):
            for k in range(w):
                band(far, (x + k) % W, yy, "foliage", lvl)
    # canopy line high up, so it frames rather than fills
    canopy_layer_band(far, 34, 26, step("foliage", 0) + (255,), 501, amp=14, step_=15)
    # horizontal mist bands break up the middle
    for bandy, amount in ((96, 0.55), (150, 0.40), (198, 0.30)):
        for y in range(bandy, bandy + 14):
            fade = 1.0 - abs((y - bandy) - 7) / 7.0
            for x in range(W):
                if bayer_on(x, y, amount * fade):
                    band(far, x, y, "foliage", 2.0)
    # light shafts slanting down
    for _ in range(6):
        sx = rnd.randrange(W)
        wdt = rnd.randrange(12, 30)
        for y in range(H):
            fade = 1.0 - y / float(H)
            for x in range(sx + y // 3, sx + y // 3 + wdt):
                if bayer_on(x % W, y, 0.34 * fade):
                    band(far, x % W, y, "foliage", 2.4)
    far.save(os.path.join(SPRITES, "bg_far.png"))

    # ---------------- near: chunky readable trunks with leaf clusters
    near = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rnd = random.Random(606)
    for _ in range(6):
        x = rnd.randrange(W)
        w = rnd.randrange(11, 19)
        for yy in range(0, H):
            for k in range(w):
                px = (x + k) % W
                if k in (0, w - 1):
                    lvl = 0.2
                elif k < 3:
                    lvl = 1.4                      # lit shoulder of the trunk
                elif k > w - 4:
                    lvl = 0.7
                else:
                    lvl = 1.0
                band(near, px, yy, "foliage", lvl)
        # leaf clusters branching off
        for _ in range(5):
            ly = rnd.randrange(20, H - 20)
            side = rnd.choice((-1, 1))
            span = rnd.randrange(10, 26)
            for i in range(span):
                px = (x + w // 2 + side * i) % W
                thick = max(1, 4 - i // 6)
                for dy in range(-thick, thick + 1):
                    yy = ly + dy + i // 5
                    if 0 <= yy < H:
                        band(near, px, yy, "foliage", 1.3 if dy < 0 else 0.8)
    canopy_layer_band(near, 0, 26, step("foliage", 0) + (255,), 707, amp=12, step_=11)
    near.save(os.path.join(SPRITES, "bg_near.png"))
    print("bg_far.png bg_near.png")


def canopy_layer_band(img, base_y, thickness, colour, seed, amp=14, step_=9):
    """Like canopy_layer but only paints a band of `thickness` px below the
    silhouette edge, so it frames the view instead of filling it."""
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
            dx = (px - cx + W // 2) % W - W // 2
            if abs(dx) <= r:
                top = min(top, cy - int((r * r - dx * dx) ** 0.5))
        if top >= H:
            continue
        for py in range(max(0, top), min(H, max(0, top) + thickness)):
            img.putpixel((px, py), colour)


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


