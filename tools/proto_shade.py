#!/usr/bin/env python3
"""Proof of concept for the art overhaul: ramp palette + directional shading.

SUPERSEDED. Phase 1 promoted this into `tools/art/palette.py`, which is what the
game is generated from now; see docs/art-direction.md. Kept as the record of the
experiment and of `docs/art-proto.png`. Note that its "current" row now reads the
*shipped* art, so the two rows no longer differ much — and that its `auto_shade`
is the original version, which treats the ink outline as background and blows out
thin limbs. The shipped one does not; see "Phase 1 as built".
"""
import math, os, random, sys
sys.path.insert(0, "tools")
from PIL import Image
from gen_art import grid, blit, PAL, K_IDLE, E_WALKER1

# ---------------------------------------------------------------- ramps
# Each material is a dark->light ramp. This is the whole point: 6 steps lets you
# model a surface; 2 steps only lets you fill it.
RAMPS = {
    "dirt":  [(0x27,0x17,0x0e),(0x3a,0x23,0x14),(0x52,0x33,0x1d),(0x6b,0x43,0x26),
              (0x87,0x58,0x33),(0xa6,0x72,0x45),(0xc2,0x8f,0x5d)],
    "grass": [(0x0a,0x22,0x11),(0x12,0x38,0x1d),(0x1d,0x54,0x2c),(0x2a,0x76,0x3e),
              (0x3c,0x9a,0x4f),(0x58,0xc1,0x5a),(0x84,0xdc,0x76)],
    "stone": [(0x1b,0x1c,0x24),(0x2b,0x2d,0x38),(0x40,0x43,0x50),(0x58,0x5c,0x69),
              (0x73,0x77,0x83),(0x94,0x98,0xa2),(0xb8,0xbc,0xc4)],
    "wood":  [(0x2a,0x18,0x0d),(0x40,0x26,0x14),(0x5c,0x38,0x1e),(0x7a,0x4c,0x29),
              (0x99,0x64,0x38),(0xb8,0x81,0x4f),(0xd4,0xa1,0x6e)],
    "skin":  [(0x5c,0x32,0x22),(0x84,0x4c,0x33),(0xad,0x6c,0x4a),(0xd0,0x91,0x66),
              (0xe8,0xb4,0x8a),(0xf6,0xd0,0xad),(0xff,0xe6,0xcd)],
    "tunic": [(0x0d,0x2a,0x18),(0x15,0x3f,0x24),(0x1f,0x5c,0x31),(0x2d,0x7a,0x42),
              (0x42,0x9b,0x55),(0x62,0xbc,0x6e),(0x8c,0xd8,0x92)],
    "purple":[(0x21,0x12,0x2c),(0x33,0x1c,0x44),(0x4a,0x2a,0x5e),(0x63,0x3c,0x78),
              (0x7f,0x53,0x92),(0x9d,0x70,0xac),(0xbd,0x93,0xc6)],
}
BLACK = (0x0d, 0x0b, 0x0f)

# 4x4 Bayer matrix: dithering between two ramp steps is how VGA art faked the
# shades a 256-colour palette still did not have.
BAYER = [[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]]


def step(ramp, i):
    return RAMPS[ramp][max(0, min(len(RAMPS[ramp]) - 1, int(round(i))))]


def dither(ramp, x, y, level):
    """level is fractional; dither between the two neighbouring ramp steps."""
    lo = math.floor(level)
    frac = level - lo
    on = (BAYER[y % 4][x % 4] + 0.5) / 16.0 < frac
    return step(ramp, lo + (1 if on else 0))


# ---------------------------------------------------------------- tiles
def blob(img, ramp, cx, cy, rx, ry, base, light=(-1, -1)):
    """A rounded lump with its own highlight and shadow. This is what makes a
    tile read as material rather than as a gradient: discrete *things* in it."""
    for y in range(int(cy - ry - 1), int(cy + ry + 2)):
        for x in range(int(cx - rx - 1), int(cx + rx + 2)):
            if not (0 <= x < 16 and 0 <= y < 16):
                continue
            nx, ny = (x - cx) / rx, (y - cy) / ry
            d = nx * nx + ny * ny
            if d > 1.0:
                continue
            lvl = base + (1.0 - d) * 1.2
            if nx * light[0] + ny * light[1] > 0.25:
                lvl += 1.4                     # lit face
            elif nx * light[0] + ny * light[1] < -0.3:
                lvl -= 1.3                     # shadowed face
            img.putpixel((x, y), dither(ramp, x, y, lvl) + (255,))


def crack(img, ramp, x0, y0, length, base, rnd):
    x, y = x0, y0
    for _ in range(length):
        if 0 <= x < 16 and 0 <= y < 16:
            img.putpixel((x, y), dither(ramp, x, y, base - 1.8) + (255,))
            if 0 <= y + 1 < 16:
                img.putpixel((x, y + 1), dither(ramp, x, y + 1, base + 0.8) + (255,))
        x += rnd.choice([0, 1, 1])
        y += rnd.choice([-1, 0, 1])


def shaded_tile(ramp, base=3.0, seed=1, grass_cap=False, bevel=True):
    """A 16x16 block with top light, bottom occlusion, dithering and grain."""
    rnd = random.Random(seed)
    img = Image.new("RGBA", (16, 16))
    for y in range(16):
        for x in range(16):
            lvl = base
            if bevel:
                # light from above: top face bright, underside in shadow
                if y == 0: lvl += 2.2
                elif y == 1: lvl += 1.3
                elif y == 2: lvl += 0.5
                if y == 15: lvl -= 2.0
                elif y == 14: lvl -= 1.1
                # side cavities so neighbouring blocks read as separate
                if x == 0: lvl += 0.5
                elif x == 15: lvl -= 0.7
            lvl += rnd.choice([-0.35, -0.15, 0, 0, 0.15, 0.35])   # grain
            img.putpixel((x, y), dither(ramp, x, y, lvl) + (255,))
    # authored features on top of the shaded base
    if ramp == "dirt":
        for _ in range(5):
            blob(img, "dirt", rnd.randrange(2, 14), rnd.randrange(4, 14),
                 rnd.uniform(1.3, 2.6), rnd.uniform(1.1, 2.0), base - 0.6)
        for _ in range(3):
            blob(img, "stone", rnd.randrange(2, 14), rnd.randrange(5, 14),
                 rnd.uniform(1.0, 1.8), rnd.uniform(0.9, 1.4), 2.6)
    elif ramp == "stone":
        # masonry: two courses, offset, with mortar and a crack
        for cy in (4, 11):
            off = 0 if cy == 4 else 8
            for cx in range(-8, 16, 8):
                x0 = cx + off
                for xx in range(max(0, x0), min(16, x0 + 7)):
                    for yy in range(cy - 3, cy + 3):
                        if 0 <= yy < 16:
                            edge = xx in (x0, x0 + 6) or yy in (cy - 3, cy + 2)
                            top = yy == cy - 3
                            lvl = base + (1.6 if top else (-1.5 if edge else 0.2))
                            img.putpixel((xx, yy), dither("stone", xx, yy, lvl) + (255,))
        crack(img, "stone", rnd.randrange(1, 8), rnd.randrange(2, 12), 7, base, rnd)
    if grass_cap:
        for x in range(16):
            h = 2 + (1 if rnd.random() < 0.45 else 0)
            for y in range(h):
                img.putpixel((x, y), step("grass", 5 - y) + (255,))
            # blades poking down into the dirt, dithered
            if rnd.random() < 0.5:
                img.putpixel((x, h), step("grass", 3) + (255,))
    return img


# ---------------------------------------------------------------- sprites
def auto_shade(rows, mapping, light=(-1, -1)):
    """Re-light flat ASCII art: distance-to-edge gives volume, and the light
    direction biases which side of each form catches it."""
    h, w = len(rows), len(rows[0])
    filled = [[rows[y][x] in mapping for x in range(w)] for y in range(h)]

    def inside(x, y):
        return 0 <= x < w and 0 <= y < h and filled[y][x]

    # chebyshev distance to the nearest pixel outside this material
    dist = [[0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            if not filled[y][x]:
                continue
            d = 0
            while d < 4:
                d += 1
                ring = [(x + dx, y + dy) for dx in range(-d, d + 1) for dy in (-d, d)]
                ring += [(x + dx, y + dy) for dy in range(-d + 1, d) for dx in (-d, d)]
                if any(not inside(px, py) for px, py in ring):
                    break
            dist[y][x] = d

    img = Image.new("RGBA", (w, h))
    for y in range(h):
        for x in range(w):
            ch = rows[y][x]
            if ch not in mapping:
                if ch == 'k':
                    img.putpixel((x, y), BLACK + (255,))
                continue
            ramp, base = mapping[ch]
            lvl = base + min(dist[y][x], 3) * 0.55
            # which way is the light coming from
            if not inside(x + light[0], y + light[1]):
                lvl += 1.5
            if not inside(x - light[0], y - light[1]):
                lvl -= 1.1
            img.putpixel((x, y), dither(ramp, x, y, lvl) + (255,))
    return img


KAYA_MAP = {'s': ("skin", 2.0), 'G': ("tunic", 2.0), 'l': ("tunic", 3.0),
            'm': ("dirt", 1.5), 'M': ("dirt", 2.5), 'y': ("wood", 4.5),
            'w': ("skin", 6.0)}
WALKER_MAP = {'p': ("purple", 2.2), 'r': ("purple", 5.0)}


def crate_tile():
    """Structure first, then shading — a crate has planks, a frame and nails."""
    img = shaded_tile("wood", 3.2, 31, bevel=False)
    rnd = random.Random(7)
    for y in range(16):
        for x in range(16):
            lvl = 3.2
            if x in (0, 15) or y in (0, 15):
                lvl = 4.6 if y == 0 or x == 0 else 1.6      # lit / shadowed frame
            elif x in (1, 14) or y in (1, 14):
                lvl = 3.9
            elif y in (5, 10):
                lvl = 1.9                                    # plank seams
            else:
                lvl = 3.2 + rnd.choice([-0.3, 0, 0, 0.3])
            img.putpixel((x, y), dither("wood", x, y, lvl) + (255,))
    for (nx, ny) in ((2, 2), (13, 2), (2, 13), (13, 13)):
        img.putpixel((nx, ny), step("stone", 5) + (255,))
        img.putpixel((nx, ny + 1), step("stone", 2) + (255,))
    return img


def upscale(img, n):
    return img.resize((img.width * n, img.height * n), Image.NEAREST)


def main():
    old_ts = Image.open("assets/tiles/tileset.png").convert("RGBA")
    old = {
        "dirt":  old_ts.crop((16, 0, 32, 16)),
        "grass": old_ts.crop((32, 0, 48, 16)),
        "stone": old_ts.crop((48, 0, 64, 16)),
        "crate": old_ts.crop((160, 0, 176, 16)),
    }
    new = {
        "dirt":  shaded_tile("dirt", 3.0, 11),
        "grass": shaded_tile("dirt", 3.0, 12, grass_cap=True),
        "stone": shaded_tile("stone", 3.2, 21),
        "crate": crate_tile(),
    }
    ok = Image.open("assets/sprites/kaya_human.png").convert("RGBA").crop((0, 0, 16, 24))
    nk = auto_shade(K_IDLE, KAYA_MAP)
    ow = Image.open("assets/sprites/enemy_walker.png").convert("RGBA").crop((0, 0, 16, 16))
    nw = auto_shade(E_WALKER1, WALKER_MAP)

    S = 7
    pad = 10
    names = list(old.keys())
    W = pad + len(names) * (16 * S + pad) + 2 * (16 * S + pad)
    H = pad + 24 * S + pad + 18
    out = Image.new("RGBA", (W, H * 2), (22, 22, 28, 255))
    x = pad
    for n in names:
        out.alpha_composite(upscale(old[n].convert("RGBA"), S), (x, pad))
        out.alpha_composite(upscale(new[n], S), (x, H + pad))
        x += 16 * S + pad
    out.alpha_composite(upscale(ok, S), (x, pad))
    out.alpha_composite(upscale(nk, S), (x, H + pad))
    x += 16 * S + pad
    out.alpha_composite(upscale(ow, S), (x, pad))
    out.alpha_composite(upscale(nw, S), (x, H + pad))
    out.convert("RGB").save("shots/_art_proto.png")
    print("wrote shots/_art_proto.png   (top row = current, bottom = prototype)")


main()
