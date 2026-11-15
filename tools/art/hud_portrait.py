"""The HUD portrait (Kaya Refit phase 3): Kaya's head and shoulders beside
the hearts, cut from her puppet rather than drawn.

Both frames are `kaya40.front()` poses, lit by the same `auto_shade` and
inked by the same selective outline as her sheet, so the portrait is her by
construction -- change the puppet and the portrait follows. Frame 0 is the
smile, frame 1 eyes shut, which src/ui/hud.gd shows for a moment when she is
hit.

The cell is CELL px square: a one-pixel ink frame, a lit top-left bevel on a
dark panel, and the bust cropped so the hat brim reaches the frame on both
sides. Nothing here is outside the ramps: tests/test_hud_portrait.gd checks.

HD pass (docs/plan-hd.md, H1): the portrait ships natively at ART_SCALE
texels per unit. The bust is `kaya40.front_hd()` -- the same pose at 2x, with
her face, hair strands and the woven brim -- and the panel is drawn at 2x too:
the ink frame keeps its one-unit weight, the bevel is a two-step gradient, and
the panel's shade bands are whole steps with a leaf-shadow pattern instead of
a Bayer checkerboard, which reads as screen-door at 2x.
"""
import os

from PIL import Image

from . import kaya40, palette

CELL = 24
#: the window of the 32x40 puppet cell that becomes the bust: hat to beads
CROP = (4, 0, 28, 21)
#: texels per world unit (kaya40.HD_SCALE == palette.ART_SCALE)
S = kaya40.HD_SCALE


def _bust(pose):
    rows = kaya40.front_hd(pose)
    img = kaya40.light_hd(rows)
    palette.selective_outline(img)
    return img.crop(tuple(v * S for v in CROP))


def _frame():
    n = CELL * S
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    px = img.load()
    for y in range(n):
        for x in range(n):
            if min(x, y, n - 1 - x, n - 1 - y) < S:                                   # ink, one unit
                c = palette.INK
            elif min(x, y) < 2 * S:
                # lit bevel, top and left: bright on the outside, a step in
                c = palette.step("foliage", 4 if min(x, y) == S else 3)
            elif max(x, y) >= n - 2 * S:                   # shadow bevel
                c = palette.step("foliage", 0 if max(x, y) == n - 1 - S else 1)
            else:
                # the panel: dark canopy green, a step lighter toward the top
                # so the brim sits on shade, and the soft dapple of a leaf
                # shadow falling across it
                lvl = 2 if y < n * 0.35 else 1
                if lvl == 1 and ((x * 3 + y * 5) % 23 == 0 or (x - y) % 17 == 0 and y % 3 == 0):
                    lvl = 2
                if lvl == 2 and y >= n * 0.3 and (x + 2 * y) % 5 == 0:
                    lvl = 1
                c = palette.step("foliage", lvl)
            px[x, y] = c + (255,)
    return img


def build():
    frames = []
    for pose in (dict(smile=True), dict(eyes=False)):
        cell = _frame()
        bust = _bust(pose)
        # inside the frame, brim flush with the top bevel, shoulders on the
        # bottom bevel; the inner window is CELL-4 wide, the bust 24, so the
        # brim tips are clipped by the frame, which reads as "in a window"
        inner = Image.new("RGBA", ((CELL - 4) * S, (CELL - 4) * S), (0, 0, 0, 0))
        inner.alpha_composite(bust, (-2 * S, 0))
        cell.alpha_composite(inner, (2 * S, 2 * S))
        frames.append(cell)
    sheet = Image.new("RGBA", (CELL * S * len(frames), CELL * S), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        sheet.alpha_composite(f, (i * CELL * S, 0))
    path = os.path.join(palette.SPRITES, "hud_portrait.png")
    sheet.save(path)
    return path
