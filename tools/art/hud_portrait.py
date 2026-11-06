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
"""
import os

from PIL import Image

from . import kaya40, palette

CELL = 24
#: the window of the 32x40 puppet cell that becomes the bust: hat to beads
CROP = (4, 0, 28, 21)


def _bust(pose):
    rows = kaya40.front(pose)
    img = palette.auto_shade(rows, kaya40.MAT, rate=0.45, lit=0.9, dark=0.8)
    palette.selective_outline(img)
    return img.crop(CROP)


def _frame():
    img = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
    for y in range(CELL):
        for x in range(CELL):
            if x in (0, CELL - 1) or y in (0, CELL - 1):
                img.putpixel((x, y), palette.INK + (255,))
            elif x == 1 or y == 1:
                img.putpixel((x, y), palette.step("foliage", 3) + (255,))
            elif x == CELL - 2 or y == CELL - 2:
                img.putpixel((x, y), palette.step("foliage", 0) + (255,))
            else:
                # the panel: dark canopy green, a touch lighter toward the top
                # so the hat brim, the lightest thing on her, sits on shade
                img.putpixel((x, y), palette.dither("foliage", x, y, 1.6 - y / 40.0) + (255,))
    return img


def build():
    frames = []
    for pose in (dict(smile=True), dict(eyes=False)):
        cell = _frame()
        bust = _bust(pose)
        # inside the frame, brim flush with the top bevel, shoulders on the
        # bottom bevel; the inner window is CELL-4 wide, the bust 24, so the
        # brim tips are clipped by the frame, which reads as "in a window"
        inner = Image.new("RGBA", (CELL - 4, CELL - 4), (0, 0, 0, 0))
        inner.alpha_composite(bust, (-2, 0))
        cell.alpha_composite(inner, (2, 2))
        frames.append(cell)
    sheet = Image.new("RGBA", (CELL * len(frames), CELL), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        sheet.alpha_composite(f, (i * CELL, 0))
    path = os.path.join(palette.SPRITES, "hud_portrait.png")
    sheet.save(path)
    return path
