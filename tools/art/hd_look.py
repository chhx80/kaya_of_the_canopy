#!/usr/bin/env python3
"""HD look sample (docs/plan-hd.md, phase H0): what native double-resolution
art looks like, as images the owner can judge before five agents redraw
everything. Nothing here is wired into the game; nothing here writes to
assets/.

    tools/art/hd_look.py            (run with the project venv, from the root)

writes
    shots/hd_look_compare.png       Kaya and each tile: today's 1x, the same
                                    nearest-upscaled to 2x ("bigger pixels",
                                    the plan's step 1), and native 2x -- all
                                    three at the same on-screen size
    shots/hd_look_scene.png         a mock frame: today's framing (400x240) and
                                    art beside the new framing (308x184 world
                                    units = 616x368 texels) in native 2x art,
                                    both scaled to the same device height
    shots/hd_look_scene_steps.png   the new framing three ways: today's art
                                    upscaled, native 2x, and the two cropped
                                    to Kaya at device pixels
    shots/hd_look_sheet.png         Kaya's HD frames, each group over its 1x
                                    counterpart

The scene is composited here, in Python, from the same tiles and frames; it
is not a capture of the running game, so it has none of the engine's haze,
lights or autotiled edges -- and neither side of the comparison does.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from art import kaya40, palette, tiles  # noqa: E402

ROOT = palette.ROOT
SHOTS = os.path.join(ROOT, "shots")
with open(os.path.join(ROOT, "data", "display.json")) as fh:
    DISPLAY = json.load(fh)
S = int(DISPLAY["art_scale"])
VIEW_W, VIEW_H = int(DISPLAY["view_w"]), int(DISPLAY["view_h"])
OLD_W, OLD_H = 400, 240                      # Screen.W/H: today's view
DEVICE_H = 736                               # both frames are shown this tall
TS = tiles.TS

BG = (24, 26, 32, 255)
INK_TXT = (232, 228, 214)
DIM_TXT = (150, 150, 160)


def font(size):
    return ImageFont.load_default(size=size)


def label(draw, xy, text, size=18, fill=INK_TXT):
    draw.text(xy, text, font=font(size), fill=fill)


def nearest(img, k):
    return img.resize((img.width * k, img.height * k), Image.NEAREST)


def sharp_bilinear(img, h):
    """What the engine's presentation filter does: nearest up to the whole
    multiple at or above the target, then bilinear down to it exactly, so
    pixel edges stay sharp and only the last fraction is blended."""
    w = round(img.width * h / img.height)
    k = -(-h // img.height)
    return nearest(img, k).resize((w, h), Image.BILINEAR)


def on(img, colour):
    out = Image.new("RGBA", img.size, colour)
    out.alpha_composite(img)
    return out


# ------------------------------------------------------------------ Kaya
def kaya_1x(i):
    """Frame i of today's sheet, lit and outlined exactly as it ships."""
    return kaya40.render(kaya40.frames()[i])


_HD = None


def kaya_hd():
    global _HD
    if _HD is None:
        _HD = kaya40.hd_cells()
    return _HD


# ------------------------------------------------------------------ 1. compare
def compare():
    hd = kaya_hd()
    poses = [(0, "Kaya idle"), (5, "Kaya run (frame 3)"), (13, "Kaya jump apex")]
    k_bg = palette.RAMPS["foliage"][3] + (255,)
    t_bg = palette.RAMPS["water"][4] + (255,)
    cw, ch = kaya40.W * 8, kaya40.H * 8                      # 256 x 320 on screen
    tw = TS * 8                                               # 128 on screen
    gap, left, top = 12, 24, 96
    col_w = 3 * (tw + 8) + 24
    width = max(left + 3 * (cw + gap) + 24, left + 2 * col_w + 40 + 24)
    tile_rows = (len(tiles.HD_SLICE) + 1) // 2
    height = top + len(poses) * (ch + 40) + 40 + tile_rows * (tw + 40) + 24
    out = Image.new("RGBA", (width, height), BG)
    d = ImageDraw.Draw(out)
    label(d, (left, 16), "HD look sample: same on-screen size, three ways", 26)
    label(d, (left, 54), "columns, left to right:  today (1x)  |  today upscaled 2x "
                         "(bigger pixels, plan step 1)  |  native 2x (new detail)", 17, DIM_TXT)
    y = top
    for i, name in poses:
        lo = on(kaya_1x(i), k_bg)
        hi = on(hd[i], k_bg)
        label(d, (left, y), name, 18)
        y += 26
        out.alpha_composite(nearest(lo, 8), (left, y))
        out.alpha_composite(nearest(nearest(lo, S), 8 // S), (left + cw + gap, y))
        out.alpha_composite(nearest(hi, 8 // S), (left + 2 * (cw + gap), y))
        y += ch + 14
    y += 20
    for n, (tid, name, build) in enumerate(tiles.HD_SLICE):
        cx = left + (n % 2) * (col_w + 40)
        cy = y + (n // 2) * (tw + 40)
        lo = on(tiles.TILE_DEFS[tid], t_bg)
        hi = on(build(), t_bg)
        label(d, (cx, cy), "%s  (id %d)" % (name, tid), 16)
        cy += 22
        out.alpha_composite(nearest(lo, 8), (cx, cy))
        out.alpha_composite(nearest(nearest(lo, S), 8 // S), (cx + tw + 8, cy))
        out.alpha_composite(nearest(hi, 8 // S), (cx + 2 * (tw + 8), cy))
    path = os.path.join(SHOTS, "hd_look_compare.png")
    out.save(path)
    return path


# ------------------------------------------------------------------ 2. scene
# A small stretch of jungle, 25 x 15 tiles = exactly today's view. Each
# character is one tile from the slice; layers are background then solid.
BG_MAP = [
    "lllllllllllllllllllllllll",
    "lllllllllllllllllllllllll",
    "lllllllllllll.lllllllllll",
    "llltll.lll.l...lll.lltlll",
    "l..t.l.......l......l.t..",
    "...t..................t..",
    "...t..................t..",
    "...t..................t..",
    "...t..................t..",
    "...t..................t..",
    "...t..................t..",
    "...t..................t..",
    ".........................",
    ".........................",
    ".........................",
]
FG_MAP = [
    ".........................",
    ".........................",
    ".........................",
    ".........................",
    "................ppp......",
    ".................v.......",
    ".................v.......",
    ".................v.......",
    "..........ppp....v.......",
    ".................v...ssss",
    ".................v...ssss",
    "...c..^^.........v..Gssss",
    "GGGcGGGGGG~~~~~GGGGGDdddd",
    "dddddddddd=====dddddddddd",
    "dddddddddd=====dddddddddd",
]
FG_TILES = {'G': 2, 'd': 1, 's': 3, 'p': 5, 'v': 6, '~': 7, '=': 8,
            '^': 9, 'c': 10, 'D': 1}
BG_TILES = {'l': 13, 't': 14}
HD_BUILD = {tid: build for tid, _, build in tiles.HD_SLICE}

# Feet positions in world units. The new view is the same world, cropped to
# VIEW_W x VIEW_H, centred horizontally and resting on the bottom edge.
KAYA_IDLE = (150.0, 192.0)
KAYA_RUN = (262.0, 192.0)
CAM = ((OLD_W - VIEW_W) / 2.0, float(OLD_H - VIEW_H))


def backdrop(scale, view_w, view_h, cam):
    """Today's jungle parallax planes, at the scroll they would have for this
    camera. Not part of the sample: at 2x they are nearest-upscaled."""
    out = Image.new("RGBA", (view_w * scale, view_h * scale), (0, 0, 0, 255))
    for plane, factor in (("sky", 0.1), ("far", 0.3), ("near", 0.55)):
        img = Image.open(os.path.join(ROOT, "assets", "sprites",
                                      "bg_jungle_%s.png" % plane)).convert("RGBA")
        img = nearest(img, scale)
        ox = int(cam[0] * factor * scale)
        oy = max(0, img.height - view_h * scale - int((OLD_H - view_h - cam[1]) * scale * factor))
        out.alpha_composite(img.crop((ox, oy, ox + out.width, oy + out.height)))
    return out


def _paste(dst, src, xy):
    """alpha_composite that tolerates a source hanging off the edge."""
    x, y = xy
    box = (max(0, -x), max(0, -y), min(src.width, dst.width - x), min(src.height, dst.height - y))
    if box[2] > box[0] and box[3] > box[1]:
        dst.alpha_composite(src.crop(box), (x + box[0], y + box[1]))


def level(scale, tile_of, view_w, view_h, cam, kaya_of):
    out = backdrop(scale, view_w, view_h, cam)
    t = TS * scale
    ox, oy = int(round(cam[0] * scale)), int(round(cam[1] * scale))
    for grid, table in ((BG_MAP, BG_TILES), (FG_MAP, FG_TILES)):
        for r, row in enumerate(grid):
            for c, chx in enumerate(row):
                if chx in table:
                    _paste(out, tile_of(table[chx], r, c), (c * t - ox, r * t - oy))
    for (fx, fy), frame in ((KAYA_IDLE, kaya_of(0)), (KAYA_RUN, kaya_of(5))):
        x = int(round((fx - kaya40.CX) * scale)) - ox
        y = int(round((fy - kaya40.H) * scale)) - oy
        _paste(out, frame, (x, y))
    return out


_hd_tiles = {}


def hd_tile(tid, r, c):
    if tid not in _hd_tiles:
        _hd_tiles[tid] = HD_BUILD[tid]()
    return _hd_tiles[tid]


def old_tile(tid, r, c):
    return tiles.TILE_DEFS[tid]


def up_tile(tid, r, c):
    return nearest(tiles.TILE_DEFS[tid], S)


_k1 = {}


def old_kaya(i):
    if i not in _k1:
        _k1[i] = kaya_1x(i)
    return _k1[i]


def frames():
    """(today's frame at 1x, the new frame upscaled, the new frame native)."""
    old = level(1, old_tile, OLD_W, OLD_H, (0.0, 0.0), old_kaya)
    up = level(S, up_tile, VIEW_W, VIEW_H, CAM, lambda i: nearest(old_kaya(i), S))
    hd = level(S, hd_tile, VIEW_W, VIEW_H, CAM, lambda i: kaya_hd()[i])
    return old, up, hd


def scene():
    old, up, hd = frames()
    assert hd.size == (VIEW_W * S, VIEW_H * S), hd.size
    a = sharp_bilinear(old, DEVICE_H)
    b = sharp_bilinear(hd, DEVICE_H)
    # the new view's footprint, drawn on today's frame
    da = ImageDraw.Draw(a)
    k = DEVICE_H / OLD_H
    x0, y0 = CAM[0] * k, CAM[1] * k
    da.rectangle((x0, y0, x0 + VIEW_W * k - 1, y0 + VIEW_H * k - 1),
                 outline=(255, 214, 92, 255), width=3)
    gap, top = 24, 70
    out = Image.new("RGBA", (a.width + b.width + gap * 3, DEVICE_H + top + 50), BG)
    out.alpha_composite(a, (gap, top))
    out.alpha_composite(b, (gap * 2 + a.width, top))
    d = ImageDraw.Draw(out)
    label(d, (gap, 14), "TODAY: 400x240 world units, 1x art", 24)
    label(d, (gap, 42), "yellow box = what the new camera sees", 16, DIM_TXT)
    label(d, (gap * 2 + a.width, 14),
          "NEW: %dx%d world units = %dx%d texels, native 2x art" % (VIEW_W, VIEW_H,
                                                                    VIEW_W * S, VIEW_H * S), 24)
    label(d, (gap * 2 + a.width, 42),
          "both frames shown %d px tall through sharp-bilinear, as on a device" % DEVICE_H,
          16, DIM_TXT)
    label(d, (gap, top + DEVICE_H + 14),
          "Composited in Python, not captured from the engine: no haze, lights or "
          "autotiled edges on either side. Parallax backdrop is today's art "
          "(nearest-upscaled on the right); it is not part of this sample.", 15, DIM_TXT)
    path = os.path.join(SHOTS, "hd_look_scene.png")
    out.save(path)
    hd.save(os.path.join(SHOTS, "hd_look_scene_native_616x368.png"))
    return path, (old, up, hd)


def scene_steps(frames_):
    old, up, hd = frames_
    a = nearest(up, 2)
    b = nearest(hd, 2)
    # crops around the running Kaya at 4 device pixels per texel
    cx = int(round((KAYA_RUN[0] - CAM[0]) * S))
    cy = int(round((KAYA_RUN[1] - CAM[1]) * S))
    box = (cx - 110, cy - 124, cx + 70, cy + 24)
    ca, cb = nearest(up.crop(box), 4), nearest(hd.crop(box), 4)
    gap, top = 24, 56
    w = a.width * 2 + gap * 3
    h = top + a.height + 50 + ca.height + 40
    out = Image.new("RGBA", (w, h), BG)
    d = ImageDraw.Draw(out)
    label(d, (gap, 14), "NEW FRAMING, plan step 1: today's art nearest-upscaled", 22)
    label(d, (gap * 2 + a.width, 14), "NEW FRAMING, plan step 2: native 2x", 22)
    out.alpha_composite(a, (gap, top))
    out.alpha_composite(b, (gap * 2 + a.width, top))
    y = top + a.height + 16
    label(d, (gap, y), "close-up, 4 device px per texel", 18, DIM_TXT)
    out.alpha_composite(ca, (gap, y + 30))
    out.alpha_composite(cb, (gap * 2 + a.width, y + 30))
    path = os.path.join(SHOTS, "hd_look_scene_steps.png")
    out.save(path)
    return path


# ------------------------------------------------------------------ 3. sheet
def sheet():
    hd = kaya_hd()
    groups = [("idle", range(0, 2), range(0, 2)), ("run", range(2, 10), range(2, 10)),
              ("jump", range(10, 16), range(10, 16)),
              ("stoop + stoop walk", range(16, 23), range(39, 46))]
    bg = palette.RAMPS["foliage"][3] + (255,)
    cw, chh = kaya40.HW * 3, kaya40.HH * 3                # 192 x 240 per frame
    gap, left = 8, 24
    width = left + 8 * (cw + gap) + 16
    height = 60 + sum(30 + chh * 2 + gap * 2 + 20 for _ in groups)
    out = Image.new("RGBA", (width, height), BG)
    d = ImageDraw.Draw(out)
    label(d, (left, 14), "Kaya, native 2x (64x80 cell), each group over today's 1x "
                         "at the same size", 22)
    y = 56
    for name, hd_idx, lo_idx in groups:
        label(d, (left, y), name, 20)
        y += 30
        for col, (i, j) in enumerate(zip(hd_idx, lo_idx)):
            x = left + col * (cw + gap)
            out.alpha_composite(nearest(on(kaya_1x(j), bg), 3 * S), (x, y))
            out.alpha_composite(nearest(on(hd[i], bg), 3), (x, y + chh + gap))
        y += chh * 2 + gap * 2 + 20
    path = os.path.join(SHOTS, "hd_look_sheet.png")
    out.save(path)
    return path


def main():
    os.makedirs(SHOTS, exist_ok=True)
    print(compare())
    p, fr = scene()
    print(p)
    print(scene_steps(fr))
    print(sheet())


if __name__ == "__main__":
    main()
