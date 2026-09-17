#!/usr/bin/env python3
"""Generates all original pixel art for Kaya of the Canopy.

Everything here is authored from scratch (ASCII grids + deterministic
procedural texture, lit through the ramps in `tools/art/palette.py`).
Re-run with:  tools/genart.sh
Output goes to assets/tiles/, assets/sprites/ and assets/fonts/.

This file is only the running order. The generators themselves live in
`tools/art/`:

    art.palette    ramps, dither(), blob(), crack(), auto_shade()
    art.tiles      the tileset
    art.sprites    player forms, enemies, boss, pickups, props, projectiles
    art.backdrops  title bg, parallax planes, lighting art, logo, font, icons

Two flags, neither of which generates anything:

    --readability   measure every player form against every world and print the
                    table. Writes shots/readability.json and one preview per
                    world into shots/. See the note above readability() below.
    --preview       the same, plus the two extra panels each new world's
                    contact sheet is built from. Finish with, per world:

                      tools/grid.sh shots/world_ruins_sheet.png 2 2 \\
                        shots/world_ruins_ingame.png shots/world_ruins.png \\
                        shots/world_ruins_backdrop.png shots/world_ruins_tiles.png
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from art import backdrops, palette, sprites, tiles     # noqa: E402

ROOT = palette.ROOT

# Re-exported so `from gen_art import ...` keeps working for the small scripts
# that reach into the art (tools/proto_shade.py, tools/gen_store_shots.py).
PAL = palette.PAL
grid = palette.grid
blit = palette.blit
sheet = palette.sheet
K_IDLE = sprites.K_IDLE
# The beetle's frames are composed now, so there is no single grid to re-export
# — tools/proto_shade.py wants frame 0.
E_WALKER1 = sprites.walker(0)




# ---------------------------------------------------------------- readability
# `tools/gen_art.py --readability` and `--preview`.
#
# Why this is in the art pipeline rather than in tests/: the defect it exists to
# catch is not a crash and not a missing file, it is *the green frog being hard
# to see against the green hill parallax*, which is true of the art shipped
# today. Nothing in either test tier can see it, and neither can a screenshot
# that does not happen to have the frog standing in the wrong place.
#
# So it is measured, the way ADR 005 measures whether a level can be finished:
# composite the real scene the engine would composite — three parallax planes,
# the background tile layer, the solid tile layer — put each of the four forms
# on it at a spread of positions, and ask one question per form.
#
#   **camouflage** — walk the outline of the sprite. For every pixel on the
#   boundary, compare the sprite's own colour against the pixel of scenery
#   immediately outside it. If the two are closer together than the palette's
#   own finest step, the edge is one this art cannot draw, and it is counted
#   lost.
#
# Two figures come out of that walk and only the second one decides anything:
#
#   `lost%`  how much of the outline is camouflaged. Useful, but a sprite with
#            a wide internal range always loses its dark pixels against a dark
#            world and its bright ones against a bright world, so this number
#            is never near zero and never should be.
#   `hole%`  the largest *connected* stretch of camouflaged outline. This is
#            the one that matches what an eye does: a silhouette survives
#            scattered losses and dies when a whole side of it goes.
#
# The threshold is derived rather than chosen. Colour distance is the usual
# cheap perceptual weighting, sqrt(2dr^2 + 4dg^2 + 3db^2), and the cutoff is the
# *smallest distance between two adjacent steps of any ramp in
# assets/palette.json* — 28.6, foliage 0 to 1. Below that the palette has no
# way to express a difference at all, so neither has the player.
#
# The figures mean nothing on their own, so the two worlds that already ship
# are measured beside the four new ones. `jungle`/frog is the known defect,
# stated in the brief and visible in shots/world_jungle.png; every new world is
# expected to come in under it, and any that does not is reported as such
# rather than quietly accepted.
import json as _json
import math

_LUMA = (0.299, 0.587, 0.114)


def _luma(c):
    return _LUMA[0] * c[0] + _LUMA[1] * c[1] + _LUMA[2] * c[2]


def _dist(a, b):
    """Cheap perceptual colour distance: weighted euclidean in RGB."""
    dr, dg, db = a[0] - b[0], a[1] - b[1], a[2] - b[2]
    return math.sqrt(2.0 * dr * dr + 4.0 * dg * dg + 3.0 * db * db)


def _finest_step():
    """The smallest distance between two adjacent steps of any ramp.

    Read out of the generated manifest rather than hard-coded, so re-tuning a
    ramp re-tunes the threshold with it."""
    pal = _json.load(open(os.path.join(ROOT, "assets", "palette.json")))
    return min(_dist(steps[i], steps[i + 1])
               for steps in pal["ramps"].values()
               for i in range(len(steps) - 1))


class _Scene:
    """The composite the engine would draw, as a flat RGB image.

    Deliberately not the engine: it is the same *layer order* built from the
    same generated PNGs, and it can therefore be wrong about anything
    data/ambience.json does (tint, haze, vignette, light pools). What it is
    right about is the art, which is what is being measured. Stated plainly in
    REPORT.md rather than implied away.
    """

    W, H = 400, 240

    def __init__(self, world, fg, bg, tileset, variants):
        from PIL import Image
        self.img = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 255))
        for plane in ("sky", "far", "near"):
            path = os.path.join(palette.SPRITES, "bg_%s_%s.png" % (world, plane))
            if os.path.exists(path):
                self.img.alpha_composite(Image.open(path).convert("RGBA"))
        for layer in (bg, fg):
            for y, row in enumerate(_resolve(layer, variants)):
                for x, cell in enumerate(row):
                    if layer[y][x] == 0:
                        continue
                    self.img.alpha_composite(_cell(tileset, cell), (x * 16, y * 16))
        self.px = self.img.convert("RGB").load()


def _cell(atlas, i):
    return atlas.crop(((i % 16) * 16, (i // 16) * 16,
                       (i % 16) * 16 + 16, (i // 16) * 16 + 16))


def _resolve(grid, variants):
    """The neighbour sweep from src/world/tile_variants.gd, in Python.

    Reimplemented rather than imported because the engine's copy is GDScript.
    It has to agree with it or this measures a picture the game never draws, so
    the position hash and the canonical mask are both taken from the same two
    sources the engine uses: the hash below matches `tile_variants.gd`, and
    `canon_mask` is imported from the generator the engine's manifest came out
    of."""
    groups = {int(k): v for k, v in variants["groups"].items()}
    recs = {int(k): v for k, v in variants["tiles"].items()}
    bits = [(0, -1, 1), (1, -1, 2), (1, 0, 4), (1, 1, 8),
            (0, 1, 16), (-1, 1, 32), (-1, 0, 64), (-1, -1, 128)]
    h, w = len(grid), len(grid[0])
    out = []
    for y in range(h):
        row = []
        for x in range(w):
            tid = grid[y][x]
            rec = recs.get(tid)
            if rec is None:
                row.append(tid)
                continue
            mask = 255
            if rec["autotile"]:
                g = groups.get(tid)
                mask = 0
                for dx, dy, bit in bits:
                    nx, ny = x + dx, y + dy
                    n = grid[ny][nx] if 0 <= nx < w and 0 <= ny < h else tid
                    if groups.get(n) == g:
                        mask |= bit
                mask = tiles.canon_mask(mask)
            ids = rec["cases"][str(mask)]
            row.append(ids[abs((x * 73856093) ^ (y * 19349663)) % len(ids)])
        out.append(row)
    return out


#: One 25x15 screen per world: floor, pit, two ledges, a pillar and a ceiling.
#: The same shape for every world so the numbers are comparable.
#:
#: The left half is walled with the world's background tile and the right half
#: is left empty so the parallax shows through. Both halves are needed and the
#: first pass of this harness had only the first: it walled the whole screen,
#: never drew the backdrop at all, and duly reported that the frog on the
#: jungle parallax — the defect named in the brief and plainly visible in
#: shots/world_jungle.png — was fine. A measurement that cannot see the known
#: defect is not evidence of anything.
def _test_screen(fill_id, cap_id, bg_id):
    w, h = 25, 15
    fg = [[0] * w for _ in range(h)]
    bg = [[bg_id if x < 12 else 0 for x in range(w)] for _ in range(h)]
    for x in range(w):
        for y in range(12, h):
            fg[y][x] = fill_id
        fg[12][x] = cap_id
        fg[0][x] = fill_id
        fg[1][x] = fill_id
    for x in range(8, 15):                       # the pit
        for y in range(12, h):
            fg[y][x] = 0
    for x in range(3, 9):                        # a low ledge
        fg[8][x] = cap_id
        fg[9][x] = fill_id
    for x in range(17, 23):                      # a high ledge with a body
        fg[6][x] = cap_id
        for y in range(7, 9):
            fg[y][x] = fill_id
    for y in range(2, 6):                        # a pillar hanging off the roof
        fg[y][13] = fill_id
    return fg, bg


#: world -> (solid fill, its capped form, the background wall).
WORLD_TILES = {
    "jungle":   (1, 2, 15),
    "sky":      (1, 2, 13),
    "ruins":    (220, 221, 222),
    "heights":  (240, 241, 242),
    "deeps":    (260, 261, 262),
    "obsidian": (280, 281, 282),
}

#: Where a form is put on the test screen. Standing on the floor, standing on
#: each ledge, and twice in mid-air over the background — which is the case the
#: frog fails, because a jumping sprite has nothing but scenery behind it.
FORM_SPOTS = [
    (40, 176),      # standing on the floor, walled room
    (96, 112),      # standing on the low ledge, walled room
    (120, 150),     # mid-air in the walled room
    (300, 80),      # standing on the high ledge, open to the backdrop
    (232, 60),      # mid-air against the backdrop
    (360, 176),     # standing on the floor, open to the backdrop
    (208, 150),     # mid-air against the backdrop, lower
]


def _form_frame(name):
    """Frame 0 of a form sheet, as (w, h, pixel accessor)."""
    from PIL import Image
    img = Image.open(os.path.join(palette.SPRITES, "kaya_%s.png" % name))
    img = img.convert("RGBA")
    w = img.height          # the sheets are one row of square-ish cells
    cells = img.width // w
    assert cells >= 1
    return img.crop((0, 0, w, img.height))


def _camouflage(scene, sprite, ox, oy, cutoff):
    """(outline pixels, camouflaged, largest connected camouflaged run)."""
    sp = sprite.load()
    sw, sh = sprite.size
    outline = []
    lost = set()
    for y in range(sh):
        for x in range(sw):
            if sp[x, y][3] == 0:
                continue
            # An outline pixel is one with at least one transparent neighbour;
            # the scenery it is judged against is that neighbour's pixel.
            edge = None
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < sw and 0 <= ny < sh) or sp[nx, ny][3] == 0:
                    edge = (ox + nx, oy + ny)
                    break
            if edge is None:
                continue
            bx, by = edge
            if not (0 <= bx < scene.W and 0 <= by < scene.H):
                continue
            outline.append((x, y))
            if _dist(sp[x, y], scene.px[bx, by]) < cutoff:
                lost.add((x, y))
    # Largest connected run of lost outline, eight-connected. A silhouette dies
    # when one side of it goes, not when scattered pixels do.
    seen = set()
    biggest = 0
    for start in lost:
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        n = 0
        while stack:
            cx, cy = stack.pop()
            n += 1
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    q = (cx + dx, cy + dy)
                    if q in lost and q not in seen:
                        seen.add(q)
                        stack.append(q)
        biggest = max(biggest, n)
    return len(outline), len(lost), biggest


def _layer_separation(scene, fg, bg, tileset, variants):
    """Mean luma of the solid layer minus mean luma of the background layer.

    The second half of readability, and the one the first pass of TERMITE DEEPS
    failed outright: it does not matter how well the player reads if the player
    cannot tell which brown is the floor."""
    def mean(grid):
        n = 0
        s = 0.0
        for y, row in enumerate(_resolve(grid, variants)):
            for x, cell in enumerate(row):
                if grid[y][x] == 0:
                    continue
                px = _cell(tileset, cell).convert("RGB").load()
                for j in range(16):
                    for i in range(16):
                        s += _luma(px[i, j])
                        n += 1
        return s / max(1, n)
    return mean(fg) - mean(bg)


def readability(write_sheets=True):
    """Measure every form against every world. Returns the report as a dict."""
    from PIL import Image
    tileset = Image.open(os.path.join(palette.TILES, "tileset.png")).convert("RGBA")
    variants = _json.load(open(os.path.join(palette.TILES, "variants.json")))
    names = ("human", "frog", "fish", "bird")
    forms = {n: _form_frame(n) for n in names}
    cutoff = _finest_step()
    out = {"_cutoff": round(cutoff, 1)}
    print("\nreadability — how much of each form's outline the world swallows.")
    print("cutoff %.1f (the palette's own finest step). `hole` is the largest"
          % cutoff)
    print("connected stretch lost, and it is the number that decides.")
    print("jungle/frog is the known defect; every world should beat it.\n")
    print("  %-9s %6s  %s" % ("world", "fg-bg", " ".join(
        "%14s" % n for n in names)))
    print("  %-9s %6s  %s" % ("", "luma", " ".join(
        "%14s" % "lost / hole" for _ in names)))
    for world in sorted(WORLD_TILES):
        if world.startswith("_"):
            continue
        fill_id, cap_id, bg_id = WORLD_TILES[world]
        fg, bg = _test_screen(fill_id, cap_id, bg_id)
        scene = _Scene(world, fg, bg, tileset, variants)
        sep = _layer_separation(scene, fg, bg, tileset, variants)
        row = {}
        for name, sprite in forms.items():
            total = lost = 0
            hole = 0
            for (sx, sy) in FORM_SPOTS:
                t, l, h = _camouflage(scene, sprite, sx, sy, cutoff)
                total += t
                lost += l
                hole = max(hole, 100.0 * h / max(1, t))
            row[name] = {"lost_pct": round(100.0 * lost / max(1, total), 1),
                         "hole_pct": round(hole, 1)}
        out[world] = {"fg_minus_bg_luma": round(sep, 1), "forms": row}
        print("  %-9s %+6.1f  %s" % (world, sep, " ".join(
            "%7.1f%%/%5.1f%%" % (row[n]["lost_pct"], row[n]["hole_pct"])
            for n in names)))
        if write_sheets:
            _preview_sheet(world, scene, forms)
    path = os.path.join(ROOT, "shots", "readability.json")
    with open(path, "w") as f:
        _json.dump(out, f, indent=1, sort_keys=True)
        f.write("\n")
    print("\n  shots/readability.json written")
    return out


def _preview_sheet(world, scene, forms):
    """One 400x240 preview per world with all four forms standing in it."""
    img = scene.img.copy()
    for (name, sprite), (sx, sy) in zip(sorted(forms.items()), FORM_SPOTS):
        img.alpha_composite(sprite, (sx, sy))
    img.convert("RGB").save(os.path.join(ROOT, "shots", "world_%s.png" % world))


#: The twelve gameplay ids each new world owns, in atlas order.
WORLD_BLOCKS = {"ruins": range(220, 232), "heights": range(240, 252),
                "deeps": range(260, 272), "obsidian": range(280, 292)}


def preview_panels():
    """The other two panels of each new world's contact sheet: its parallax
    with nothing in front of it, and its twelve tiles at 4x."""
    from PIL import Image
    atlas = Image.open(os.path.join(palette.TILES, "tileset.png")).convert("RGBA")
    for world, ids in sorted(WORLD_BLOCKS.items()):
        back = Image.new("RGBA", (400, 240), (0, 0, 0, 255))
        for plane in ("sky", "far", "near"):
            path = os.path.join(palette.SPRITES, "bg_%s_%s.png" % (world, plane))
            back.alpha_composite(Image.open(path).convert("RGBA"))
        back.convert("RGB").save(
            os.path.join(ROOT, "shots", "world_%s_backdrop.png" % world))

        chart = Image.new("RGBA", (400, 240), tuple(palette.INK) + (255,))
        scale, cols = 4, 6
        gw = gh = 16 * scale + 8
        ox, oy = (400 - cols * gw) // 2, (240 - 2 * gh) // 2
        for j, i in enumerate(ids):
            src = _cell(atlas, i).resize((16 * scale, 16 * scale),
                                         Image.NEAREST)
            chart.alpha_composite(src, (ox + (j % cols) * gw + 4,
                                        oy + (j // cols) * gh + 4))
        chart.convert("RGB").save(
            os.path.join(ROOT, "shots", "world_%s_tiles.png" % world))
    print("  shots/world_*_{backdrop,tiles}.png written")


def main():
    if "--readability" in sys.argv:
        readability()
        return
    if "--preview" in sys.argv:
        readability(write_sheets=True)
        preview_panels()
        return
    palette.write_manifest()
    tiles.build_tileset()
    sprites.build_sprites()
    sprites.build_boss()
    backdrops.build_font()
    backdrops.build_logo()
    backdrops.build_title_bg()
    backdrops.build_backdrops()
    backdrops.build_light_art()
    backdrops.build_icon()
    backdrops.build_store_icons()
    print("done")


if __name__ == "__main__":
    main()
