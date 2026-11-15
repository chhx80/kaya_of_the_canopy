"""Her boomerang blade and the projectile sheet, drawn natively at ART_SCALE.

docs/plan-hd.md step 2. The 1x sheets (tools/art/sprites.py I_BLADE1/2,
P_SHOT, P_SPARK) were a white ring and two 6-px blobs. At two texels per world
unit there is room for what a thrown blade is made of, so each texel is chosen
here from polar coordinates rather than rasterised from a grid:

  * blade.png, two 16x16-unit spin frames: a ring-blade (a chakram) with four
    swept teeth, a bevelled cutting edge that is brightest where it faces the
    light, a fuller groove round the middle of the steel, a leather-wrapped
    grip across one segment, and a star glint on the rim. Frame 0 has its teeth
    on the diagonals (the 1x frame's rounded square), frame 1 on the axes (its
    diamond), so the spin reads the way it read at 1x. The glint stays put
    while the steel turns: it belongs to the light, not to the blade.
  * projectiles.png, two 8x8-unit frames: 0 the enemy shot (a purple orb with
    a swirling hot core, a rim light and a dark lower edge), 1 the fish's bite
    flash (a gold four-point burst with a white-hot centre).

Same footprints as 1x, so the hitboxes in data/weapons and data/enemies still
describe what is drawn. Every colour is a palette ramp step.
"""

import math

from PIL import Image

from . import palette

S = palette.ART_SCALE
LIGHT = (-0.7071, -0.7071)          # palette.LIGHT, normalised: upper left


def _px(img, x, y, ramp, lvl):
    if 0 <= x < img.width and 0 <= y < img.height:
        img.putpixel((x, y), palette.step(ramp, lvl) + (255,))


# ===================================================================== blade
# Centre of the 1x ring (columns 2-11, rows 3-12 of the 16 px cell), in world
# units; radii in world units.
BLADE_C = (7.0, 8.0)
R_OUT, R_IN, TOOTH = 3.9, 2.1, 1.6


def _blade(teeth_at):
    """One spin frame. `teeth_at` is the angle of the first tooth, degrees."""
    n = 16 * S
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    cx, cy = BLADE_C[0] * S, BLADE_C[1] * S
    t0 = math.radians(teeth_at)
    grip_mid = t0 + math.radians(45.0 + 90.0)          # between two teeth
    body = {}
    for y in range(n):
        for x in range(n):
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            r = math.hypot(dx, dy) / S
            th = math.atan2(dy, dx)
            # a tooth: the rim swept out to a hooked point, trailing the spin
            ph = ((th - t0) % (math.pi / 2)) / (math.pi / 2)        # 0..1 between teeth
            bump = TOOTH * max(0.0, 1.0 - ph / 0.34) ** 1.3
            rout = R_OUT + bump
            if R_IN <= r <= rout:
                body[(x, y)] = (r, th, rout)
    for (x, y), (r, th, rout) in body.items():
        dx, dy = (x + 0.5 - cx) / S, (y + 0.5 - cy) / S
        rr = math.hypot(dx, dy) or 1.0
        face = (dx * LIGHT[0] + dy * LIGHT[1]) / rr       # +1 facing the light
        out_d = (rout - r) * S                            # texels from the edge
        in_d = (r - R_IN) * S
        dg = abs(((th - grip_mid + math.pi) % (2 * math.pi)) - math.pi)
        if dg < math.radians(22) and out_d >= 1.0 and in_d >= 0.5:
            # leather wrap: diagonal turns of cord, lit toward the light
            wrap = int(math.floor((th * 9.0 / math.pi * S) + r * S * 0.9)) % 3
            lvl = 3.0 + face * 1.2 - (1.6 if wrap == 0 else 0.0)
            _px(img, x, y, "dirt", lvl)
            continue
        if out_d < 1.0:                       # the cutting edge
            _px(img, x, y, "metal", 6.0 if face > -0.3 else 4.6)
        elif out_d < 2.0:                     # bevel
            _px(img, x, y, "metal", 5.3 + face * 0.8)
        elif in_d < 1.0:                      # inner edge, the ring's own shadow
            _px(img, x, y, "metal", 2.6 - face * 0.8)
        elif abs(r - (R_IN + 0.95)) < 0.3:    # the fuller groove
            _px(img, x, y, "metal", 3.2 + face * 0.6)
        else:                                 # flat of the steel
            _px(img, x, y, "metal", 4.6 + face * 1.0)
    # dark rim all round, the 1x sheet's 'A' line, so it reads on bright sky
    px = img.load()
    rim = []
    for y in range(n):
        for x in range(n):
            if px[x, y][3]:
                continue
            for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if 0 <= x + ox < n and 0 <= y + oy < n and px[x + ox, y + oy][3] \
                        and px[x + ox, y + oy][:3] != palette.step("metal", 1):
                    rim.append((x, y))
                    break
    for x, y in rim:
        d = math.hypot(x + 0.5 - cx, y + 0.5 - cy) / S
        _px(img, x, y, "metal", 1 if d > (R_IN + R_OUT) / 2 else 0)
    # the glint: a four-point star on the rim where it faces the light
    gx = int(cx + LIGHT[0] * (R_OUT - 0.4) * S)
    gy = int(cy + LIGHT[1] * (R_OUT - 0.4) * S)
    for k, (ox, oy) in enumerate(((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1),
                                  (2, 0), (-2, 0), (0, 2), (0, -2))):
        _px(img, gx + ox, gy + oy, "metal", 6 if k < 5 else 5)
    _px(img, gx - 1, gy - 1, "gold", 6)
    return img


def blade_cells():
    """0 teeth on the diagonals, 1 teeth on the axes -- data/weapons/blade.json
    `frames: [0, 1]` at spin_fps."""
    return [_blade(45.0), _blade(0.0)]


# =============================================================== projectiles
def _orb():
    """The enemy shot: 8x8 units, the 1x orb's footprint (a 3-unit radius)."""
    n = 8 * S
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    c = 4.0 * S
    for y in range(n):
        for x in range(n):
            dx, dy = (x + 0.5 - c) / S, (y + 0.5 - c) / S
            r = math.hypot(dx, dy)
            if r > 3.45:
                continue
            face = (dx * LIGHT[0] + dy * LIGHT[1]) / (r or 1.0)
            th = math.atan2(dy, dx)
            if r > 2.85:                          # rim: lit upper left, dark below
                _px(img, x, y, "purple", 1.6 + face * 1.6)
            elif r < 1.25:                        # hot core
                _px(img, x, y, "metal", 6.0 if r < 0.8 else 5.0)
            else:                                 # the body, swirling: two arms
                arm = math.sin(2 * th + r * 2.4)
                lvl = 3.4 + face * 0.8 + (1.2 if arm > 0.55 else 0.0)
                _px(img, x, y, "purple", lvl)
    _px(img, int(c - 1.8 * S), int(c - 1.8 * S), "metal", 6)     # catch-light
    _px(img, int(c - 1.8 * S) + 1, int(c - 1.8 * S), "purple", 6)
    return img


def _burst():
    """The bite flash: the 1x spark's fat diamond, now with a white-hot heart,
    axial spikes past it and four sparks thrown off on the diagonals."""
    n = 8 * S
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    c = 4.0 * S
    for y in range(n):
        for x in range(n):
            dx, dy = (x + 0.5 - c) / S, (y + 0.5 - c) / S
            ax, ay = abs(dx), abs(dy)
            d = ax + ay                                   # the diamond
            spike = min(ax, ay) < 0.5 and max(ax, ay) < 3.6
            if d < 0.9:
                _px(img, x, y, "metal", 6)
            elif d < 1.7:
                _px(img, x, y, "gold", 6)
            elif d < 2.7:
                _px(img, x, y, "gold", 5.0 if dx + dy < 0 else 4.2)
            elif spike:
                _px(img, x, y, "gold", 4.4 if max(ax, ay) < 3.1 else 3.2)
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):          # sparks
        X, Y = int(c + sx * 2.6 * S), int(c + sy * 2.6 * S)
        _px(img, X - (1 if sx < 0 else 0), Y - (1 if sy < 0 else 0), "gold", 5)
    return img


def projectile_cells():
    """0 the enemy shot (every shooter's `frame: 0`), 1 the bite flash
    (data/weapons/bite.json `frames: [1]`)."""
    return [_orb(), _burst()]
