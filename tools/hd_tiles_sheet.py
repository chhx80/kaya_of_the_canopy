#!/usr/bin/env python3
"""Review sheets for the 2x tileset (docs/hd-tiles-howto.md).

    $PYVENV tools/hd_tiles_sheet.py <world> [--scale K]

where <world> is jungle, verbs, ruins, heights, deeps or nest. Writes, for the
ids that world owns:

    shots/hd1_tiles_<world>_bases.png    every gameplay tile: today's 1x cell
                                         nearest-upscaled | the shipped 2x cell |
                                         the 2x cell tiled 2x2 (seam check)
    shots/hd1_tiles_<world>_fields.png   per autotiled material: a terrain field
                                         built from real blob cases (ledges,
                                         strips, pillars, inside corners) and a
                                         filled 4x3 field of interior variants,
                                         both on the material's own backdrop
                                         colour, with the 1x field beside it

Everything is built through the same functions the atlas is (tiles.base_hd,
tiles._cases_for_hd), so what you see is what ships. Stdout prints, per
native id, how much of the cell differs from the nearest-doubled 1x cell
(0% would mean a lazy double).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image, ImageDraw  # noqa: E402

from art import hd_tilekit as hd, palette, tiles  # noqa: E402

ROOT = palette.ROOT
WORLDS = {
    "jungle": list(range(1, 28)),
    "verbs": list(range(200, 216)),
    "ruins": list(range(220, 232)),
    "heights": list(range(240, 252)),
    "deeps": list(range(260, 272)),
    "nest": list(range(280, 292)),
}
BACKDROP = (58, 66, 92, 255)

#: '#' is the material; everything else is empty.
FIELD = [
    "................",
    "..####.....##...",
    "..####....####..",
    ".#######...##...",
    ".###..###.......",
    ".###..###..###..",
    ".########..#.#..",
    "...........###..",
    ".######.........",
    "................",
]


def _variant(cases, m, x, y):
    imgs = cases.get(m) or cases[tiles.MASK_FULL]
    return imgs[(x * 7 + y * 13) % len(imgs)]


def _mask(x, y, on):
    raw = 0
    for bit, dx, dy in ((tiles.BIT_N, 0, -1), (tiles.BIT_NE, 1, -1), (tiles.BIT_E, 1, 0),
                        (tiles.BIT_SE, 1, 1), (tiles.BIT_S, 0, 1), (tiles.BIT_SW, -1, 1),
                        (tiles.BIT_W, -1, 0), (tiles.BIT_NW, -1, -1)):
        if on(x + dx, y + dy):
            raw |= bit
    return tiles.canon_mask(raw)


#: capped tile -> the fill it caps. In a level the cap is only laid where the
#: top is open, so the field shows the pair the way a level does.
CAPPED = {2: 1, 4: 3, 221: 220, 241: 240, 261: 260, 281: 280}


def field(cases, cell, under=None):
    """`cases` paints the material; `under`, if given, paints every cell whose
    top is covered (the fill under a capped tile)."""
    rows, cols = len(FIELD), len(FIELD[0])

    def on(x, y):
        return 0 <= y < rows and 0 <= x < cols and FIELD[y][x] == "#"

    img = Image.new("RGBA", (cols * cell, rows * cell), BACKDROP)
    for y in range(rows):
        for x in range(cols):
            if on(x, y):
                m = _mask(x, y, on)
                src = under if (under is not None and m & tiles.BIT_N) else cases
                img.alpha_composite(_variant(src, m, x, y), (x * cell, y * cell))
    filled = Image.new("RGBA", (4 * cell, 3 * cell), BACKDROP)
    for y in range(3):
        for x in range(4):
            filled.alpha_composite(_variant(cases, tiles.MASK_FULL, x, y), (x * cell, y * cell))
    return img, filled


def diff_share(tid):
    lo = palette.upscale(tiles.TILE_DEFS[tid])
    hi = tiles.base_hd(tid)
    a, b = lo.tobytes(), hi.tobytes()
    n = sum(1 for i in range(0, len(a), 4) if a[i:i + 4] != b[i:i + 4])
    return n / float(hd.N * hd.N)


def _luma(p):
    return 0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2]


def seam_ratio(imgs):
    """Two numbers for a fill's interior paintings.

    wrap: the mean luma step across a cell's own wrap line (a painting beside
    itself) over the mean step across a world-unit line inside it. About 1
    means the boundary is as quiet as the material; a wrap bug or a hard
    border shows up well above it. Only a painting beside itself is measured:
    two DIFFERENT paintings always meet with uncorrelated texture, which this
    would read as a seam although the eye does not.

    bias: the mean luma of the outermost texel ring minus the mean of the
    whole cell, worst painting. A lit or dark frame -- the seam variants
    cannot hide -- shows up here."""
    n = hd.N
    inside = across = 0.0
    ni = na = 0
    bias = 0.0
    for im in imgs:
        a = im.load()
        for y in range(n):
            for x in range(hd.WU - 1, n - 1, hd.WU):
                inside += abs(_luma(a[x, y]) - _luma(a[x + 1, y]))
                inside += abs(_luma(a[y, x]) - _luma(a[y, x + 1]))
                ni += 2
        for i in range(n):
            across += abs(_luma(a[n - 1, i]) - _luma(a[0, i]))
            across += abs(_luma(a[i, n - 1]) - _luma(a[i, 0]))
            na += 2
        allm = sum(_luma(a[x, y]) for x in range(n) for y in range(n)) / float(n * n)
        ring = [a[x, y] for x in range(n) for y in range(n)
                if x in (0, n - 1) or y in (0, n - 1)]
        rm = sum(_luma(p) for p in ring) / float(len(ring))
        if abs(rm - allm) > abs(bias):
            bias = rm - allm
    return (across / na) / max(1e-6, inside / ni), bias


def main():
    world = sys.argv[1] if len(sys.argv) > 1 else "jungle"
    k = int(sys.argv[sys.argv.index("--scale") + 1]) if "--scale" in sys.argv else 4
    ids = WORLDS[world]
    N = hd.N
    out_dir = os.path.join(ROOT, "shots")

    # ---- bases
    row_h = N * 2 + 6
    sheet = Image.new("RGBA", ((N * 4 + 24) * k * 2 + 12 * k, ((len(ids) + 1) // 2) * row_h * k),
                      (24, 26, 32, 255))
    for n, tid in enumerate(ids):
        ox = (n % 2) * ((N * 4 + 24) * k + 12 * k)
        oy = (n // 2) * row_h * k
        lo = palette.upscale(tiles.TILE_DEFS[tid])
        hi = tiles.base_hd(tid)
        tile_bg = Image.new("RGBA", (N, N), BACKDROP)
        for i, im in enumerate((lo, hi)):
            c = tile_bg.copy()
            c.alpha_composite(im)
            sheet.alpha_composite(c.resize((N * k, N * k), Image.NEAREST), (ox + i * (N + 4) * k, oy))
        quad = Image.new("RGBA", (N * 2, N * 2), BACKDROP)
        for a in range(2):
            for b in range(2):
                quad.alpha_composite(hi, (a * N, b * N))
        sheet.alpha_composite(quad.resize((N * 2 * k, N * 2 * k), Image.NEAREST),
                              (ox + (2 * N + 16) * k, oy))
        ImageDraw.Draw(sheet).text((ox + 2, oy + N * k + 4), "%d %s" % (
            tid, "native" if hd.is_native(tid) else "upscaled"), fill=(230, 230, 220))
        if hd.is_native(tid):
            spec = next((s for s in tiles.VARIANT_SPECS if s["id"] == tid), None)
            interiors = (tiles._cases_for_hd(spec)[tiles.MASK_FULL] if spec
                         else [tiles.base_hd(tid)])
            opaque = all(im.getpixel((x, y))[3] == 255 for im in interiors
                         for x in range(N) for y in range(N))
            lo = ([palette.upscale(i) for i in tiles._cases_for(spec)[tiles.MASK_FULL]]
                  if spec else [palette.upscale(tiles.TILE_DEFS[tid])])
            print("  id %3d  %5.1f%% of texels differ from the nearest-doubled 1x cell%s"
                  % (tid, 100 * diff_share(tid),
                     ("   wrap %.2f bias %+5.1f  (1x: wrap %.2f bias %+5.1f) over %d paintings"
                      % (seam_ratio(interiors) + seam_ratio(lo) + (len(interiors),)))
                     if opaque else ""))
    p = os.path.join(out_dir, "hd1_tiles_%s_bases.png" % world)
    sheet.save(p)
    print(p)

    # ---- fields, per autotiled material in this world
    specs = [s for s in tiles.VARIANT_SPECS if s["id"] in ids and s["rim"] is not None]
    if not specs:
        return
    panels = []
    by_id = {s["id"]: s for s in tiles.VARIANT_SPECS}
    for spec in specs:
        hi = tiles._cases_for_hd(spec)
        lo = {m: [palette.upscale(i) for i in imgs] for m, imgs in tiles._cases_for(spec).items()}
        u_hi = u_lo = None
        if spec["id"] in CAPPED:
            us = by_id[CAPPED[spec["id"]]]
            u_hi = tiles._cases_for_hd(us)
            u_lo = {m: [palette.upscale(i) for i in imgs] for m, imgs in tiles._cases_for(us).items()}
        f_hi, fill_hi = field(hi, N, u_hi)
        f_lo, fill_lo = field(lo, N, u_lo)
        panels.append((spec["id"], f_lo, f_hi, fill_lo, fill_hi))
    fw, fh = panels[0][1].size
    gw, gh = panels[0][3].size
    sc = 2
    page = Image.new("RGBA", ((fw * 2 + gw * 2 + 60) * sc // 2, len(panels) * (fh + 30) * sc // 2),
                     (24, 26, 32, 255))
    d = ImageDraw.Draw(page)
    for n, (tid, f_lo, f_hi, g_lo, g_hi) in enumerate(panels):
        oy = n * (fh + 30) * sc // 2
        x = 0
        for im in (f_lo, f_hi, g_lo, g_hi):
            page.alpha_composite(im.resize((im.width * sc // 2, im.height * sc // 2), Image.NEAREST),
                                 (x, oy + 24))
            x += im.width * sc // 2 + 20
        d.text((4, oy + 4), "id %d: 1x field | 2x field | 1x filled | 2x filled" % tid,
               fill=(230, 230, 220))
    p = os.path.join(out_dir, "hd1_tiles_%s_fields.png" % world)
    page.save(p)
    print(p)


if __name__ == "__main__":
    main()
