#!/usr/bin/env python3
"""The palette and shading engine — phase 1 of docs/art-direction.md.

The diagnosis behind this file: the old art had 18 flat colours and at most 4
shades of any hue. With two or three shades you can *fill* a region; you cannot
*model* a surface. Apogee's VGA games ran 6-10 shades of every material, which
is why their tiles read as rock and ours read as wallpaper.

So everything below is built out of **material ramps**: twelve materials, seven
steps each, dark to light. Nothing in `tools/art/` may invent a colour — it
picks a ramp and a level, and `dither()` resolves that to a pixel. Fractional
levels are resolved with a 4x4 Bayer matrix, which is how VGA artists faked the
shades a 256-colour palette still did not have.

The legacy ASCII grids are still authored with one character per colour; `PAL`
is now *derived* from the ramps via `CHARS`, so even art that has not been
re-lit shares the same vocabulary.
"""
import math
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TILES = os.path.join(ROOT, "assets", "tiles")
SPRITES = os.path.join(ROOT, "assets", "sprites")
FONTS = os.path.join(ROOT, "assets", "fonts")
for d in (TILES, SPRITES, FONTS):
    os.makedirs(d, exist_ok=True)

# ---------------------------------------------------------------- ramps
# Dark -> light, seven steps. Ordered by luminance so `dither()` between any two
# adjacent steps is a smooth transition rather than a hue jump.
RAMPS = {
    # earth and rock
    "dirt":    [(0x27, 0x17, 0x0e), (0x3a, 0x23, 0x14), (0x52, 0x33, 0x1d),
                (0x6b, 0x43, 0x26), (0x87, 0x58, 0x33), (0xa6, 0x72, 0x45),
                (0xc2, 0x8f, 0x5d)],
    "stone":   [(0x1b, 0x1c, 0x24), (0x2b, 0x2d, 0x38), (0x40, 0x43, 0x50),
                (0x58, 0x5c, 0x69), (0x73, 0x77, 0x83), (0x94, 0x98, 0xa2),
                (0xb8, 0xbc, 0xc4)],
    "wood":    [(0x2a, 0x18, 0x0d), (0x40, 0x26, 0x14), (0x5c, 0x38, 0x1e),
                (0x7a, 0x4c, 0x29), (0x99, 0x64, 0x38), (0xb8, 0x81, 0x4f),
                (0xd4, 0xa1, 0x6e)],
    # growing things: `grass` is the lit, saturated green, `foliage` the deep
    # shade green that backgrounds and canopies are built from
    "grass":   [(0x0a, 0x22, 0x11), (0x11, 0x35, 0x1c), (0x1a, 0x50, 0x29),
                (0x2a, 0x7a, 0x3f), (0x3c, 0x9c, 0x4b), (0x58, 0xc1, 0x5a),
                (0x8a, 0xde, 0x7c)],
    "foliage": [(0x06, 0x16, 0x11), (0x0b, 0x22, 0x19), (0x0f, 0x33, 0x24),
                (0x14, 0x47, 0x2e), (0x1d, 0x5c, 0x3b), (0x28, 0x74, 0x4a),
                (0x39, 0x8d, 0x5c)],
    # Kaya
    "cloth":   [(0x0d, 0x2a, 0x18), (0x15, 0x3f, 0x24), (0x1f, 0x5c, 0x31),
                (0x2d, 0x7a, 0x42), (0x42, 0x9b, 0x55), (0x62, 0xbc, 0x6e),
                (0x8c, 0xd8, 0x92)],
    "skin":    [(0x5c, 0x32, 0x22), (0x84, 0x4c, 0x33), (0xad, 0x6c, 0x4a),
                (0xd0, 0x91, 0x66), (0xe8, 0xb4, 0x8a), (0xf6, 0xd0, 0xad),
                (0xff, 0xe6, 0xcd)],
    # water runs abyss -> navy -> blue -> cyan
    "water":   [(0x0e, 0x11, 0x1e), (0x1a, 0x1c, 0x2c), (0x22, 0x29, 0x42),
                (0x2b, 0x35, 0x56), (0x36, 0x52, 0x7d), (0x3b, 0x6e, 0xa5),
                (0x41, 0xa6, 0xb5)],
    # steel through to the off-white used for eyes, teeth and type
    "metal":   [(0x17, 0x18, 0x1e), (0x2b, 0x2d, 0x35), (0x49, 0x4a, 0x53),
                (0x6a, 0x6a, 0x72), (0x8e, 0x8c, 0x90), (0xb8, 0xb0, 0xa8),
                (0xf2, 0xef, 0xe6)],
    "gold":    [(0x2e, 0x1c, 0x0c), (0x4e, 0x2e, 0x11), (0x7a, 0x47, 0x18),
                (0xa8, 0x64, 0x22), (0xe0, 0x8c, 0x3a), (0xf2, 0xd5, 0x65),
                (0xfd, 0xf1, 0xb4)],
    "ember":   [(0x27, 0x08, 0x0c), (0x48, 0x10, 0x13), (0x74, 0x1d, 0x1c),
                (0xa0, 0x33, 0x28), (0xc0, 0x4a, 0x3a), (0xe4, 0x7a, 0x3c),
                (0xff, 0xc2, 0x62)],
    "purple":  [(0x21, 0x12, 0x2c), (0x33, 0x1c, 0x44), (0x4a, 0x2a, 0x5e),
                (0x63, 0x3c, 0x78), (0x7f, 0x53, 0x92), (0x9d, 0x70, 0xac),
                (0xbd, 0x93, 0xc6)],
}
STEPS = 7
INK = (0x0d, 0x0b, 0x0f)        # the one colour outside the ramps: outlines

# Light comes from the upper left, everywhere, always. Tiles, sprites and props
# all bevel the same way, which is most of what makes a set look authored.
LIGHT = (-1, -1)

# 4x4 Bayer matrix: dithering between two ramp steps is how VGA art faked the
# shades a 256-colour palette still did not have.
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]

# ---------------------------------------------------------------- char map
# The legacy ASCII grids address colours by character. Every one of them is now
# a (ramp, step) pair, so nothing in the project can reach a colour that is not
# on a ramp. Steps were chosen to sit near the old flat colours, so art that has
# not been re-lit still looks like itself — only in the shared vocabulary.
CHARS = {
    '.': None,                  # transparent
    'k': "ink",                 # near-black outline
    'd': ("water", 1),          # dark blue-grey
    'n': ("water", 3),          # navy
    'b': ("water", 5),          # blue
    'c': ("water", 6),          # cyan
    'g': ("foliage", 3),        # dark green
    'G': ("grass", 3),          # green
    'l': ("grass", 5),          # light green
    'y': ("gold", 5),           # yellow
    'o': ("gold", 4),           # orange
    'r': ("ember", 4),          # red
    'm': ("dirt", 3),           # brown
    'M': ("dirt", 5),           # light brown
    'a': ("metal", 3),          # grey
    'A': ("metal", 5),          # light grey
    'w': ("metal", 6),          # off-white
    's': ("skin", 4),           # skin
    'p': ("purple", 4),         # purple
}


def step(ramp, i):
    """Ramp step `i`, clamped. `i` is rounded, so callers can pass floats."""
    r = RAMPS[ramp]
    return r[max(0, min(len(r) - 1, int(round(i))))]


def dither(ramp, x, y, level):
    """Resolve a fractional ramp level at (x, y) with the Bayer matrix.

    Levels between two steps come out as an ordered mix of the two, which is
    what lets a seven-step ramp render a smooth-looking gradient."""
    lo = math.floor(level)
    frac = level - lo
    on = (BAYER[y % 4][x % 4] + 0.5) / 16.0 < frac
    return step(ramp, lo + (1 if on else 0))


def bayer_on(x, y, frac):
    """True for the fraction of pixels the Bayer matrix turns on at (x, y).

    `dither()` uses this to mix two steps of one ramp; backdrops use it directly
    to cross-fade between two *different* ramps, which is how the title sky gets
    from night blue to sunset orange without inventing a colour in between.
    """
    return (BAYER[y % 4][x % 4] + 0.5) / 16.0 < frac


def _rgba(entry):
    if entry is None:
        return (0, 0, 0, 0)
    if entry == "ink":
        return INK + (255,)
    return step(entry[0], entry[1]) + (255,)


PAL = {ch: _rgba(entry) for ch, entry in CHARS.items()}

#: Every colour this project is allowed to emit, as a flat list. Written out to
#: assets/palette.json so the test suite can assert nothing escaped the ramps.
ALL_COLOURS = [INK] + [c for name in sorted(RAMPS) for c in RAMPS[name]]


def put(img, x, y, ramp, level, alpha=255):
    """Dithered pixel, bounds-checked. The workhorse of every generator here."""
    if 0 <= x < img.width and 0 <= y < img.height:
        img.putpixel((int(x), int(y)), dither(ramp, int(x), int(y), level) + (alpha,))


def put_ink(img, x, y):
    if 0 <= x < img.width and 0 <= y < img.height:
        img.putpixel((int(x), int(y)), INK + (255,))


def grid(rows):
    """ASCII rows -> list of (x, y, rgba)."""
    out = []
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            col = PAL[ch]
            if col[3]:
                out.append((x, y, col))
    return out


def blit(img, ox, oy, pixels):
    for x, y, col in pixels:
        img.putpixel((ox + x, oy + y), col)


def image(rows):
    """ASCII rows -> a flat RGBA image (no relighting)."""
    h, w = len(rows), len(rows[0])
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    blit(img, 0, 0, grid(rows))
    return img


def sheet(name, cells, cw, ch, cols=None, folder=SPRITES):
    """cells: ASCII-row-lists or PIL images. Packs them left to right."""
    cols = cols or len(cells)
    rows = (len(cells) + cols - 1) // cols
    img = Image.new("RGBA", (cw * cols, ch * rows), (0, 0, 0, 0))
    for i, cell in enumerate(cells):
        ox, oy = (i % cols) * cw, (i // cols) * ch
        if isinstance(cell, Image.Image):
            img.alpha_composite(cell, (ox, oy))
        else:
            blit(img, ox, oy, grid(cell))
    img.save(os.path.join(folder, name + ".png"))
    return img


# ---------------------------------------------------------------- structure
# The prototype's second finding, and the one that matters most for tiles:
# shading a flat fill makes it *softer*, not better. Apogee tiles contain
# discrete things — pebbles, mortar courses, planks, nails — each with its own
# highlight and shadow. Structure first, then shading. These are the things.
def blob(img, ramp, cx, cy, rx, ry, base, light=LIGHT, lit=1.4, dark=1.3):
    """A rounded lump with a lit face and a shadowed one."""
    for y in range(int(cy - ry - 1), int(cy + ry + 2)):
        for x in range(int(cx - rx - 1), int(cx + rx + 2)):
            if not (0 <= x < img.width and 0 <= y < img.height):
                continue
            nx, ny = (x - cx) / rx, (y - cy) / ry
            d = nx * nx + ny * ny
            if d > 1.0:
                continue
            lvl = base + (1.0 - d) * 1.2
            facing = nx * light[0] + ny * light[1]
            if facing > 0.25:
                lvl += lit
            elif facing < -0.3:
                lvl -= dark
            put(img, x, y, ramp, lvl)


def crack(img, ramp, x0, y0, length, base, rnd, drift=(0, 1, 1)):
    """A dark fissure with a lit lip along its lower edge."""
    x, y = x0, y0
    for _ in range(length):
        put(img, x, y, ramp, base - 1.8)
        put(img, x, y + 1, ramp, base + 0.8)
        x += rnd.choice(drift)
        y += rnd.choice([-1, 0, 1])


def speckle(img, ramp, rnd, count, base, spread=(-0.9, 0.9), box=None):
    """Loose grain: the cheap way to stop a fill reading as a flat rectangle."""
    x0, y0, x1, y1 = box or (0, 0, img.width, img.height)
    for _ in range(count):
        x, y = rnd.randrange(x0, x1), rnd.randrange(y0, y1)
        put(img, x, y, ramp, base + rnd.uniform(*spread))


# ---------------------------------------------------------------- relighting
def auto_shade(rows, mapping, light=LIGHT, depth=3, rate=0.7,
               lit=1.1, dark=0.95, outline='k'):
    """Re-light flat ASCII art from a light direction.

    Two different notions of "inside" are at work here, and keeping them apart
    is what stops the result blowing out:

    * **Volume** is measured against the whole silhouette, ink outline included
      — the outline is part of the body, not background, so a limb three pixels
      wide is thin rather than all-edge.
    * **Facing** is measured against the material only, so where one form meets
      another across an outline (head against shoulder, arm against tunic) the
      upper-left side still catches the light and the lower-right still falls
      into occlusion. That internal relief is most of what reads as volume.

    `depth` caps how far in the body keeps brightening — 3 for organic shapes
    that should read as round, 1 for architecture that should read as a flat
    face with a rim light rather than as a pillow.
    """
    h, w = len(rows), len(rows[0])
    mat = [[rows[y][x] in mapping for x in range(w)] for y in range(h)]
    body = [[mat[y][x] or rows[y][x] == outline for x in range(w)]
            for y in range(h)]

    def in_body(x, y):
        return 0 <= x < w and 0 <= y < h and body[y][x]

    def in_mat(x, y):
        return 0 <= x < w and 0 <= y < h and mat[y][x]

    dist = [[0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            if not body[y][x]:
                continue
            d = 0
            while d < depth + 1:
                d += 1
                ring = [(x + dx, y + dy) for dx in range(-d, d + 1) for dy in (-d, d)]
                ring += [(x + dx, y + dy) for dy in range(-d + 1, d) for dx in (-d, d)]
                if any(not in_body(px, py) for px, py in ring):
                    break
            dist[y][x] = d

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for y in range(h):
        for x in range(w):
            ch = rows[y][x]
            if not mat[y][x]:
                if ch == outline:
                    img.putpixel((x, y), INK + (255,))
                continue
            ramp, base = mapping[ch]
            lvl = base + (min(dist[y][x], depth) - 1) * rate
            if not in_mat(x + light[0], y + light[1]):
                lvl += lit
            if not in_mat(x - light[0], y - light[1]):
                lvl -= dark
            put(img, x, y, ramp, lvl)
    return img


def write_manifest():
    """Emit the generated palette so tests (and later phases) can check that no
    asset contains a colour the ramps did not produce."""
    import json
    out = {
        "_comment": "Generated by tools/art/palette.py. Do not edit.",
        "light": list(LIGHT),
        "ink": list(INK),
        "ramps": {name: [list(c) for c in RAMPS[name]] for name in sorted(RAMPS)},
        "chars": {ch: ("ink" if e == "ink" else (list(e) if e else None))
                  for ch, e in sorted(CHARS.items())},
    }
    path = os.path.join(ROOT, "assets", "palette.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
        f.write("\n")
    print("palette.json  %d ramps x %d steps = %d colours"
          % (len(RAMPS), STEPS, len(ALL_COLOURS)))
