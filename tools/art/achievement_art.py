"""Achievement images for App Store Connect: one per world, 1024x1024.

Each is that world's boss, taken from its own generated sprite sheet, on a
medallion in the world's colours. Game Center crops achievement art to a
circle and wants a flattened RGB image, so everything that matters sits inside
the centre circle and there is no transparency. Original art like the rest:
built only from assets this project generates.

Run: tools/genart.sh does not call this (the images are not part of the game);
`$PYVENV -m tools.art.achievement_art` or `$PYVENV tools/art/achievement_art.py`.
Writes export/achievements/<achievement id>.png.
"""

import json
import math
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SIZE = 1024
OUT = os.path.join(ROOT, "export", "achievements")

# boss id per level, and a world's palette: (outer, inner, rim, glow)
BOSS = {"jungle_5": "boss_grove", "ruins_5": "tide_maw", "heights_5": "stormcrest",
        "deeps_5": "brood_queen", "nest_5": "obsidian_heart"}
COLOURS = {
    "jungle":  ((0x0c, 0x24, 0x16), (0x1d, 0x5c, 0x3b), (0xe2, 0xb8, 0x4f), (0x58, 0xc1, 0x5a)),
    "ruins":   ((0x0e, 0x18, 0x24), (0x2b, 0x45, 0x5a), (0xb8, 0xd4, 0xd0), (0x41, 0xa6, 0xb5)),
    "heights": ((0x3a, 0x16, 0x14), (0xa0, 0x4a, 0x2e), (0xf2, 0xd5, 0x65), (0xff, 0xc2, 0x62)),
    "deeps":   ((0x10, 0x0b, 0x08), (0x3a, 0x23, 0x14), (0xc2, 0x8f, 0x5d), (0xe8, 0xa8, 0x3c)),
    "nest":    ((0x12, 0x08, 0x10), (0x40, 0x1a, 0x2c), (0xe4, 0x7a, 0x3c), (0xff, 0x6a, 0x3a)),
}


def _frame(boss):
    meta = json.load(open(os.path.join(ROOT, "data", "enemies", boss + ".json")))
    sheet = Image.open(os.path.join(ROOT, "assets", "sprites",
                                    os.path.basename(meta["sprite"]))).convert("RGBA")
    fw, fh = int(meta["frame_w"]), int(meta["frame_h"])
    cell = sheet.crop((0, 0, fw, fh))
    box = cell.getbbox() or (0, 0, fw, fh)
    return cell.crop(box)


def medallion(entry):
    world = entry["level"].split("_")[0]
    outer, inner, rim, glow = COLOURS[world]
    img = Image.new("RGB", (SIZE, SIZE), outer)
    d = ImageDraw.Draw(img)
    c = SIZE // 2
    # concentric bands, stepped like the game's dithered ramps rather than smooth
    for i in range(12, -1, -1):
        t = i / 12.0
        r = int(SIZE * 0.47 * (0.55 + 0.45 * t))
        col = tuple(int(inner[k] + (outer[k] - inner[k]) * t) for k in range(3))
        d.ellipse((c - r, c - r, c + r, c + r), fill=col)
    # sunburst behind the boss
    for k in range(24):
        a0 = k * math.tau / 24
        a1 = a0 + math.tau / 48
        r = SIZE * 0.40
        pts = [(c, c), (c + r * math.cos(a0), c + r * math.sin(a0)),
               (c + r * math.cos(a1), c + r * math.sin(a1))]
        band = tuple(int(inner[j] * 0.7 + glow[j] * 0.3) for j in range(3))
        d.polygon(pts, fill=band)
    # rim, inside the circle Game Center keeps
    rr = int(SIZE * 0.455)
    d.ellipse((c - rr, c - rr, c + rr, c + rr), outline=rim, width=26)
    d.ellipse((c - rr + 34, c - rr + 34, c + rr - 34, c + rr - 34), outline=(0x0d, 0x0b, 0x0f), width=6)
    # the boss, pixel-scaled with nearest neighbour so it stays pixel art
    boss = _frame(BOSS[entry["level"]])
    scale = max(1, int((SIZE * 0.52) / max(boss.width, boss.height)))
    big = boss.resize((boss.width * scale, boss.height * scale), Image.NEAREST)
    shadow = Image.new("RGBA", big.size, (0, 0, 0, 0))
    shadow.paste((0x0d, 0x0b, 0x0f, 150), mask=big.split()[3])
    x = c - big.width // 2
    y = c - big.height // 2 + int(SIZE * 0.02)
    img.paste(shadow, (x + scale * 2, y + scale * 2), shadow)
    img.paste(big, (x, y), big)
    return img


def main():
    os.makedirs(OUT, exist_ok=True)
    entries = json.load(open(os.path.join(ROOT, "data", "achievements.json")))["achievements"]
    for e in entries:
        path = os.path.join(OUT, e["id"] + ".png")
        medallion(e).save(path)
        print("wrote", os.path.relpath(path, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
