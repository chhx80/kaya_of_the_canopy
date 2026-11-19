#!/usr/bin/env python3
"""Draw a whole level as one image: both tile layers from the shipped atlas,
autotiled the way src/world/tile_variants.gd does it, with every entity and
route mark on top. A review aid for levels too long to see in a few captures.

    $PYVENV tools/level_map.py jungle_1 shots/jungle_1_map.png [px_per_tile]

Not the game's renderer: no parallax, no lighting, no decor, no animation. It
answers "what is where", not "what does it look like in play" -- that is what
tools/shot.sh is for.
"""
import json, os, sys
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BIT_N, BIT_NE, BIT_E, BIT_SE, BIT_S, BIT_SW, BIT_W, BIT_NW = 1, 2, 4, 8, 16, 32, 64, 128

## Entity -> (marker colour, letter). Anything else is drawn grey with "?".
GLYPHS = {
    "player_spawn": ((80, 220, 255), "S"), "exit": ((255, 255, 255), "E"),
    "checkpoint": ((255, 200, 40), "C"), "gem": ((90, 200, 255), ""),
    "heart": ((255, 60, 90), "H"),
    "enemy_walker": ((200, 90, 255), "w"), "enemy_jumper": ((255, 90, 60), "j"),
    "enemy_shooter": ((60, 255, 120), "s"), "enemy_charger": ((255, 150, 40), "c"),
    "enemy_dropper": ((180, 180, 90), "d"), "enemy_flyer": ((255, 240, 90), "f"),
}


def canon(raw):
    m = raw & (BIT_N | BIT_E | BIT_S | BIT_W)
    for d, a, b in ((BIT_NE, BIT_N, BIT_E), (BIT_SE, BIT_E, BIT_S),
                    (BIT_SW, BIT_S, BIT_W), (BIT_NW, BIT_W, BIT_N)):
        if raw & a and raw & b and raw & d:
            m |= d
    return m


def hash_at(x, y, salt):
    h = ((x * 73856093) ^ (y * 19349663) ^ (salt * 83492791)) & 0x7fffffff
    h = ((h ^ (h >> 15)) * 2246822519) & 0x7fffffff
    h = ((h ^ (h >> 13)) * 3266489917) & 0x7fffffff
    return h ^ (h >> 16)


def main(level_id, out, ppt=8):
    lv = json.load(open(os.path.join(ROOT, "levels/%s.json" % level_id)))
    legend_doc = json.load(open(os.path.join(ROOT, "data/level_legend.json")))
    legend = dict(legend_doc["shared"])
    legend.update(legend_doc["tilesets"][lv.get("tileset", "jungle")])
    var = json.load(open(os.path.join(ROOT, "assets/tiles/variants.json")))
    atlas = Image.open(os.path.join(ROOT, "assets/tiles/tileset.png")).convert("RGBA")
    cols = int(var["atlas_columns"])
    ts = atlas.width // cols          # the atlas is drawn at art_scale, not 16 px
    tiles = var["tiles"]
    group_of = {}
    for tid, rec in tiles.items():
        group_of[int(tid)] = rec.get("group", "")
    for grp, ids in var.get("group_members", {}).items():
        for i in ids:
            group_of.setdefault(int(i), grp)

    grids = {"fg": [[legend.get(c, 0) for c in r] for r in lv["fg"]],
             "bg": [[legend.get(c, 0) for c in r] for r in lv["bg"]]}
    h, w = len(lv["fg"]), len(lv["fg"][0])

    def ident(layer, x, y):
        if x < 0 or y < 0 or x >= w or y >= h:
            return None
        return grids[layer][y][x]

    def cell(layer, x, y):
        tid = grids[layer][y][x]
        rec = tiles.get(str(tid))
        if tid <= 0 or rec is None:
            return max(tid, 0)
        mask = 255
        if rec.get("autotile"):
            grp = group_of.get(tid, "")
            raw = 0
            for bit, dx, dy in ((BIT_N, 0, -1), (BIT_NE, 1, -1), (BIT_E, 1, 0),
                                (BIT_SE, 1, 1), (BIT_S, 0, 1), (BIT_SW, -1, 1),
                                (BIT_W, -1, 0), (BIT_NW, -1, -1)):
                n = ident(layer, x + dx, y + dy)
                if n is None or group_of.get(n, "") == grp:
                    raw |= bit
            mask = canon(raw)
        cases = rec.get("cases", {})
        lst = cases.get(str(mask)) or cases.get("255") or [tid]
        return lst[hash_at(x, y, tid) % len(lst)]

    cache = {}

    def sprite(c, dim):
        key = (c, dim)
        if key not in cache:
            im = atlas.crop(((c % cols) * ts, (c // cols) * ts,
                             (c % cols + 1) * ts, (c // cols + 1) * ts))
            im = im.resize((ppt, ppt), Image.NEAREST)
            if dim < 1.0:
                px = im.load()
                for yy in range(ppt):
                    for xx in range(ppt):
                        r, g, b, a = px[xx, yy]
                        px[xx, yy] = (int(r * dim), int(g * dim), int(b * dim), a)
            cache[key] = im
        return cache[key]

    img = Image.new("RGBA", (w * ppt, h * ppt))
    d = ImageDraw.Draw(img)
    for y in range(h):          # a dusk-green sky ramp in place of the parallax
        t = y / max(1, h - 1)
        d.rectangle((0, y * ppt, w * ppt, (y + 1) * ppt),
                    fill=(int(34 + 10 * t), int(58 + 20 * t), int(66 + 6 * t), 255))
    for layer, dim in (("bg", 0.62), ("fg", 1.0)):
        for y in range(h):
            for x in range(w):
                if grids[layer][y][x] > 0:
                    s = sprite(cell(layer, x, y), dim)
                    img.alpha_composite(s, (x * ppt, y * ppt))
    for s in range(1, (w + 24) // 25):   # screen seams, faintly
        d.line((s * 25 * ppt, 0, s * 25 * ppt, h * ppt), fill=(255, 255, 255, 40))
    d.line((0, 15 * ppt, w * ppt, 15 * ppt), fill=(255, 255, 255, 40))
    r = max(2, ppt // 3)
    for e in lv["entities"]:
        col, ch = GLYPHS.get(e["type"], ((150, 150, 150), "?"))
        cx, cy = e["x"] * ppt + ppt // 2, e["y"] * ppt + ppt // 2
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col + (255,),
                  outline=(0, 0, 0, 255))
        if ch and ppt >= 8:
            d.text((cx - 3, cy - ppt - 2), ch, fill=col + (255,))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    img.convert("RGB").save(out)
    print("wrote %s (%dx%d)" % (out, img.width, img.height))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 8)
