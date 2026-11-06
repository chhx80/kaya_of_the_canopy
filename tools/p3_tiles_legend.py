#!/usr/bin/env python3
"""Kaya Refit phase 3, tiles: the per-tileset legibility sheet.

    tools/p3_tiles_sheets.py legend

For each of the five worlds, every gameplay role — solid, one-way, ladder,
water, hazard, breakable, background — is laid out as its own small room on
that world's background wall, side by side, at 1x and again at 3x, with Kaya
standing on the solid one for scale. A player has to tell those seven apart at
a glance at 1x; this sheet is where that is looked at, and the table it prints
is the same thing as numbers: each role's mean luma and its distance from the
wall behind it.

What `_compose()` reproduces of the engine: the real atlas, the real variant
manifest (the blob mask is the engine's; the position hash is a stand-in, so
*which* painting lands where differs), the ambient `bg_tint`/`fg_tint` of the
world's first level exactly as `src/world/ambience.gd::_tint()` computes it,
and the contact shadows exactly as `TileVariants.contact_bits()` decides them.
What it does not: the haze quad, the vignette, light pools, tile animation and
the parallax. Those are mood, drawn over or under everything alike; the
in-game captures (shots/p3_tiles_after_*.png) are the proof of those.
"""
import json
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from art import palette, tiles  # noqa: E402

SHOTS = os.path.join(ROOT, "shots")
TS = 16
BG = (18, 20, 26, 255)
TEXT = (232, 200, 120, 255)

WORLDS = ["jungle", "ruins", "heights", "deeps", "nest"]
#: The level whose ambience a world's sheet is lit by.
LIT_BY = {"jungle": "jungle_2", "ruins": "ruins_1", "heights": "heights_1",
          "deeps": "deeps_2", "nest": "nest_1"}

#: Each role as a 4x4-tile room, in legend characters. '.' is empty
#: foreground; the background layer of every room is the world's wall 'L',
#: except the background room, which shows all four background roles.
ROOMS = [
    ("solid", ["....", "....", "#S##", "dsdd"], None),
    ("one-way", ["....", "....", "=.==", "...."], None),
    ("ladder", [".|..", ".|..", ".|..", ".|.."], None),
    ("water", ["....", "~~~~", "wwww", "wwww"], None),
    ("hazard", ["....", "....", "^^^^", "####"], None),
    ("breakable", ["....", "..c.", ".cc.", "####"], None),
    ("background", ["##..", "....", "....", "...."], ["LLTT", "LLTT", "XXrr", "XXrr"]),
]
ROOM = 4
#: Rooms are one tile taller than wide, so Kaya (40 px) fits standing on the
#: solid room's floor; the extra row is the empty one prepended on top.
ROOM_H = ROOM + 1


def _load():
    legend = json.load(open(os.path.join(ROOT, "data", "level_legend.json")))
    data = json.load(open(os.path.join(ROOT, "data", "tiles.json")))["tiles"]
    amb = json.load(open(os.path.join(ROOT, "data", "ambience.json")))
    var = json.load(open(os.path.join(ROOT, "assets", "tiles", "variants.json")))
    atlas = Image.open(os.path.join(ROOT, "assets", "tiles", "tileset.png")).convert("RGBA")
    shadow = Image.open(os.path.join(ROOT, "assets", "tiles", "contact_shadow.png")).convert("RGBA")
    pal = json.load(open(os.path.join(ROOT, "assets", "palette.json")))["ramps"]
    return legend, data, amb, var, atlas, shadow, pal


def _tint(spec, pal):
    """src/world/ambience.gd::_tint(), in Python."""
    c = pal[spec["ramp"]][int(spec["step"])]
    peak = max(c[0], c[1], c[2], 1) / 255.0
    mix = max(0.0, min(1.0, float(spec.get("mix", 1.0))))
    scale = float(spec.get("scale", 1.0))
    return tuple((1.0 + ((ch / 255.0) / peak - 1.0) * mix) * scale for ch in c)


def _multiply(img, t):
    r, g, b, a = img.split()
    r = r.point(lambda v: min(255, int(v * t[0])))
    g = g.point(lambda v: min(255, int(v * t[1])))
    b = b.point(lambda v: min(255, int(v * t[2])))
    return Image.merge("RGBA", (r, g, b, a))


def _cell(atlas, i):
    return atlas.crop(((i % 16) * TS, (i // 16) * TS, (i % 16) * TS + TS, (i // 16) * TS + TS))


def _resolve(grid, var, x, y):
    tid = grid[y][x]
    rec = var["tiles"].get(str(tid))
    if rec is None:
        return tid
    mask = 255
    if rec["autotile"]:
        groups = var["groups"]
        g = groups.get(str(tid))
        raw = 0
        h, w = len(grid), len(grid[0])
        for dx, dy, bit in ((0, -1, 1), (1, -1, 2), (1, 0, 4), (1, 1, 8),
                            (0, 1, 16), (-1, 1, 32), (-1, 0, 64), (-1, -1, 128)):
            nx, ny = x + dx, y + dy
            n = grid[ny][nx] if 0 <= nx < w and 0 <= ny < h else tid
            if groups.get(str(n)) == g:
                raw |= bit
        mask = tiles.canon_mask(raw)
    ids = rec["cases"].get(str(mask)) or rec["cases"]["255"]
    return ids[(x * 7 + y * 13 + tid) % len(ids)]


def _solid_static(data, tid):
    d = data.get(str(tid), {})
    return bool(d.get("solid")) and not d.get("breakable") and "switch_group" not in d


def _compose(world, rooms_fg, rooms_bg, ctx):
    legend, data, amb, var, atlas, shadow, pal = ctx
    m = dict(legend["shared"])
    m.update(legend["tilesets"][world])
    level = amb["levels"][LIT_BY[world]]
    bg_t = _tint(level["bg_tint"], pal)
    fg_t = _tint(level["fg_tint"], pal)
    fg = [[m.get(ch, 0) for ch in row] for row in rooms_fg]
    bg = [[m.get(ch, 0) for ch in row] for row in rooms_bg]
    h, w = len(fg), len(fg[0])
    img = Image.new("RGBA", (w * TS, h * TS), (0, 0, 0, 255))
    bgl = Image.new("RGBA", img.size, (0, 0, 0, 0))
    fgl = Image.new("RGBA", img.size, (0, 0, 0, 0))
    cells = var["contact_shadow"]["cells"]
    for y in range(h):
        for x in range(w):
            if bg[y][x] > 0:
                bgl.alpha_composite(_cell(atlas, _resolve(bg, var, x, y)), (x * TS, y * TS))
            if fg[y][x] > 0:
                fgl.alpha_composite(_cell(atlas, _resolve(fg, var, x, y)), (x * TS, y * TS))
            elif bg[y][x] > 0:
                def cast(cx, cy):
                    return 0 <= cx < w and 0 <= cy < h and _solid_static(data, fg[cy][cx])
                n, wst = cast(x, y - 1), cast(x - 1, y)
                sides = []
                if n:
                    sides.append("n")
                if wst:
                    sides.append("w")
                if not n and not wst and cast(x - 1, y - 1):
                    sides.append("nw")
                if cast(x, y + 1):
                    sides.append("s")
                if cast(x + 1, y):
                    sides.append("e")
                for s in sides:
                    c = cells[s]
                    fgl.alpha_composite(shadow.crop((c * TS, 0, c * TS + TS, TS)), (x * TS, y * TS))
    img.alpha_composite(_multiply(bgl, bg_t))
    img.alpha_composite(_multiply(fgl, fg_t))
    return img


def _luma(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def _mean_luma(img, box):
    px = img.convert("RGB").load()
    vals = [_luma(px[x, y]) for y in range(box[1], box[3]) for x in range(box[0], box[2])]
    return sum(vals) / len(vals)


def _kaya():
    sheet = Image.open(os.path.join(palette.SPRITES, "kaya_human.png")).convert("RGBA")
    return sheet.crop((0, 0, 32, 40))


def world_sheet(world, ctx, kaya):
    rooms = []
    for name, fg_rows, bg_rows in ROOMS:
        bg_rows = bg_rows or ["LLLL"] * ROOM
        fg_rows = ["...."] + fg_rows
        bg_rows = [bg_rows[0]] + bg_rows
        rooms.append((name, _compose(world, fg_rows, bg_rows, ctx)))
    wall = _compose(world, ["...."] * ROOM, ["LLLL"] * ROOM, ctx)
    wall_l = _mean_luma(wall, (0, 0, ROOM * TS, ROOM * TS))
    # Kaya stands on the solid room, feet on its top face (row 3).
    solid = rooms[0][1]
    solid.alpha_composite(kaya, (ROOM * TS // 2 - 16, 3 * TS - 40))
    gap = 4
    one_w = len(rooms) * (ROOM * TS + gap) - gap
    one = Image.new("RGBA", (one_w, ROOM_H * TS), BG)
    for i, (_, im) in enumerate(rooms):
        one.alpha_composite(im, (i * (ROOM * TS + gap), 0))
    big = one.resize((one.width * 3, one.height * 3), Image.NEAREST)
    pad = 10
    out = Image.new("RGBA", (big.width + 2 * pad, 40 + one.height + 22 + big.height + 24 + pad), BG)
    d = ImageDraw.Draw(out)
    d.text((pad, 8), "%s — gameplay roles at 1x (top) and 3x, lit by %s's ambience, "
           "with contact shadows" % (world.upper(), LIT_BY[world]), fill=TEXT)
    out.alpha_composite(one, (pad, 26))
    y3 = 26 + one.height + 22
    for i, (name, _) in enumerate(rooms):
        d.text((pad + i * (ROOM * TS + gap) * 3 + 4, y3 - 14), name, fill=TEXT)
    out.alpha_composite(big, (pad, y3))
    # the numbers: role band luma vs the wall
    rows = []
    for name, full in rooms:
        im = full.crop((0, TS, ROOM * TS, ROOM_H * TS))     # drop the head row
        if name == "one-way":
            box = (0, 2 * TS, ROOM * TS, 2 * TS + 4)
        elif name == "ladder":
            box = (TS, 0, 2 * TS, ROOM * TS)
        elif name == "water":
            box = (0, TS, ROOM * TS, ROOM * TS)
        elif name == "hazard":
            box = (0, 2 * TS + 6, ROOM * TS, 3 * TS)
        elif name == "breakable":
            box = (TS, 2 * TS, 3 * TS, 3 * TS)
        elif name == "solid":
            box = (0, 3 * TS, ROOM * TS, ROOM * TS)
        else:
            box = (0, TS, ROOM * TS, ROOM * TS)     # under the overhang
        rows.append((name, _mean_luma(im, box)))
    stat = "  ".join("%s %.0f (%+.0f)" % (n, l, l - wall_l) for n, l in rows)
    d.text((pad, out.height - pad - 12), "mean luma, (vs the wall %.0f):  %s" % (wall_l, stat),
           fill=TEXT)
    return out, rows, wall_l


def main():
    ctx = _load()
    kaya = _kaya()
    sheets = []
    print("legibility: mean luma of each role's own pixels, and its distance from the wall")
    for world in WORLDS:
        img, rows, wall_l = world_sheet(world, ctx, kaya)
        path = os.path.join(SHOTS, "p3_tiles_legibility_%s.png" % world)
        img.save(path)
        sheets.append(img)
        print("  %-8s wall %5.1f  " % (world, wall_l)
              + "  ".join("%s %+.0f" % (n, l - wall_l) for n, l in rows))
    W = max(s.width for s in sheets)
    H = sum(s.height for s in sheets)
    out = Image.new("RGBA", (W, H), BG)
    y = 0
    for s in sheets:
        out.alpha_composite(s, (0, y))
        y += s.height
    path = os.path.join(SHOTS, "p3_tiles_legibility_all.png")
    out.save(path)
    print(path)


if __name__ == "__main__":
    main()
