"""The checkpoint post (docs/plan-longer-levels.md), drawn natively at ART_SCALE.

One frame is a 16x32 world-unit cell -- the tile Kaya stands in and the one
above it -- so 32x64 texels. Frames, in the order data/checkpoint.json names
them: unlit, then three lit flicker frames.

    a stone footing on the floor line, a carved post with a spiral glyph, and a
    bronze brazier bowl on top. Unlit: cold coals and a dead glyph. Lit: a
    flame of ember, gold and a white core, and the glyph burning gold.

Built with tools/art/hd_back.py's Cell, so the lighting, the weighted ink line
and the hand anti-aliasing are the props sheet's. Every lit frame differs only
in the flame, so a flicker never makes the post itself shimmer.

Run standalone (`$PYVENV tools/art/checkpoint_art.py`) to rebuild just this
sheet, or as part of tools/gen_art.py.
"""
import math
import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from art import palette                                        # noqa: E402
    from art.hd_back import Cell, K, _mask, pillow                 # noqa: E402
else:
    from . import palette
    from .hd_back import Cell, K, _mask, pillow

W, H = 16 * K, 32 * K          # texels per frame
NAME = "checkpoint"


def _post(c, lit):
    """Everything but the flame: footing, post, glyph, bowl, coals."""
    # stone footing: a wide block with a chamfered top on the floor line
    foot = _mask(W, H, lambda x, y: (5 <= x <= 26 and 57 <= y <= 63)
                 or (7 <= x <= 24 and 54 <= y < 57))
    pillow(c, foot, "stone", 3.2, span=1.1, depth=3.0)
    for x in range(7, 25):
        c.put(x, 54, "stone", 5)                    # lit top edge of the chamfer
    # the post: carved wood, slightly tapered toward the bowl
    def post(x, y):
        if not 22 <= y < 54:
            return False
        half = 4.5 + (y - 22) * 0.05
        return abs(x - 15.5) <= half
    pm = _mask(W, H, post)
    pillow(c, pm, "wood", 3.4, span=1.2, depth=3.0)
    for y in range(24, 54, 4):                      # grain rings
        for x in range(12, 20):
            if c.material(x, y) and (x + y) % 3:
                c.put(x, y, "wood", 2)
    # the spiral glyph on its face
    cx, cy = 15.5, 37.5
    for y in range(28, 48):
        for x in range(11, 21):
            fx, fy = x + 0.5 - cx, y + 0.5 - cy
            r = math.hypot(fx, fy)
            a = math.atan2(fy, fx)
            # an Archimedean spiral, r = 0.7 * theta, two turns
            on = False
            for turn in range(3):
                want = 0.7 * (a + math.pi + turn * 2 * math.pi)
                if abs(r - want) < 0.7 and r < 4.8:
                    on = True
            if on and c.material(x, y):
                if lit:
                    c.put(x, y, "gold", 6 if r < 2.2 else 5)
                else:
                    c.put(x, y, "wood", 1)
    # the brazier bowl: bronze, wider at the lip
    def bowl(x, y):
        if not 14 <= y <= 22:
            return False
        half = 11.0 - (y - 14) * 0.75
        return abs(x - 15.5) <= half
    bm = _mask(W, H, bowl)
    pillow(c, bm, "gold", 2.8, span=1.3, depth=2.5)
    for x in range(5, 27):                          # the lip
        if c.material(x, 14):
            c.put(x, 14, "gold", 5 if x < 16 else 4)
        if c.material(x, 15):
            c.put(x, 15, "gold", 1)
    # coals in the bowl's mouth
    for x in range(8, 24):
        if (x * 7) % 5 < 3:
            c.put(x, 13, "ember", 4 if lit else 1)
            if x % 3 == 0:
                c.put(x, 12, "ember", 5 if lit else 2)


def _flame(c, f):
    """One flicker frame: a teardrop of ember round gold round a white core.
    `f` sways the tip and breathes the height."""
    sway = (0.0, 1.6, -1.2)[f]
    tall = (13.0, 14.5, 12.2)[f]
    base_y = 12.5
    for y in range(0, 14):
        for x in range(4, 28):
            fy = base_y - (y + 0.5)                 # height above the bowl
            if fy < 0 or fy > tall:
                continue
            t = fy / tall
            centre = 15.5 + sway * t * t
            half = 7.6 * math.sin(math.pi * (0.18 + 0.82 * (1 - t))) * (1 - t * 0.55)
            d = abs(x + 0.5 - centre)
            if d > half:
                continue
            u = d / max(0.5, half)
            if u < 0.35 and t < 0.6:
                c.put(x, y, "metal", 6)            # white-hot core
            elif u < 0.7 and t < 0.85:
                c.put(x, y, "gold", 6 if u < 0.5 else 5)
            else:
                c.put(x, y, "ember", 5 if t < 0.7 else 4)
    # two sparks above the tip, placed by frame
    for (x, y) in (((13, 1), (19, 0)), ((18, 0), (12, 2)), ((15, 0), (20, 2)))[f]:
        c.put(x, y, "gold", 6)


def frame(lit, f=0):
    c = Cell(W, H)
    _post(c, lit)
    c.outline()
    if lit:
        # the flame is light, not an object: no ink round it
        _flame(c, f)
    c.hand_aa()
    return c.image()


def cells():
    return [frame(False)] + [frame(True, f) for f in range(3)]


def build():
    palette.sheet(NAME, cells(), W, H)


if __name__ == "__main__":
    started = palette.run_started()
    build()
    palette.publish_hd(started, (palette.SPRITES,))
    print("checkpoint: %s/%s.png" % (palette.SPRITES, NAME))
